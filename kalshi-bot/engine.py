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

from kalshi_client import KalshiError, fee_per_contract, parse_time, quotes, trade_fee
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

    def check_entry(self, ticker, price, cost):
        """Fail-closed gate. Returns (ok, reason)."""
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
        return True, "ok"

    def realize(self, pnl):
        with self.lock:
            self.pnl += pnl
            if pnl < 0:
                self.loss_streak += 1
            elif pnl > 0:
                self.loss_streak = 0


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
def enter(client, st, live, ticker, side, price, ask_size, fee_mult, reason, reasoning=None):
    """Place (or paper-simulate) one limit buy. All risk checks happen here."""
    with st.lock:
        r = st.rounds.get(ticker)
        if r is None:
            return False
        count = max_affordable_count(st.cfg["size_per_trade_usd"], price, fee_mult)
        if ask_size is not None:
            count = min(count, int(ask_size))
        if count < 1:
            st.note(f"skip {ticker}: size cap too small for price {price:.2f} (or no depth)")
            return False
        fee = trade_fee(price, count, fee_mult)
        ok, why = st.check_entry(ticker, price, price * count + fee)
        if not ok:
            r["reason"] = f"blocked: {why}"
            return False
        st.attempted.add(ticker)  # one attempt per round, even if the order fails
        if live:
            st.save()  # write-ahead: a crash during/after the order can never lead to a second order
        fill_price = price
        if live:
            try:
                res = client.place_order(ticker, side, "buy", count, price)
            except KalshiError as e:
                if e.ambiguous:
                    st.halt(f"order outcome unknown for {ticker} ({e}); restart to reconcile with Kalshi")
                else:
                    st.note(f"ORDER REJECTED {ticker}: {e}")
                st.save()
                return False
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
        r["pos"] = dict(side=side, count=count, price=fill_price, fee=fee, closed=False,
                        opened=datetime.now(timezone.utc).isoformat())
        r.update(action="ENTER", reason=reason, reasoning=reasoning or r["reasoning"], side=side)
        st.note(f"{'LIVE' if live else 'PAPER'} BUY {count} {side.upper()} {ticker} @ {fill_price:.3f} fee ${fee:.2f} ({reason})")
        st.save()
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
        sold = pos["count"]
        if live:
            try:
                res = client.place_order(ticker, pos["side"], "sell", pos["count"], bid)
            except KalshiError as e:
                if e.ambiguous:
                    st.halt(f"cash-out outcome unknown for {ticker} ({e}); restart to reconcile")
                return f"cash-out failed: {e}"
            sold = int(round(float(res.get("fill_count") or 0)))
            if sold < 1:
                return "cash-out not filled (no liquidity at the bid)"
            avg = res.get("average_fill_price")
            if avg:
                bid = float(avg) if pos["side"] == "yes" else 1 - float(avg)
        sell_fee = trade_fee(bid, sold, fee_mult)
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
        st.note(f"CASH OUT {sold} {pos['side'].upper()} {ticker} @ {bid:.3f} pnl {pnl:+.2f}")
        st.save()
        return f"sold {sold} @ {bid:.3f}, pnl {pnl:+.2f}"


def finalize_round(st, r, result):
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
        r["result"], r["finalized"] = result, True
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


def settle_pending(client, st, now=None):
    now = now or time.time()
    for ticker, r in list(st.rounds.items()):
        close = parse_time(r["close_time"]).timestamp()
        if now < close + 3 or now < r.get("next_check", 0):
            continue
        r["next_check"] = now + 5
        try:
            res = client.market(ticker).get("result")
        except Exception as e:
            st.note(f"settle lookup {ticker}: {e}")
            continue
        if res in ("yes", "no"):
            finalize_round(st, r, res)
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
    def __init__(self, client, st, feeds, live, fee_mult=1.0):
        self.client, self.st, self.feeds, self.live, self.fee_mult = client, st, feeds, live, fee_mult
        self.ladder, self.ladder_at = None, 0.0
        self.errors = {}

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
            reasoning=rv["lines"], fresh=fresh,
            position=None if not pos or pos.get("closed") else dict(pos))
    if cfg.get("record_snapshots") and sig:
        append_csv(st.snaps_path, SNAP_COLUMNS, dict(
            snap, vol_ps=vol, momentum=mom, p_up=sig["p_up"], yes_ask_size=q["yes_ask_size"], no_ask_size=q["no_ask_size"],
            ticker=m["ticker"], asset=asset), st.lock)
    if dec["enter"] and r is not None:
        ask_size = q["yes_ask_size"] if dec["side"] == "yes" else q["no_ask_size"]
        enter(ctx.client, st, ctx.live, m["ticker"], dec["side"], dec["price"], ask_size, ctx.fee_mult,
              dec["reason"], rv["lines"])


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
        except Exception as e:
            st.note(f"settle error: {e}")
        stop.wait(st.cfg["poll_seconds"])
