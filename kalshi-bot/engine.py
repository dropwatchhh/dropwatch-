"""State, risk limits, trading actions, settlement, reconciliation, main loop.

Every limit is enforced in State.check_entry(), which enter() calls itself, so no
caller (loop, board, test) can place an order around it. Money is in USD floats.
"""
import csv
import json
import math
import os
import threading
import time
from collections import deque
from datetime import datetime, timezone

import postmortem
import preflight
from kalshi_client import KalshiError, fee_per_contract, parse_time, quotes, trade_fee
from pilot import ASSETS_ALLOWED, STRONG, evaluate_signal
from signals import MODES, SERIES, analyze, decide, ladder_implied_vol, review, vol_scale_from

DEFAULTS = dict(
    trading="paper", mode="balanced", assets=["BTC"], size_per_trade_usd=5.0, daily_loss_cap_usd=15.0,
    max_losses_in_row=3, poll_seconds=2.0, hard_max_price=0.95, stale_seconds=5.0, basis_bps=2.0,
    shrink=0.9, momentum_weight=0.0, max_disagreement=0.30, fee_multiplier=None,
    record_snapshots=True, ladder_refresh_seconds=60,
)

TRADE_COLUMNS = [
    "time", "ticker", "asset", "close_time", "mode", "trading", "secs_left", "price", "target", "z_sigma",
    "momentum_pct", "vol_per_min_pct", "vol_scale", "p_model", "p_market", "yes_bid", "yes_ask", "no_bid",
    "no_ask", "action", "side", "count", "entry_price", "entry_fee", "edge", "reason", "reasoning",
    "cashed_out", "cash_price", "result", "won", "fees", "pnl",
]
SNAP_COLUMNS = ["time", "ticker", "asset", "secs_left", "price", "target", "vol_ps", "vol_scale", "momentum",
                "p_up", "yes_bid", "yes_ask", "no_bid", "no_ask", "yes_ask_size", "no_ask_size"]


KILL_FILE = os.getenv("KALSHI_BOT_KILL_FILE", "KILL")


def load_config(path):
    with open(path) as f:
        cfg = {**DEFAULTS, **json.load(f)}
    errs = []
    if cfg["trading"] not in ("paper", "live"):
        errs.append("trading must be 'paper' or 'live'")
    if cfg["mode"] not in MODES:
        errs.append(f"mode must be one of {list(MODES)}")
    if not cfg["assets"] or any(a not in SERIES for a in cfg["assets"]):
        errs.append(f"assets must be a non-empty subset of {list(SERIES)}")
    if not cfg["size_per_trade_usd"] > 0:
        errs.append("size_per_trade_usd must be > 0")
    if not cfg["daily_loss_cap_usd"] > 0:
        errs.append("daily_loss_cap_usd must be > 0")
    if int(cfg["max_losses_in_row"]) < 1:
        errs.append("max_losses_in_row must be >= 1")
    if not cfg["poll_seconds"] >= 0.5:
        errs.append("poll_seconds must be >= 0.5")
    if not 0.5 < cfg["hard_max_price"] <= 0.99:
        errs.append("hard_max_price must be in (0.5, 0.99]")
    if errs:
        raise ValueError("; ".join(errs))
    return cfg


def resolve_live(flag, cfg):
    """Live orders need BOTH the --live flag and trading=live in config."""
    return bool(flag) and cfg.get("trading") == "live"


def utc_today():
    return datetime.now(timezone.utc).date().isoformat()


