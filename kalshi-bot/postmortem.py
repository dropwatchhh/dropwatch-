"""Automatic post-mortem for each LOSING trade. Descriptive only: it states facts and how unusual the
loss was by the model's own numbers. It never changes thresholds, limits or parameters, and nothing
reads its output back into the strategy."""
import csv
import time
from datetime import datetime, timezone

MEASURED_BASIS_BPS = 4.13   # std of Coinbase-vs-index gap measured in history.py (2026-11-08..22)


def _path_rows(snaps_path, ticker):
    try:
        with open(snaps_path, newline="") as f:
            rows = [r for r in csv.DictReader(f) if r["ticker"] == ticker]
    except FileNotFoundError:
        return []
    return sorted(rows, key=lambda r: -float(r["secs_left"]))


def build(rnd, result, final_value, pnl, snaps_path="snapshots.csv", fee=None):
    pos, snap = rnd.get("pos") or {}, rnd.get("snap") or {}
    side = pos.get("side") or rnd.get("side")
    price, count = pos.get("price"), pos.get("count")
    target = snap.get("target")
    p_up = snap.get("p_model")
    p_side = None if p_up is None else (p_up if side == "yes" else 1 - p_up)
    mkt_up = snap.get("p_market")
    mkt_side = None if mkt_up is None else (mkt_up if side == "yes" else 1 - mkt_up)
    lines, tags = [], []
    lines.append(f"Bought {count} {str(side).upper()} @ {price:.3f} (fee ${pos.get('fee', 0):.2f}); market settled {result.upper()}; "
                 f"net P&L {pnl:+.2f}.")
    if p_side is not None:
        mkt_txt = f"market mid {mkt_side:.0%}" if mkt_side is not None else "no market mid recorded"
        lines.append(f"At entry the model gave this side {p_side:.0%} ({mkt_txt}), {snap.get('secs_left')}s before close, "
                     f"distance {snap.get('z_sigma')} sigma.")
        loss_p = 1 - p_side
        lines.append(f"By the model's own numbers this loss had a {loss_p:.0%} chance (about 1 in {1 / max(loss_p, 1e-9):.0f}); "
                     f"a single loss is weak evidence either way.")
        if loss_p >= 0.10:
            tags.append("within expected variance")
        if mkt_side is not None and p_side - mkt_side >= 0.20:
            tags.append("large model-vs-market disagreement at entry")
            lines.append(f"The model was {p_side - mkt_side:.0%} more confident than the market: the market was the better forecaster here.")
    rows = _path_rows(snaps_path, rnd["ticker"])
    flips, worst = [], 0.0
    if rows and target and side:
        prev_ahead = None
        for r in rows:
            if float(r["secs_left"]) > float(snap.get("secs_left") or 1e9):
                continue
            px = float(r["price"])
            ahead = (px >= float(r["target"])) == (side == "yes")
            adverse = (float(r["target"]) - px) if side == "yes" else (px - float(r["target"]))
            worst = max(worst, adverse)
            if prev_ahead is True and not ahead:
                flips.append(float(r["secs_left"]))
            prev_ahead = ahead
        lines.append(f"After entry the worst move against the position was ${worst:,.2f} past the target (spot, Coinbase)."
                     + (f" The side lost its lead {len(flips)} time(s); last at ~{int(flips[-1])}s before close." if flips else ""))
        if flips and flips[-1] <= 120:
            tags.append("late flip (<=120s before close)")
    if final_value and target:
        margin_bps = (float(final_value) - float(target)) / float(target) * 1e4
        lines.append(f"Kalshi's final index value {float(final_value):,.2f} vs target {float(target):,.2f} = {margin_bps:+.1f} bps.")
        if abs(margin_bps) <= MEASURED_BASIS_BPS:
            tags.append("within Coinbase-vs-index gap")
            lines.append(f"That margin is inside the measured ~{MEASURED_BASIS_BPS} bps Coinbase-vs-index gap: effectively a coin-flip finish.")
    ask = snap.get("yes_ask") if side == "yes" else snap.get("no_ask")
    if ask and price and price - ask > 0.0005:
        tags.append("fill worse than quote")
        lines.append(f"Fill {price:.3f} was {price - ask:.3f} worse than the quoted ask {ask:.3f}.")
    lines.append("No thresholds, limits or model parameters were changed by this loss. Any change is a human decision after reviewing the whole sample.")
    return dict(ts=datetime.now(timezone.utc).isoformat(), ticker=rnd["ticker"], side=side, result=result, pnl=round(pnl, 4),
                tags=tags or ["no specific cause identified"], lines=lines)
