#!/usr/bin/env python3
"""Replay recorded rounds and report whether the strategy beat the prices it paid.

  python backtest.py                      # analyse trades.csv (what the bot actually did)
  python backtest.py --replay --mode aggressive --min-edge 0.03
                                          # re-run the decision rules over snapshots.csv

All PnL is net of Kalshi fees (rows already contain fees; replay recomputes them).
"""
import argparse
import csv
import math
import random
import sys
from collections import defaultdict
from statistics import NormalDist

from engine import max_affordable_count
from kalshi_client import fee_per_contract, trade_fee
from signals import MODES, decide

MIN_TRADES = 30


def _f(x):
    try:
        return float(x) if x not in (None, "") else None
    except ValueError:
        return None


def load_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def binom_p_ge(k, n, p=0.5):
    """Exact one-sided P(X >= k) for X ~ Binomial(n, p)."""
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def max_drawdown(pnls):
    peak = eq = dd = 0.0
    for p in pnls:
        eq += p
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    return dd


def bootstrap_mean_ci(xs, n=2000, seed=1):
    """95% bootstrap CI for the mean (deterministic seed). None for < 2 points."""
    if len(xs) < 2:
        return None
    rnd = random.Random(seed)
    means = sorted(sum(rnd.choice(xs) for _ in xs) / len(xs) for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n)]


def analyse(rows):
    """rows: dicts shaped like trades.csv. Returns a metrics dict."""
    resolved = [r for r in rows if r.get("result") in ("yes", "no")]
    traded = [r for r in resolved if r.get("action") == "ENTER" and _f(r.get("count"))]
    out = dict(rounds=len(rows), resolved=len(resolved), traded=len(traded), skipped=len(resolved) - len(traded))
    pnls = [_f(r["pnl"]) or 0.0 for r in traded]
    fees = sum(_f(r["fees"]) or 0.0 for r in traded)
    cost = sum((_f(r["entry_price"]) * _f(r["count"]) + (_f(r["entry_fee"]) or 0)) for r in traded)
    wins = sum(1 for p in pnls if p > 0)
    out.update(wins=wins, win_rate=wins / len(traded) if traded else None, fees=fees, net_pnl=sum(pnls),
               gross_pnl=sum(pnls) + fees, capital_at_risk=cost, roi=sum(pnls) / cost if cost else None,
               max_drawdown=max_drawdown(pnls), cashed_out=sum(1 for r in traded if r.get("cashed_out") == "1"))
    out["pnl_per_trade"] = sum(pnls) / len(pnls) if pnls else None
    out["pnl_per_trade_ci95"] = bootstrap_mean_ci(pnls)
    out["avg_entry_price"] = sum(_f(r["entry_price"]) for r in traded) / len(traded) if traded else None
    out["avg_claimed_edge"] = (sum(_f(r["edge"]) or 0 for r in traded) / len(traded)) if traded else None
    # price tests use trades held to settlement (cash-outs have a different payoff)
    held = [r for r in traded if r.get("cashed_out") != "1"]
    be = [(_f(r["entry_price"]) + (_f(r["entry_fee"]) or 0) / _f(r["count"])) for r in held]
    hw = sum(1 for r in held if (_f(r["pnl"]) or 0) > 0)
    out["held"] = len(held)
    out["avg_breakeven"] = sum(be) / len(be) if be else None
    out["realized_edge"] = (hw / len(held) - out["avg_breakeven"]) if held else None
    out["p_vs_coinflip"] = binom_p_ge(hw, len(held)) if held else None
    if held:
        var = sum(b * (1 - b) for b in be)
        out["z_vs_price"] = (hw - sum(be)) / math.sqrt(var) if var > 0 else 0.0
        out["p_vs_price"] = 1 - NormalDist().cdf(out["z_vs_price"])
    # calibration on ALL resolved rounds (skips included): model vs market mid
    cal = [(_f(r.get("p_model")), _f(r.get("p_market")), 1.0 if r["result"] == "yes" else 0.0)
           for r in resolved if _f(r.get("p_model")) is not None and _f(r.get("p_market")) is not None]
    out["calib_n"] = len(cal)
    if cal:
        out["brier_model"] = sum((p - y) ** 2 for p, _, y in cal) / len(cal)
        out["brier_market"] = sum((m - y) ** 2 for _, m, y in cal) / len(cal)
        bins = defaultdict(list)
        for p, _, y in cal:
            bins[min(int(p * 10), 9)].append((p, y))
        out["calibration"] = [(b / 10, len(v), sum(p for p, _ in v) / len(v), sum(y for _, y in v) / len(v))
                              for b, v in sorted(bins.items())]
    n = len(held)
    if n < MIN_TRADES:
        out["verdict"] = (f"INCONCLUSIVE: only {n} held-to-settlement trades (need >= {MIN_TRADES}). "
                          f"No statistical claim about edge can be made.")
    elif out["realized_edge"] > 0 and out["p_vs_price"] < 0.05 and out["net_pnl"] > 0:
        out["verdict"] = "EDGE (tentative): beat the prices paid at p<0.05 and net PnL > 0. Confirm out-of-sample."
    else:
        out["verdict"] = "NO DEMONSTRATED EDGE: results are not distinguishable from paying fair price plus fees."
    return out