def append_csv(path, columns, row, lock=None):
    def _w():
        new = not os.path.exists(path) or os.path.getsize(path) == 0
        with open(path, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
            if new:
                w.writeheader()
            w.writerow(row)
    if lock:
        with lock:
            _w()
    else:
        _w()


# ------------------------------------------------------------------ state + risk
class State:
    def __init__(self, cfg, path="state.json", trades_path="trades.csv", snaps_path="snapshots.csv", today_fn=utc_today,
                 kill_path=None):
        self.cfg, self.path = cfg, path
        self.kill_path = kill_path or KILL_FILE
        self.live = False          # set by bot.main only for trading=live AND --live
        self.pilot = None          # pilot.Pilot (required for any live order)
        self.ledger = None         # livelog.Ledger
        self.settle_checks = []    # live trades awaiting reconciliation with Kalshi's settlement record
        self.live_gate = None      # callable -> (ok, reason): the readiness re-check made AT ORDER TIME (fail closed if missing)
        self.trades_path, self.snaps_path, self.today_fn = trades_path, snaps_path, today_fn
        self.lock = threading.RLock()
        self.armed = False
        self.halted = ""
        self.day = today_fn()
        self.pnl = 0.0
        self.loss_streak = 0
        self.rounds = {}        # ticker -> round record (unfinalized)
        self.attempted = set()  # tickers we already tried to enter (one per round)
        self.last = {}          # asset -> terminal snapshot for the board
        self.balance = None
        self.log = deque(maxlen=50)
        self._load()

    # ---- persistence
    def _load(self):
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path) as f:
                d = json.load(f)
            self.rounds = d.get("rounds", {})
            self.attempted = set(d.get("attempted", []))
            if d.get("day") == self.day:
                self.pnl, self.loss_streak = d["pnl"], d["loss_streak"]
        except Exception:
            pass

    def save(self):
        with self.lock:
            tmp = self.path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(dict(day=self.day, pnl=self.pnl, loss_streak=self.loss_streak,
                               rounds=self.rounds, attempted=sorted(self.attempted)), f)
            os.replace(tmp, self.path)

    def note(self, msg):
        line = f"{datetime.now().strftime('%H:%M:%S')} {msg}"
        with self.lock:
            self.log.appendleft(line)
        print(line, flush=True)

    # ---- risk
    def roll_day(self):
        with self.lock:
            today = self.today_fn()
            if today != self.day:
                self.day, self.pnl, self.loss_streak = today, 0.0, 0
                self.note(f"New UTC day {today}: daily PnL and loss streak reset")

    def halt(self, reason):
        with self.lock:
            self.armed, self.halted = False, reason
            self.note(f"HALTED: {reason}")

    def open_cost(self):
        return sum(r["pos"]["price"] * r["pos"]["count"] + r["pos"]["fee"]
                   for r in self.rounds.values() if r.get("pos") and not r["pos"].get("closed"))

    def check_entry(self, ticker, price, cost, signal=None):
        """Fail-closed gate. Returns (ok, reason). In live mode the pilot gates apply too."""
        self.roll_day()
        c = self.cfg
        if os.path.exists(self.kill_path):
            self.armed = False
            return False, "kill switch engaged (KILL file present; run `python kill.py --clear`)"
        if self.halted:
            return False, f"halted: {self.halted}"
        if not self.armed:
            return False, "disarmed"
        if ticker in self.attempted or (self.rounds.get(ticker) or {}).get("pos"):
            return False, "already traded this round"
        if not (0 < price <= min(c["hard_max_price"], MODES[c["mode"]]["max_price"])):
            return False, f"price {price} above max {min(c['hard_max_price'], MODES[c['mode']]['max_price'])}"
        if cost > c["size_per_trade_usd"] + 1e-9:
            return False, f"cost ${cost:.2f} exceeds size cap ${c['size_per_trade_usd']:.2f}"
        if self.pnl <= -c["daily_loss_cap_usd"]:
            return False, "daily loss cap hit"
        if self.pnl - self.open_cost() - cost < -c["daily_loss_cap_usd"]:
            return False, "would risk breaching daily loss cap"
        if self.loss_streak >= c["max_losses_in_row"]:
            return False, f"{self.loss_streak} losses in a row"
        if self.live:
            if self.pilot is None:
                return False, "live orders require the pilot controls"
            if not signal or signal.get("ticker") != ticker or signal.get("grade") != STRONG \
                    or time.time() - signal.get("ts", 0) > c["stale_seconds"]:
                return False, "not a fresh STRONG BUY NOW (every check must pass)"
            n_open = sum(1 for r in self.rounds.values() if r.get("pos") and not r["pos"].get("closed"))
            ok, why = self.pilot.check_entry(cost, n_open, self.open_cost())
            if not ok:
                return False, why
            if self.live_gate is None:
                return False, "no live readiness gate attached"
            try:
                ok, why = self.live_gate()      # demo order + shard + hard stop etc. must pass RIGHT NOW
            except Exception as e:
                return False, f"readiness check errored ({type(e).__name__}): {e}"
            if not ok:
                return False, why
        return True, "ok"

    def realize(self, pnl):
        with self.lock:
            self.pnl += pnl
            if pnl < 0:
                self.loss_streak += 1
            elif pnl > 0:
                self.loss_streak = 0
            if self.live and self.pilot:
                ev = self.pilot.record_pnl(pnl)
                if ev:
                    if ev == "hard_stop":
                        self.armed = False
                    self.note(f"BREAKER {ev.upper()}: {self.pilot.hard_stop_reason or 'paused for the day'}")
                    if self.ledger:
                        self.ledger.log("breaker", kind=ev, **self.pilot.status())


