#!/usr/bin/env python3
"""Gate 3 scorecard. Computes every criterion mechanically; prints PASS/FAIL per item.

  python gate3.py --source paper  --trades trades.csv --log paper_run.log
  python gate3.py --source history --trades hist14_trades.csv --snapshots hist14_snaps.csv

Only --source paper can yield GO: a historical replay is evidence, not paper trading.
Pessimistic fills: entries pay ask + 1 tick. (The strategy holds to settlement; it has no
automated stop-loss, so the 'sell at bid - 1 tick' rule only applies to manual cash-outs,
which are charged bid - 1 tick below when present.)
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone

import backtest as bt
from engine import DEFAULTS
from kalshi_client import trade_fee


def _ts(r):
    t = r.get("time") or ""
    try:
        return datetime.fromisoformat(t).timestamp()
    except ValueError:
        try:
            return float(t)
        except ValueError:
            return None


def violations(rows, cfg):
    """Re-check the risk limits against what the bot actually did (paper/live trades.csv)."""
    out, pnl_by_day, streak = [], {}, 0
    ents = sorted((r for r in rows if r.get("action") == "ENTER" and r.get("count")), key=lambda r: r.get("time") or "")
    for r in ents:
        price, n, fee = float(r["entry_price"]), float(r["count"]), float(r["entry_fee"] or 0)
        day = (r.get("time") or "")[:10]
        if price * n + fee > cfg["size_per_trade_usd"] + 1e-6:
            out.append(f"{r['ticker']}: cost {price * n + fee:.2f} > size cap")
        if price > cfg["hard_max_price"] + 1e-9:
            out.append(f"{r['ticker']}: price {price} > hard max")
        if pnl_by_day.get(day, 0.0) <= -cfg["daily_loss_cap_usd"]:
            out.append(f"{r['ticker']}: entered after daily loss cap")
        if streak >= cfg["max_losses_in_row"]:
            out.append(f"{r['ticker']}: entered after {streak} losses in a row")
        p = float(r["pnl"] or 0)
        pnl_by_day[day] = pnl_by_day.get(day, 0.0) + p
        streak = streak + 1 if p < 0 else (0 if p > 0 else streak)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["paper", "history"], required=True)
    ap.add_argument("--trades", required=True)
    ap.add_argument("--snapshots")
    ap.add_argument("--log")
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--mode", default=None)
    a = ap.parse_args(argv)
    cfg = {**DEFAULTS, **json.load(open(a.config))}
    mode = a.mode or cfg["mode"]
    rows = bt.load_csv(a.trades)
    if a.source == "history":
        snaps = bt.load_csv(a.snapshots)
        rows = bt.replay(rows, snaps, mode, cfg["size_per_trade_usd"], 1.0, None, cfg["hard_max_price"],
                         cfg["max_disagreement"], slip_ticks=1)
    else:   # paper: re-price entries one tick worse, using the recorded quotes
        adj = []
        for r in rows:
            if r.get("action") == "ENTER" and r.get("count"):
                px = round(float(r["entry_price"]) + bt.tick_at(float(r["entry_price"])), 4)
                n = float(r["count"])
                fee = trade_fee(px, n)
                won = (r["result"] == r["side"]) and r.get("cashed_out") != "1"
                gross = (n if won else 0.0) if r.get("cashed_out") != "1" else float(r["pnl"]) + float(r["entry_price"]) * n + float(r["entry_fee"])
                r = dict(r, entry_price=str(px), entry_fee=str(fee), fees=str(fee), pnl=str(gross - px * n - fee))
            adj.append(r)
        rows = adj
    m = bt.analyse(rows)
    times = [t for t in (_ts(r) for r in rows) if t]
    span_days = (max(times) - min(times)) / 86400 if times else 0
    srt = sorted(rows, key=lambda r: r.get("time") or "")
    h = len(srt) // 2
    halves = [bt.analyse(srt[:h]), bt.analyse(srt[h:])]
    ci = m.get("pnl_per_trade_ci95")
    crashes = viol = None
    if a.source == "paper":
        viol = violations(bt.load_csv(a.trades), cfg)
        if a.log:
            txt = open(a.log, errors="ignore").read()
            crashes = len(re.findall(r"Traceback|loop error|HALTED", txt))
    checks = [
        ("Source is real paper trading (not a replay)", a.source == "paper", a.source),
        ("Duration >= 14 days", span_days >= 14, f"{span_days:.1f} days"),
        (">= 300 trades", m["traded"] >= 300, f"{m['traded']} trades"),
        ("0 unhandled crashes / halts in logs", crashes == 0 if crashes is not None else False,
         "no log supplied" if crashes is None else f"{crashes} found"),
        ("0 risk-limit violations", viol == [] if viol is not None else False,
         "not checkable on a replay" if viol is None else f"{len(viol)} found"),
        ("Net PnL > 0 after fees + 1-tick slippage", m["net_pnl"] > 0, f"${m['net_pnl']:+.2f}"),
        ("Bootstrap 95% CI lower bound of PnL/trade > 0", bool(ci and ci[0] > 0), "n/a" if not ci else f"[{ci[0]:+.3f}, {ci[1]:+.3f}]"),
        ("Brier(model) < Brier(market mid)", bool(m.get("calib_n")) and m["brier_model"] < m["brier_market"],
         "n/a" if not m.get("calib_n") else f"{m['brier_model']:.4f} vs {m['brier_market']:.4f}"),
        ("Brier better in 2nd half (out-of-sample)", bool(halves[1].get("calib_n")) and halves[1]["brier_model"] < halves[1]["brier_market"],
         "n/a" if not halves[1].get("calib_n") else f"{halves[1]['brier_model']:.4f} vs {halves[1]['brier_market']:.4f}"),
        ("Both halves net PnL > 0", all(x["net_pnl"] > 0 for x in halves), " / ".join(f"${x['net_pnl']:+.2f}" for x in halves)),
        ("Max drawdown < 3 x daily loss cap", m["max_drawdown"] < 3 * cfg["daily_loss_cap_usd"],
         f"${m['max_drawdown']:.2f} vs ${3 * cfg['daily_loss_cap_usd']:.0f}"),
    ]
    print(f"Gate 3 scorecard ({a.source}, mode={mode}, rounds={m['rounds']}, trades={m['traded']})")
    for name, ok, ev in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {ev}")
    allok = all(ok for _, ok, _ in checks)
    print("GATE 3:", "PASS" if allok else "FAIL")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