def format_report(m):
    def pct(x):
        return "n/a" if x is None else f"{x * 100:.1f}%"
    L = ["=" * 60,
         f"rounds {m['rounds']} | resolved {m['resolved']} | traded {m['traded']} | skipped {m['skipped']}",
         f"win rate        {pct(m['win_rate'])}  ({m['wins']}/{m['traded']}, {m['cashed_out']} cashed out)",
         f"avg entry price {m['avg_entry_price'] if m['avg_entry_price'] is None else round(m['avg_entry_price'], 3)}"
         f" | breakeven win rate (price+fee) {pct(m['avg_breakeven'])}",
         f"claimed edge    {m['avg_claimed_edge'] if m['avg_claimed_edge'] is None else round(m['avg_claimed_edge'], 3)}"
         f" | realized edge (win rate - breakeven) {m['realized_edge'] if m['realized_edge'] is None else round(m['realized_edge'], 3)}",
         f"fees ${m['fees']:.2f} | gross PnL ${m['gross_pnl']:+.2f} | NET PnL ${m['net_pnl']:+.2f} | ROI {pct(m['roi'])}",
         f"max drawdown    ${m['max_drawdown']:.2f}"]
    if m.get("pnl_per_trade_ci95"):
        lo, hi = m["pnl_per_trade_ci95"]
        L.append(f"net PnL per trade ${m['pnl_per_trade']:+.3f}  (95% bootstrap CI {lo:+.3f} .. {hi:+.3f}"
                 f"{'; includes zero' if lo <= 0 <= hi else ''})")
    if m.get("p_vs_coinflip") is not None:
        L.append(f"beats coin flip (win rate > 50%)?   p = {m['p_vs_coinflip']:.3f}")
        L.append(f"beats the prices paid (incl fees)? p = {m['p_vs_price']:.3f}  (z = {m['z_vs_price']:+.2f})")
    if m.get("calib_n"):
        L.append(f"Brier score on {m['calib_n']} rounds: model {m['brier_model']:.4f} vs market mid "
                 f"{m['brier_market']:.4f}  ({'model better' if m['brier_model'] < m['brier_market'] else 'MARKET better'}; lower wins)")
        L.append("calibration (model P(up) bin: n, mean predicted, actual up-rate):")
        L += [f"  {b:.1f}-{b + .1:.1f}: n={n:3d} pred {p:.2f} actual {a:.2f}" for b, n, p, a in m["calibration"]]
    L += ["", "VERDICT: " + m["verdict"], "=" * 60]
    return "\n".join(L)


