#!/usr/bin/env python3
"""Pre-flight checks that must pass before LIVE can be enabled (and keep passing while it is on).

  python preflight.py demo     # run the DEMO test order. Needs ONLY KALSHI_DEMO_* variables in this process.
                               # Writes preflight.json; the live bot (which holds only KALSHI_LIVE_*) reads it.

The shard check runs inside the live process with the live client. Crypto markets live on exchange shard 2 and
Kalshi requires that shard to be funded before ordering; a balance sitting in another shard cannot trade them.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

from kalshi_client import KalshiError, quotes, trade_fee
from signals import SERIES

DEMO_MAX_AGE = 24 * 3600     # the demo test order must be at most a day old
SHARD_TOL = 1e-9


def _write(path, d):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(d, f)
    os.replace(tmp, path)


# ------------------------------------------------------------------ shard check (live client)
def shard_check(client, market, need_usd):
    """Is there >= need_usd on the exchange shard this market trades on?"""
    r = dict(name="shard", ts=time.time(), ok=False, need_usd=need_usd)
    try:
        shard = market.get("exchange_index")
        if shard is None:
            r["detail"] = "market has no exchange_index; cannot verify the shard"
            return r
        bal = client.balance_detail()
        bd = {int(b["exchange_index"]): float(b["balance"]) for b in bal.get("balance_breakdown") or []}
        r.update(market_shard=shard, shard_balance=bd.get(int(shard)), total_balance=float(bal.get("balance_dollars") or bal["balance"] / 100))
        if not bd:
            r["detail"] = "balance_breakdown missing; cannot verify the shard balance"
        elif bd.get(int(shard), 0.0) + SHARD_TOL < need_usd:
            r["detail"] = (f"only ${bd.get(int(shard), 0.0):.2f} on exchange shard {shard} (need ${need_usd:.2f}); other shards: "
                           f"{ {k: v for k, v in bd.items() if k != int(shard)} }. Move funds to shard {shard} at "
                           f"kalshi.com/account/exchange-indexes")
        else:
            r.update(ok=True, detail=f"${bd[int(shard)]:.2f} available on shard {shard}")
    except (KalshiError, KeyError, ValueError, TypeError) as e:
        r["detail"] = f"shard check failed: {type(e).__name__}: {e}"
    return r


# ------------------------------------------------------------------ demo test order (demo client, separate process)
def demo_test_order(demo, sleep=time.sleep):
    """Buy 1 contract on DEMO, verify what Kalshi recorded (count, price, fee) against the order response and our
    fee model, then sell it back. ok only if everything lines up."""
    out = dict(name="demo_order", ts=time.time(), ok=False, steps=[], base_host=urlparse(demo.base).hostname,
               key_fingerprint=getattr(demo, "fingerprint", None))

    def step(name, ok, detail=""):
        out["steps"].append(dict(name=name, ok=bool(ok), detail=detail))
        return ok

    if not (out["base_host"] or "").endswith("demo.kalshi.co"):
        step("environment is demo", False, str(out["base_host"]))
        return out
    demo.allow_orders, demo.buy_limits = True, (2.0, 0.99, 1)
    try:
        m = demo.open_market(SERIES["BTC"])
        if not m:
            step("open demo KXBTC15M market", False, "none open")
            return out
        q = quotes(m)
        ask = q["yes_ask"]
        if not (ask and 0.02 < ask < 0.98 and (q["yes_ask_size"] or 0) >= 1):
            step("liquid ask on demo", False, f"ask={ask} size={q['yes_ask_size']}")
            return out
        res = demo.place_order(m["ticker"], "yes", "buy", 1, ask)
        step("buy 1 YES at the ask (IOC)", float(res.get("fill_count") or 0) >= 1, f"fill_count={res.get('fill_count')}")
        fills = []
        for _ in range(5):
            sleep(1.5)
            fills = demo.fills(res.get("order_id"))
            if fills:
                break
        cnt = sum(float(f["count_fp"]) for f in fills)
        px = sum(float(f["yes_price_dollars"]) * float(f["count_fp"]) for f in fills) / cnt if cnt else None
        fee = sum(float(f.get("fee_cost") or 0) for f in fills)
        step("fills endpoint shows the order", cnt >= 1, f"count={cnt}")
        if px is not None:
            step("fill price matches response", abs(float(res.get("average_fill_price") or px) - px) < 5e-4,
                 f"response {res.get('average_fill_price')} vs fills {px:.4f}")
            model = trade_fee(px, cnt)
            out["fee_model_vs_api"] = dict(model=model, api=fee)
            step("fee model matches Kalshi fee_cost", abs(model - fee) <= 0.0101, f"model ${model:.4f} vs API ${fee:.4f}")
        bid = quotes(demo.market(m["ticker"]))["yes_bid"]
        if bid and bid > 0:
            r2 = demo.place_order(m["ticker"], "yes", "sell", 1, bid)
            step("cash-out sells back (reduce-only IOC)", float(r2.get("fill_count") or 0) >= 1, f"fill_count={r2.get('fill_count')}")
        else:
            step("cash-out sells back", False, "no bid on demo")
    except KalshiError as e:
        step("no API error", False, str(e))
    out["ok"] = bool(out["steps"]) and all(s["ok"] for s in out["steps"])
    return out


def save_demo_result(path, res):
    _write(path, res)


def demo_fresh(path, live_fingerprint=None, now=None, max_age=DEMO_MAX_AGE):
    """Is there a recent passing demo test order, made with a different key and a demo host?"""
    try:
        d = json.load(open(path))
    except Exception:
        return False, "no demo test order recorded (run `python preflight.py demo` with only KALSHI_DEMO_* set)"
    if not d.get("ok"):
        return False, "the last demo test order FAILED"
    if not (d.get("base_host") or "").endswith("demo.kalshi.co"):
        return False, "recorded demo result is not from a demo host"
    if live_fingerprint and d.get("key_fingerprint") == live_fingerprint:
        return False, "demo test used the same key as live"
    age = (now or time.time()) - d.get("ts", 0)
    if age > max_age:
        return False, f"demo test order is {age / 3600:.0f}h old (max {max_age // 3600}h): re-run it"
    return True, f"passed {age / 60:.0f} min ago"


def main(argv=None):
    import credentials
    argv = argv if argv is not None else sys.argv[1:]
    if argv != ["demo"]:
        sys.exit("usage: python preflight.py demo")
    try:
        demo = credentials.load("demo")
    except credentials.CredentialError as e:
        sys.exit(f"DEMO credentials problem: {e}")
    res = demo_test_order(demo)
    save_demo_result(os.getenv("PREFLIGHT_FILE", "preflight.json"), res)
    for s in res["steps"]:
        print(f"[{'PASS' if s['ok'] else 'FAIL'}] {s['name']} {s['detail']}")
    print("DEMO TEST ORDER:", "PASS" if res["ok"] else "FAIL")
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
