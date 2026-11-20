#!/usr/bin/env python3
"""Replay data/snapshots.jsonl through the REAL Desk class (imported, not edited), paper mode.
Baseline = trading_desk rules incl. 3% round-trip cost, stop loss, partial exit, max hold.
Risk pause/kill limits are disabled here so every signal gets a fair sample; drawdown is reported.
Split: first 70% of tokens (by time) = tune (reference only), last 30% = held-out test, evaluated once.
"""
import argparse, json, os, statistics, sys
import trading_desk as td
from strategies.candidates import CANDIDATES, NOT_TESTABLE

STEPS_PER_DAY = 4320   # 20s steps

class ReplayFeed:
    def __init__(self, rows): self.rows, self.desk = rows, None
    def new_pairs(self):
        return [r["tok"] for r in self.rows if r["start"] == self.desk.step]
    def price(self, tok):
        r = self.by_sym[tok.symbol]; i = self.desk.step - r["start"] - 1
        return r["path"][max(0, min(i, len(r["path"]) - 1))]

def make_desk(cls_trail):
    base = td.Desk
    class BtDesk(base):
        events = None
        def log(self, kind, **kw):
            kw["kind"] = kind; self.events.append(kw)
        if cls_trail:
            def manage(self):
                act, pct = cls_trail
                for addr, p in list(self.pos.items()):
                    p.token.price = self.feed.price(p.token)
                    ret = p.token.price / p.entry - 1; p.peak = max(p.peak, p.token.price)
                    C = td.CFG
                    if not p.partial and ret <= -C["stop_loss"]: self.close(addr, "stop loss")
                    elif p.partial and ret <= 0: self.close(addr, "break-even stop")
                    elif ret >= C["take_profit"]: self.close(addr, "take profit")
                    elif not p.partial and ret >= C["partial_at"]: self.take_partial(addr)
                    elif p.peak / p.entry > 1 + act and p.token.price <= p.peak * (1 - pct): self.close(addr, "trailing stop")
                    elif self.step - p.entry_step >= C["max_hold_steps"]: self.close(addr, "max hold time")
    return BtDesk

def run(rows, name=None):
    cand = CANDIDATES.get(name, {}) if name else {}
    saved = dict(td.CFG); saved_f = td.filter_agent
    td.CFG.update(log_file=os.devnull, daily_loss_limit=1.0, max_drawdown=1.0)   # no pause/kill in replay
    td.CFG.update(cand.get("cfg", {}))
    ef = cand.get("extra_filter")
    if ef: td.filter_agent = lambda t: saved_f(t) or ef(t)
    try:
        toks, by = [], {}
        for i, r in enumerate(rows):
            f = dict(r["features"]); f["symbol"] = f"{f['symbol']}#{i}"; t = td.Token(**f)
            toks.append({"tok": t, "start": r["start_step"], "path": r["path"]}); by[t.symbol] = toks[-1]
        feed = ReplayFeed(toks); feed.by_sym = by
        d = make_desk(cand.get("trail"))(feed); d.events = []; feed.desk = d
        t0 = min(x["start"] for x in toks); d.step = t0 - 1
        end = max(x["start"] + len(x["path"]) for x in toks) + 1
        curve, size = [], {}
        while d.step < end:
            if d.step % STEPS_PER_DAY == 0: d.day = "rollover"      # reset daily trade counter
            d.run_step(); curve.append(d.equity())
            for e in d.events:
                if e["kind"] == "buy": size[e["sym"]] = e["size"]
        pnl = {}
        for e in d.events:
            if e["kind"] in ("exit", "partial_exit"): pnl[e["sym"]] = pnl.get(e["sym"], 0) + e["pnl"]
        rets = {s: pnl.get(s, 0) / size[s] for s in size}
        peak, mdd = curve[0], 0
        for v in curve: peak = max(peak, v); mdd = max(mdd, 1 - v / peak)
        return {"rets": rets, "mdd": mdd, "final": d.equity()}
    finally:
        td.CFG.clear(); td.CFG.update(saved); td.filter_agent = saved_f

def stats(res):
    r = list(res["rets"].values())
    return {"trades": len(r), "win_rate": round(sum(x > 0 for x in r) / len(r), 3) if r else None,
            "avg_ret_pct": round(100 * statistics.mean(r), 2) if r else None,
            "max_drawdown_pct": round(100 * res["mdd"], 1)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/snapshots.jsonl")
    ap.add_argument("--min-tokens", type=int, default=300)
    ap.add_argument("--allow-sim", action="store_true", help="plumbing test only; output is NOT evidence")
    ap.add_argument("--out", default="data/backtest_results.json")
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(a.data)] if os.path.exists(a.data) else []
    rows = [r for r in rows if r["complete"] and r["path"]]
    sim = any(r["source"] == "sim" for r in rows)
    if sim and not a.allow_sim: sys.exit("Data contains simulated tokens; refusing (use --allow-sim for plumbing tests only).")
    if len(rows) < a.min_tokens and not a.allow_sim:
        sys.exit(f"Only {len(rows)} complete tokens recorded; need >= {a.min_tokens}. Run record.py longer. Not testing on tiny samples.")
    rows.sort(key=lambda r: (r["ts"], r["start_step"]))
    cut = int(len(rows) * 0.7); tune, test = rows[:cut], rows[cut:]
    out = {"n_tokens": len(rows), "n_tune": len(tune), "n_test": len(test), "plumbing_only": sim, "ideas": {}}
    base = run(test); out["baseline_test"] = stats(base)
    base_win = {s for s, x in base["rets"].items() if x > 0}
    for name in CANDIDATES:
        c = run(test, name); s = stats(c); r = c["rets"]
        s["blocked_baseline_winners"] = len(base_win - set(r))
        s["baseline_losers_avoided"] = len({x for x, v in base["rets"].items() if v <= 0} - set(r))
        top2 = sorted(r.values())[:-2]
        s["avg_ret_pct_without_top2"] = round(100 * statistics.mean(top2), 2) if top2 else None
        b = out["baseline_test"]["avg_ret_pct"]
        ok = (s["trades"] >= 100 and s["avg_ret_pct"] is not None and b is not None
              and s["avg_ret_pct"] > b and s["avg_ret_pct_without_top2"] is not None and s["avg_ret_pct_without_top2"] > b)
        s["verdict"] = "adopt" if ok else ("need more data" if s["trades"] < 100 else "reject")
        out["ideas"][name] = s
    for k, why in NOT_TESTABLE.items(): out["ideas"][k] = {"verdict": "need more data", "why": why}
    json.dump(out, open(a.out, "w"), indent=1); print(json.dumps(out, indent=1))

if __name__ == "__main__":
    main()
