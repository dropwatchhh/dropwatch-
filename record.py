#!/usr/bin/env python3
"""Paper-only data recorder. Saves every scanned token's features and its price path
afterwards to data/snapshots.jsonl. Does not trade, holds no keys, never imports live code paths.

  python3 record.py --feed dexscreener --steps 2000 --delay 20
"""
import argparse, json, os, time
from dataclasses import asdict
import trading_desk as td

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--feed", choices=["sim", "dexscreener"], default="dexscreener")
    ap.add_argument("--steps", type=int, default=2000)
    ap.add_argument("--delay", type=float, default=20)
    ap.add_argument("--horizon", type=int, default=90, help="steps of price path to record per token")
    ap.add_argument("--max-tracked", type=int, default=40, help="cap on tokens tracked at once (rate limits)")
    ap.add_argument("--out", default="data/snapshots.jsonl")
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    feed = td.SimFeed() if a.feed == "sim" else td.DexScreenerFeed()
    seen, track, out = set(), {}, open(a.out, "a")
    skipped = done = 0

    def flush(addr, complete):
        r = track.pop(addr)
        out.write(json.dumps({"source": a.feed, "start_step": r["start"], "ts": r["ts"],
                              "complete": complete, "features": asdict(r["tok"]),
                              "path": r["path"]}) + "\n"); out.flush()

    try:
        for step in range(1, a.steps + 1):
            for addr in list(track):                       # advance price paths
                r = track[addr]
                r["path"].append(feed.price(r["tok"]))
                if len(r["path"]) >= a.horizon:
                    flush(addr, True); done += 1
            for t in feed.new_pairs():                     # record EVERY scanned token, unfiltered
                if t.addr in seen or t.price <= 0: continue
                seen.add(t.addr)
                if len(track) >= a.max_tracked: skipped += 1; continue
                track[t.addr] = {"tok": t, "start": step, "ts": time.time(), "path": []}
            if step % 10 == 0:
                print(f"step {step} tracking={len(track)} complete={done} skipped(cap)={skipped}", flush=True)
            time.sleep(a.delay)
    except KeyboardInterrupt:
        pass
    for addr in list(track): flush(addr, False)
    print(f"done: complete={done} skipped_over_cap={skipped} -> {a.out}")

if __name__ == "__main__":
    main()