FILL_RETRY_DELAY = 1.5   # seconds between polls of Kalshi's fills (its reads can lag a fresh order)


def verify_fill(client, res, side, count, fee_mult, sleep=None):
    """Compare what we think happened with Kalshi's own fill records. ok=False means STOP: unknown or mismatched."""
    oid = res.get("order_id")
    if not oid:
        return dict(ok=False, detail="order response has no order_id")
    fills = []
    sleep = sleep or time.sleep
    for _ in range(5):
        try:
            fills = client.fills(oid)
        except Exception as e:        # never let a failed lookup escape: the order may already have filled
            return dict(ok=False, detail=f"could not read fills from Kalshi ({type(e).__name__}: {e})")
        if fills:
            break
        sleep(FILL_RETRY_DELAY)
    if not fills:
        return dict(ok=False, detail="no fills visible on Kalshi for this order yet")
    key = "yes_price_dollars" if side == "yes" else "no_price_dollars"
    try:
        cnt = sum(float(f["count_fp"]) for f in fills)
        px = sum(float(f[key]) * float(f["count_fp"]) for f in fills) / cnt
        fee = sum(float(f.get("fee_cost") or 0) for f in fills)
    except (KeyError, ValueError, ZeroDivisionError, TypeError) as e:
        return dict(ok=False, detail=f"unreadable fill record ({type(e).__name__})")
    bad = []
    if abs(cnt - count) > 1e-6:
        bad.append(f"count {cnt:g} vs expected {count}")
    avg = res.get("average_fill_price")
    if avg:
        want = float(avg) if side == "yes" else 1 - float(avg)
        if abs(px - want) > 5e-4:
            bad.append(f"price {px:.4f} vs response {want:.4f}")
    if abs(trade_fee(px, cnt, fee_mult) - fee) > 0.0101:
        bad.append(f"fee ${fee:.4f} vs model ${trade_fee(px, cnt, fee_mult):.4f}")
    return dict(ok=not bad, count=cnt, price=px, fee=fee, detail="matches Kalshi's fill records" if not bad else "; ".join(bad))


