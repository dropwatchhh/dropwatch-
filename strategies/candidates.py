"""Candidate ideas from ideas.jsonl, written from scratch as parameter sets. All default OFF:
nothing here is imported by trading_desk.py. backtest.py applies them one at a time.

Each candidate: cfg (CFG overrides), extra_filter (t -> reject reason or None), trail (activate_ret, pct).
Ideas needing data the feed lacks (holders, unique buyers, dev sells, token extensions, ladder
structure) are listed in NOT_TESTABLE and get verdict "need more data".
"""
def _ratio(t): return t.buys / max(t.sells, 1)

CANDIDATES = {
    "buysell_1_5": dict(cfg={}, extra_filter=lambda t: None if _ratio(t) >= 1.5 else "ratio<1.5"),
    "momentum_5pct": dict(cfg={}, extra_filter=lambda t: None if (t.change_5m >= 5 and _ratio(t) >= 2.0) else "not momentum"),
    "stop_30": dict(cfg={"stop_loss": 0.30}),
    "trail_50_20": dict(cfg={"trail_pct": 0.20}, trail=(0.5, 0.20)),
}
NOT_TESTABLE = {
    "dev_sell_exit": "needs dev-wallet trade data", "unique_buyers": "needs per-wallet trade data",
    "top10_35": "needs holder snapshot (recorder does not fetch on-chain data yet)",
    "top1_50": "needs holder snapshot", "t22_extensions": "needs mint account snapshot",
    "fee_close_auth": "needs mint account snapshot", "ladder_1_8_3": "different exit structure; not implemented",
}