# ------------------------------------------------------------------ replay
def replay(trades_rows, snap_rows, mode, size, fee_mult=1.0, min_edge=None, hard_max=0.95, max_disagreement=0.30):
    """Re-run decide() over recorded snapshots; first qualifying snapshot per round is the entry.
    Applies the same reasoning-engine veto as live (model vs market-mid disagreement)."""
    modes_backup = dict(MODES)
    try:
        if min_edge is not None:
            MODES["_replay"] = dict(MODES[mode], min_edge=min_edge)
            mode = "_replay"
        results = {r["ticker"]: r["result"] for r in trades_rows if r.get("result") in ("yes", "no")}
        by = defaultdict(list)
        for s in snap_rows:
            by[s["ticker"]].append(s)
        out = []
        for ticker, snaps in by.items():
            if ticker not in results:
                continue
            ref = min(snaps, key=lambda x: abs(float(x["secs_left"]) - 300))  # ~5 min out, for calibration stats
            row = dict(ticker=ticker, action="SKIP", time=min(x["time"] for x in snaps), result=results[ticker], pnl="0", fees="0", p_model=ref["p_up"],
                       p_market=str((_f(ref["yes_bid"]) + _f(ref["yes_ask"])) / 2))
            for s in sorted(snaps, key=lambda x: x["time"]):
                pu = _f(s["p_up"])
                side = "yes" if pu >= 0.5 else "no"
                sig = dict(side=side, p_side=max(pu, 1 - pu))
                q = {k: _f(s[k]) for k in ("yes_bid", "yes_ask", "no_bid", "no_ask")}
                d = decide(sig, q, float(s["secs_left"]), mode, fee_mult, hard_max)
                if not d["enter"]:
                    continue
                mid = (q["yes_bid"] + q["yes_ask"]) / 2
                if sig["p_side"] - (mid if side == "yes" else 1 - mid) > max_disagreement:
                    continue  # reasoning-engine veto
                n = max_affordable_count(size, d["price"], fee_mult)
                if n < 1:
                    continue
                fee = trade_fee(d["price"], n, fee_mult)
                won = results[ticker] == side
                pnl = (n if won else 0) - d["price"] * n - fee
                row.update(action="ENTER", side=side, count=str(n), entry_price=str(d["price"]), entry_fee=str(fee),
                           edge=str(d["edge"]), pnl=str(pnl), fees=str(fee), cashed_out="0",
                           p_model=s["p_up"], p_market=str((_f(s["yes_bid"]) + _f(s["yes_ask"])) / 2))
                break
            out.append(row)
        return out
    finally:
        MODES.clear()
        MODES.update(modes_backup)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--trades", default="trades.csv")
    ap.add_argument("--snapshots", default="snapshots.csv")
    ap.add_argument("--replay", action="store_true", help="re-decide from snapshots instead of using recorded decisions")
    ap.add_argument("--mode", default="balanced", choices=list(MODES))
    ap.add_argument("--min-edge", type=float)
    ap.add_argument("--size", type=float, default=5.0)
    ap.add_argument("--fee-multiplier", type=float, default=1.0)
    ap.add_argument("--halves", action="store_true", help="also report the first and second half (by time) separately")
    a = ap.parse_args(argv)
    try:
        rows = load_csv(a.trades)
    except FileNotFoundError:
        sys.exit(f"{a.trades} not found. Run the bot in paper mode first.")
    if a.replay:
        rows = replay(rows, load_csv(a.snapshots), a.mode, a.size, a.fee_multiplier, a.min_edge)
        print(f"[replay: mode={a.mode} min_edge={a.min_edge}; ignores loss-streak/daily-cap limits]")
    print(format_report(analyse(rows)))
    if a.halves and len(rows) >= 2:
        rows = sorted(rows, key=lambda r: r.get("time") or "")
        h = len(rows) // 2
        for name, part in (("FIRST HALF", rows[:h]), ("SECOND HALF", rows[h:])):
            m = analyse(part)
            print(f"\n--- {name}: traded {m['traded']}, win {m['win_rate'] if m['win_rate'] is None else round(m['win_rate'], 3)}, "
                  f"breakeven {m['avg_breakeven'] if m['avg_breakeven'] is None else round(m['avg_breakeven'], 3)}, "
                  f"net PnL ${m['net_pnl']:+.2f}, p(beats price) {m.get('p_vs_price') if m.get('p_vs_price') is None else round(m['p_vs_price'], 3)}")


if __name__ == "__main__":
    main()