def max_affordable_count(size, price, mult):
    n = int(size // (price + fee_per_contract(price, mult)))
    while n > 0 and price * n + trade_fee(price, n, mult) > size + 1e-9:
        n -= 1
    return n


# ------------------------------------------------------------------ rounds
def new_round(asset, m, snap, reasoning, dec, st):
    return dict(ticker=m["ticker"], asset=asset, close_time=m["close_time"], snap=snap, score=-9.0,
                reasoning=reasoning, action="SKIP", reason=dec["reason"], edge=dec.get("edge"), side=dec.get("side"),
                mode=st.cfg["mode"], pos=None, cash=None, pnl=0.0, fees=0.0, result="", finalized=False)


def update_round_snapshot(st, r, snap, dec, reasoning):
    """Keep, per round, the snapshot that came closest to qualifying (best in-window edge)."""
    if r.get("pos"):
        return
    score = (dec["edge"] if dec.get("edge") is not None else -5.0) + (0 if dec.get("in_window") else -10.0)
    if score > r["score"]:
        r.update(snap=snap, score=score, reasoning=reasoning, reason=dec["reason"], edge=dec.get("edge"),
                 side=dec.get("side"), mode=st.cfg["mode"])


# ------------------------------------------------------------------ trading actions
def enter(client, st, live, ticker, side, price, ask_size, fee_mult, reason, reasoning=None, signal=None):
    """Place (or paper-simulate) one limit buy. All risk checks happen here."""
    with st.lock:
        r = st.rounds.get(ticker)
        if r is None:
            return False
        if bool(live) != bool(st.live):
            st.note("refusing order: live flag does not match the process's live mode")
            return False
        size, max_count = st.cfg["size_per_trade_usd"], None
        if st.live and st.pilot:
            size, max_count = min(size, st.pilot.limits["stake_usd"]), st.pilot.limits["contracts"]
        count = max_affordable_count(size, price, fee_mult)
        if max_count is not None:
            count = min(count, int(max_count))
        if ask_size is not None:
            count = min(count, int(ask_size))
        if count < 1:
            st.note(f"skip {ticker}: size cap too small for price {price:.2f} (or no depth)")
            return False
        fee = trade_fee(price, count, fee_mult)
        ok, why = st.check_entry(ticker, price, price * count + fee, signal)
        if not ok:
            r["reason"] = f"blocked: {why}"
            return False
        st.attempted.add(ticker)  # one attempt per round, even if the order fails
        if live:
            st.save()  # write-ahead: a crash during/after the order can never lead to a second order
            st.pilot.record_order_sent()
            if st.ledger:
                st.ledger.log("order_sent", ticker=ticker, side=side, action="buy", count=count, limit_price=price,
                              model_fee=fee, signal=dict(grade=signal["grade"], checks=signal["checks"], flip=signal["flip"]))
        fill_price = price
        if live:
            try:
                res = client.place_order(ticker, side, "buy", count, price)
            except KalshiError as e:
                if st.ledger:
                    st.ledger.log("order_error", ticker=ticker, error=str(e), ambiguous=e.ambiguous)
                if e.ambiguous:
                    st.halt(f"order outcome unknown for {ticker} ({e}); restart to reconcile with Kalshi")
                else:
                    st.note(f"ORDER REJECTED {ticker}: {e}")
                st.save()
                return False
            if st.ledger:
                st.ledger.log("order_result", ticker=ticker, **{k: res.get(k) for k in (
                    "order_id", "client_order_id", "fill_count", "remaining_count", "average_fill_price", "average_fee_paid")})
            filled = float(res.get("fill_count") or 0)
            if filled < 1:
                st.note(f"LIVE order {ticker} not filled (IOC at {price:.2f}); no position")
                st.save()
                return False
            count = int(round(filled))
            avg = res.get("average_fill_price")
            if avg:  # V2 reports the YES-leg price
                fill_price = float(avg) if side == "yes" else 1 - float(avg)
            fee = (float(res["average_fee_paid"]) * count) if res.get("average_fee_paid") else trade_fee(fill_price, count, fee_mult)
            v = verify_fill(client, res, side, count, fee_mult)
            if st.ledger:
                st.ledger.log("fill_check", ticker=ticker, **v)
            if v.get("price") is not None:       # Kalshi's own records are the source of truth for real P&L
                fill_price, fee = v["price"], v["fee"]
        r["pos"] = dict(side=side, count=count, price=fill_price, fee=fee, closed=False,
                        opened=datetime.now(timezone.utc).isoformat())
        r.update(action="ENTER", reason=reason, reasoning=reasoning or r["reasoning"], side=side)
        st.note(f"{'LIVE' if live else 'PAPER'} BUY {count} {side.upper()} {ticker} @ {fill_price:.3f} fee ${fee:.2f} ({reason})")
        st.save()
        if live and not v["ok"]:
            st.halt(f"fill check FAILED for {ticker}: {v['detail']}. Position is tracked; disarmed until you review.")
        return True


def cash_out(client, st, ticker, live, fee_mult=1.0):
    """Sell the open position at the current bid. Works even when disarmed."""
    with st.lock:
        r = st.rounds.get(ticker)
        pos = r and r.get("pos")
        if not pos or pos.get("closed"):
            return "no open position"
        m = client.market(ticker)
        q = quotes(m)
        bid = q["yes_bid"] if pos["side"] == "yes" else q["no_bid"]
        if not bid or bid <= 0:
            return "no bid available - cannot cash out right now"
        sold, exit_fee, verified = pos["count"], None, False
        if live:
            if st.ledger:
                st.ledger.log("cash_out_sent", ticker=ticker, side=pos["side"], count=pos["count"], limit_price=bid)
            try:
                res = client.place_order(ticker, pos["side"], "sell", pos["count"], bid)
            except KalshiError as e:
                if st.ledger:
                    st.ledger.log("order_error", ticker=ticker, error=str(e), ambiguous=e.ambiguous)
                if e.ambiguous:
                    st.halt(f"cash-out outcome unknown for {ticker} ({e}); restart to reconcile")
                return f"cash-out failed: {e}"
            sold = int(round(float(res.get("fill_count") or 0)))
            if sold < 1:
                return "cash-out not filled (no liquidity at the bid)"
            avg = res.get("average_fill_price")
            if avg:
                bid = float(avg) if pos["side"] == "yes" else 1 - float(avg)
            if st.ledger:
                st.ledger.log("order_result", ticker=ticker, **{k: res.get(k) for k in (
                    "order_id", "client_order_id", "fill_count", "remaining_count", "average_fill_price", "average_fee_paid")})
            if st.pilot:
                v = verify_fill(client, res, pos["side"], sold, fee_mult)
                if st.ledger:
                    st.ledger.log("fill_check", ticker=ticker, **v)
                verified = v["ok"]
                if v.get("price") is not None:
                    bid, exit_fee = v["price"], v["fee"]
                if not v["ok"]:
                    st.halt(f"cash-out fill check FAILED for {ticker}: {v['detail']}")
        sell_fee = exit_fee if exit_fee is not None else trade_fee(bid, sold, fee_mult)
        share = sold / pos["count"]
        cost = (pos["price"] * pos["count"] + pos["fee"]) * share
        pnl = bid * sold - sell_fee - cost
        r["pnl"] += pnl
        r["fees"] += sell_fee + pos["fee"] * share
        r["cash"] = dict(price=bid, count=sold)
        if sold >= pos["count"]:
            pos["closed"] = True
        else:
            pos["count"] -= sold
            pos["fee"] *= 1 - share
        st.realize(pnl)
        if live and st.ledger:
            st.ledger.log("trade_closed", ticker=ticker, exit_kind="cashout", side=pos["side"], count=sold, exit_price=bid,
                          entry_price=pos["price"], fees=round(sell_fee + pos["fee"] * share, 4), pnl_net=round(pnl, 4), verified=verified)
        st.note(f"CASH OUT {sold} {pos['side'].upper()} {ticker} @ {bid:.3f} pnl {pnl:+.2f}")
        st.save()
        return f"sold {sold} @ {bid:.3f}, pnl {pnl:+.2f}"


def finalize_round(st, r, result, market=None):
    """Settle any held position, write the round's trades.csv row, drop it from state."""
    with st.lock:
        pos = r.get("pos")
        if pos and not pos.get("closed"):
            won = result == pos["side"]
            pnl = (pos["count"] if won else 0.0) - pos["price"] * pos["count"] - pos["fee"]
            r["pnl"] += pnl
            r["fees"] += pos["fee"]
            pos["closed"] = True
            st.realize(pnl)
            st.note(f"SETTLED {r['ticker']} result={result} {'WIN' if won else 'LOSS'} pnl {pnl:+.2f}")
            if st.live and st.ledger:
                st.ledger.log("trade_closed", ticker=r["ticker"], exit_kind="settlement", result=result, side=pos["side"],
                              count=pos["count"], entry_price=pos["price"], fees=round(pos["fee"], 4), pnl_net=round(pnl, 4),
                              payout=float(pos["count"] if won else 0), verified=False)
                st.settle_checks.append(dict(ticker=r["ticker"], count=pos["count"], side=pos["side"], won=won,
                                             cost=pos["price"] * pos["count"], since=time.time()))
        r["result"], r["finalized"] = result, True
        if traded_loss(r) and st.ledger:
            try:
                st.ledger.postmortem(dict(postmortem.build(r, result, (market or {}).get("expiration_value"), r["pnl"], st.snaps_path),
                                          mode="live" if st.live else "paper"))
            except Exception as e:      # a failed post-mortem must never block settlement
                st.note(f"post-mortem failed: {e}")
        s = r["snap"] or {}
        traded = bool(r.get("pos"))
        side = (r["pos"] or {}).get("side") if traded else None
        row = dict(s, time=s.get("time"), ticker=r["ticker"], asset=r["asset"], close_time=r["close_time"],
                   mode=r["mode"], trading=s.get("trading"), action="ENTER" if traded else "SKIP",
                   side=side or r.get("side"), count=(r["pos"] or {}).get("count") if traded else None,
                   entry_price=(r["pos"] or {}).get("price") if traded else None,
                   entry_fee=(r["pos"] or {}).get("fee") if traded else None,
                   edge=r.get("edge"), reason=r["reason"], reasoning=" | ".join(r["reasoning"] or []),
                   cashed_out=1 if r.get("cash") else 0, cash_price=(r.get("cash") or {}).get("price"),
                   result=result, won=(1 if r["pnl"] > 0 else 0) if traded else None,
                   fees=round(r["fees"], 4), pnl=round(r["pnl"], 4) if traded else 0.0)
        append_csv(st.trades_path, TRADE_COLUMNS, row)
        st.rounds.pop(r["ticker"], None)
        st.save()


def traded_loss(r):
    return bool(r.get("pos")) and r["pnl"] < 0


def verify_settlements(client, st, now=None):
    """Reconcile closed live trades with Kalshi's settlement records; a mismatch halts trading."""
    now = now or time.time()
    for chk in list(st.settle_checks):
        try:
            rows = client.settlements(chk["ticker"])
        except Exception as e:
            st.note(f"settlement lookup {chk['ticker']}: {e}")
            continue
        if not rows:
            if now - chk["since"] > 3600:
                st.settle_checks.remove(chk)
                st.ledger.log("settlement_unverified", ticker=chk["ticker"], detail="no settlement record after 1h")
                st.halt(f"no Kalshi settlement record for {chk['ticker']} after 1h")
            continue
        row = rows[0]
        revenue = float(row["revenue"]) / 100.0
        basis = float(row.get("yes_total_cost_dollars") or 0) + float(row.get("no_total_cost_dollars") or 0)
        want = float(chk["count"] if chk["won"] else 0)
        bad = []
        if abs(revenue - want) > 0.005:
            bad.append(f"revenue ${revenue:.2f} vs expected ${want:.2f}")
        if abs(basis - chk["cost"]) > 0.02:
            bad.append(f"cost basis ${basis:.2f} vs ours ${chk['cost']:.2f}")
        st.settle_checks.remove(chk)
        st.ledger.log("settlement_verified" if not bad else "settlement_mismatch", ticker=chk["ticker"], revenue=revenue,
                      cost_basis=basis, fee_cost=row.get("fee_cost"), detail="; ".join(bad) or "matches Kalshi's settlement record")
        if bad:
            st.halt(f"settlement mismatch for {chk['ticker']}: {'; '.join(bad)}")


def settle_pending(client, st, now=None):
    now = now or time.time()
    for ticker, r in list(st.rounds.items()):
        close = parse_time(r["close_time"]).timestamp()
        if now < close + 3 or now < r.get("next_check", 0):
            continue
        r["next_check"] = now + 5
        try:
            mk = client.market(ticker)
            res = mk.get("result")
        except Exception as e:
            st.note(f"settle lookup {ticker}: {e}")
            continue
        if res in ("yes", "no"):
            finalize_round(st, r, res, mk)
        elif now > close + 3600 and not (r.get("pos") and not r["pos"].get("closed")):
            finalize_round(st, r, "")  # never resolved; unheld, record as unknown


def reconcile(client, st):
    """Live startup: align local positions with what Kalshi says we hold."""
    prefixes = tuple(SERIES.values())
    held = {}
    for p in client.positions():
        t, n = p.get("ticker", ""), float(p.get("position_fp") or p.get("position") or 0)
        if t.startswith(prefixes) and n != 0:
            exposure = float(p.get("market_exposure_dollars") or 0)
            held[t] = dict(side="yes" if n > 0 else "no", count=int(abs(round(n))),
                           price=exposure / abs(n) if exposure else 0.5)
    with st.lock:
        for t, h in held.items():
            if not (st.rounds.get(t) or {}).get("pos"):
                m = client.market(t)
                st.rounds[t] = dict(ticker=t, asset=next(a for a, s in SERIES.items() if t.startswith(s)),
                                    close_time=m["close_time"], snap={}, score=-9.0, reasoning=["reconciled from Kalshi"],
                                    action="ENTER", reason="reconciled from Kalshi", edge=None, side=h["side"],
                                    mode=st.cfg["mode"], pos=dict(h, fee=0.0, closed=False), cash=None, pnl=0.0,
                                    fees=0.0, result="", finalized=False)
                st.attempted.add(t)
                st.note(f"RECONCILED open position from Kalshi: {h['count']} {h['side']} {t}")
        for t, r in list(st.rounds.items()):
            if r.get("pos") and not r["pos"].get("closed") and t not in held:
                st.note(f"local position {t} not on Kalshi; dropping (never filled or already settled)")
                r["pos"] = None
        st.save()


# ------------------------------------------------------------------ main loop
class Ctx:
    def __init__(self, client, st, feeds, live, fee_mult=1.0, preflight_path="preflight.json", fee_verified=False):
        self.client, self.st, self.feeds, self.live, self.fee_mult = client, st, feeds, live, fee_mult
        self.ladder, self.ladder_at = None, 0.0
        self.errors = {}
        self.preflight_path, self.fee_verified = preflight_path, fee_verified
        self.shard = None                      # last shard-check result
        self.ready_at = self.settle_at = 0.0
        if st.live:
            st.live_gate = self.gate

    def readiness(self, fresh_shard=False):
        """Everything that must be true for LIVE to be enabled (and to stay enabled). Returns dict(ok, checks)."""
        st, checks = self.st, []

        def add(name, ok, detail=""):
            checks.append(dict(name=name, ok=bool(ok), detail=detail))
        add("process started with trading=live AND --live", self.live and st.live, "" if self.live else "start with --live and trading=live")
        add("live credentials loaded (KALSHI_LIVE_*)", bool(getattr(self.client, "key", None)) and getattr(self.client, "env", "") == "live", "")
        add("pilot controls present", st.pilot is not None, "")
        add("BTC only", list(st.cfg["assets"]) == list(ASSETS_ALLOWED), str(st.cfg["assets"]))
        add("fee schedule verified (quadratic, multiplier read from Kalshi)", self.fee_verified, f"multiplier {self.fee_mult}")
        ok, why = preflight.demo_fresh(self.preflight_path, getattr(self.client, "fingerprint", None))
        add("DEMO test order passed recently (separate demo key)", ok, why)
        if fresh_shard or self.shard is None or time.time() - self.shard["ts"] > 55:
            try:
                m = self.client.open_market(SERIES["BTC"])
                self.shard = preflight.shard_check(self.client, m, st.pilot.limits["stake_usd"] if st.pilot else 1.0) if m else \
                    dict(ok=False, ts=time.time(), detail="no open BTC market")
            except Exception as e:
                self.shard = dict(ok=False, ts=time.time(), detail=f"shard check error: {e}")
        add("SHARD check: funds on the exchange shard BTC trades on", self.shard["ok"], self.shard.get("detail", ""))
        add("no hard stop active", not (st.pilot and st.pilot.hard_stopped), st.pilot.hard_stop_reason if st.pilot else "")
        add("kill switch not engaged", not os.path.exists(st.kill_path), "")
        add("not halted", not st.halted, st.halted)
        return dict(ok=all(c["ok"] for c in checks), checks=checks, ts=time.time())

    def gate(self):
        """Order-time check: everything LIVE requires must pass right now, not just at the last poll."""
        rd = self.readiness(fresh_shard=True)
        if rd["ok"]:
            return True, "ok"
        return False, "live readiness failing: " + "; ".join(f"{c['name']}: {c['detail']}" if c["detail"] else c["name"]
                                                            for c in rd["checks"] if not c["ok"])

    def periodic(self, now=None):
        """While LIVE is on, keep proving it is safe; switch it off the moment any check fails."""
        now, st = now or time.time(), self.st
        if st.live and st.pilot and st.pilot.live_enabled and now - self.ready_at >= 60:
            self.ready_at = now
            rd = self.readiness(fresh_shard=True)
            if not rd["ok"]:
                why = "; ".join(f"{c['name']}: {c['detail']}" for c in rd["checks"] if not c["ok"])
                st.pilot.disable()
                st.armed = False
                st.note(f"LIVE DISABLED automatically: {why}")
                if st.ledger:
                    st.ledger.log("live_disabled", reason=why)
        if st.live and st.settle_checks and now - self.settle_at >= 30:
            self.settle_at = now
            verify_settlements(self.client, st, now)

    def get_ladder(self, spot, now):
        if now - self.ladder_at >= self.st.cfg["ladder_refresh_seconds"]:
            self.ladder_at = now
            try:
                self.ladder = self.client.btc_ladder()
            except Exception as e:
                self.ladder = None
                self.st.note(f"ladder fetch failed: {e}")
        return ladder_implied_vol(spot, self.ladder or [], now) if self.ladder else None


def process_asset(ctx, asset, now=None):
    st, cfg = ctx.st, ctx.st.cfg
    feed = ctx.feeds[asset]
    try:
        feed.poll()
    except Exception as e:
        st.note(f"{asset} price poll failed: {e}")
    m = ctx.client.open_market(SERIES[asset])
    if not m:
        return
    now = now or time.time()
    target = float(m.get("floor_strike") or 0)
    close_ts = parse_time(m["close_time"]).timestamp()
    secs_left = close_ts - now
    q = quotes(m)
    fresh = feed.is_fresh(cfg["stale_seconds"], now)
    price = feed.last()
    vol = feed.vol(now) if fresh else None
    mom = feed.momentum(120, now) if fresh else 0.0
    ladder = ctx.get_ladder(price, now) if (fresh and asset == "BTC") else None
    scale = vol_scale_from(vol, ladder["vol_ps"] if ladder else None)
    sig = None
    if fresh and target > 0:
        sig = analyze(price, target, secs_left, vol, mom, feed.mean_since(close_ts - 60), cfg["basis_bps"],
                      cfg["shrink"], cfg["momentum_weight"], scale)
    dec = decide(sig, q, secs_left, cfg["mode"], ctx.fee_mult, cfg["hard_max_price"])
    if not fresh:
        dec["reason"] = f"stale price data ({feed.age(now):.0f}s old), skipping"
    rv = review(sig, q, dec, vol, scale, ladder, mom, cfg["max_disagreement"])
    if dec["enter"] and rv["verdict"] == "veto":
        dec.update(enter=False, reason="reasoning engine veto (model vs market disagree too much)")
    pilot_ev = None
    if ctx.live and st.pilot:      # LIVE pilot: only a STRONG BUY NOW may enter, with the conservative rules' side and price
        pilot_ev = evaluate_signal(m["ticker"], sig, q, secs_left, mom, fresh, ctx.fee_mult, cfg["hard_max_price"],
                                   lambda d: review(sig, q, d, vol, scale, ladder, mom, cfg["max_disagreement"]), now)
        strong = pilot_ev["grade"] == STRONG
        dec = dict(enter=strong, side=pilot_ev["side"], price=pilot_ev["price"], edge=pilot_ev["edge"],
                   in_window=dec.get("in_window", False),
                   reason=("STRONG BUY NOW: every check passed" if strong else "WAIT: " + "; ".join(pilot_ev["failed"])))
    mid = None if sig is None else (None if q["yes_bid"] is None or q["yes_ask"] is None else (q["yes_bid"] + q["yes_ask"]) / 2)
    snap = dict(time=datetime.fromtimestamp(now, timezone.utc).isoformat(), trading="live" if ctx.live else "paper",
                secs_left=int(secs_left), price=price, target=target, z_sigma=None if not sig else round(sig["z"], 3),
                momentum_pct=round(mom * 100, 4), vol_per_min_pct=None if not vol else round(vol * math.sqrt(60) * 100, 5),
                vol_scale=round(scale, 3), p_model=None if not sig else round(sig["p_up"], 4),
                p_market=None if mid is None else round(mid, 4), yes_bid=q["yes_bid"], yes_ask=q["yes_ask"],
                no_bid=q["no_bid"], no_ask=q["no_ask"])
    with st.lock:
        r = st.rounds.get(m["ticker"])
        if r is None and m["ticker"] not in st.attempted:
            r = st.rounds[m["ticker"]] = new_round(asset, m, snap, rv["lines"], dec, st)
        if r is not None:
            update_round_snapshot(st, r, snap, dec, rv["lines"])
        pos = (r or {}).get("pos")
        st.last[asset] = dict(
            ticker=m["ticker"], price=price, target=target, secs_left=int(secs_left), momentum=snap["momentum_pct"],
            vol=snap["vol_per_min_pct"], p_up=snap["p_model"], p_market=snap["p_market"],
            likely=None if not sig else ("UP" if sig["side"] == "yes" else "DOWN"), z=snap["z_sigma"],
            high_low=feed.high_low(600, now), yes_ask=q["yes_ask"], no_ask=q["no_ask"],
            action=("ENTER " + dec["side"].upper()) if dec["enter"] else "SKIP", why=dec["reason"],
            reasoning=rv["lines"], fresh=fresh, pilot=pilot_ev,
            position=None if not pos or pos.get("closed") else dict(pos))
    if cfg.get("record_snapshots") and sig:
        append_csv(st.snaps_path, SNAP_COLUMNS, dict(
            snap, vol_ps=vol, momentum=mom, p_up=sig["p_up"], yes_ask_size=q["yes_ask_size"], no_ask_size=q["no_ask_size"],
            ticker=m["ticker"], asset=asset), st.lock)
    if dec["enter"] and r is not None:
        ask_size = q["yes_ask_size"] if dec["side"] == "yes" else q["no_ask_size"]
        enter(ctx.client, st, ctx.live, m["ticker"], dec["side"], dec["price"], ask_size, ctx.fee_mult,
              dec["reason"], rv["lines"], signal=pilot_ev)


def run_loop(ctx, stop, deadline=None):
    st = ctx.st
    while not stop.is_set():
        if deadline and time.time() >= deadline:
            stop.set()
            break
        st.roll_day()
        if os.path.exists(st.kill_path) and st.armed:
            st.armed = False
            st.note("KILL file present: disarmed")
        for asset in ctx.feeds:
            try:
                process_asset(ctx, asset)
                ctx.errors[asset] = 0
            except Exception as e:  # fail closed: log, skip this asset this cycle, back off
                ctx.errors[asset] = ctx.errors.get(asset, 0) + 1
                st.note(f"{asset} loop error ({type(e).__name__}): {e}")
                stop.wait(min(30, 2 ** ctx.errors[asset]))
        try:
            settle_pending(ctx.client, st)
            ctx.periodic()
        except Exception as e:
            st.note(f"settle/periodic error: {e}")
        stop.wait(st.cfg["poll_seconds"])
