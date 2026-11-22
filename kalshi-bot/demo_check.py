#!/usr/bin/env python3
"""Gate 2 harness for Kalshi's DEMO environment (fake money). NOT RUN in the readiness review:
it needs demo API credentials, which only the account holder can create.

Setup (once):  create a demo account + demo API key (https://docs.kalshi.com/getting_started/demo_env.md)
  export KALSHI_BASE_URL=https://external-api.demo.kalshi.co/trade-api/v2
  export KALSHI_API_KEY_ID=<DEMO key id>   KALSHI_PRIVATE_KEY_PATH=<DEMO key pem>
  python demo_check.py

Hard guard: refuses to run unless the base URL is a demo host. Each step prints PASS/FAIL with the
raw numbers; compare against the demo web UI too. Orders are tiny (1-2 contracts).
"""
import os
import sys
import time
from urllib.parse import urlparse

from kalshi_client import Kalshi, KalshiError, quotes, trade_fee, v2_order_body
from signals import SERIES

results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")


def main():
    host = urlparse(os.getenv("KALSHI_BASE_URL", "")).hostname or ""
    if not host.endswith("demo.kalshi.co"):
        sys.exit("REFUSING: KALSHI_BASE_URL must be a demo.kalshi.co host. This script never touches production.")
    c = Kalshi.from_env()
    if not (c.key and c.key_id):
        sys.exit("Set the DEMO KALSHI_API_KEY_ID / KALSHI_PRIVATE_KEY_PATH.")
    c.allow_orders = True
    c.buy_limits = (5.0, 0.99)  # tiny demo orders only
    bal0 = c.balance_usd()
    print(f"demo balance ${bal0:.2f}")
    m = c.open_market(SERIES["BTC"])
    if not m:
        sys.exit("no open KXBTC15M market on demo right now")
    t, q = m["ticker"], quotes(m)
    ask = q["yes_ask"]
    # 1. immediate fill: compare bot's view with Kalshi's own fill record (fee + price fields)
    if ask and 0 < ask < 0.99:
        res = c.place_order(t, "yes", "buy", 2, ask)
        n = float(res.get("fill_count") or 0)
        time.sleep(1.5)
        fills = c.fills(res.get("order_id"))
        fee_api = sum(float(f.get("fee_cost") or 0) for f in fills)
        cnt_api = sum(float(f.get("count_fp") or 0) for f in fills)
        px_api = (sum(float(f["yes_price_dollars"]) * float(f["count_fp"]) for f in fills) / cnt_api) if cnt_api else None
        print("  order response:", {k: res.get(k) for k in ("fill_count", "average_fill_price", "average_fee_paid")})
        print("  fills endpoint:", dict(count=cnt_api, avg_yes_price=px_api, fee_cost=fee_api))
        check("fill count matches fills endpoint", abs(n - cnt_api) < 1e-6)
        if px_api is not None:
            check("fill price: response vs fills endpoint", abs(float(res.get("average_fill_price") or px_api) - px_api) < 1e-4)
            model = trade_fee(px_api, cnt_api)
            check("bot fee model vs Kalshi fee_cost (the 0.07 coefficient)", abs(model - fee_api) <= 0.011,
                  f"model ${model:.4f} vs api ${fee_api:.4f}")
        # 2. cash-out including thin book: sell everything at the bid, then try to oversell
        pos = [p for p in c.positions() if p.get("ticker") == t]
        held = abs(float(pos[0].get("position_fp") or 0)) if pos else 0
        bid = quotes(c.market(t))["yes_bid"]
        if held and bid:
            r2 = c.place_order(t, "yes", "sell", int(held), bid)
            check("cash-out sells reduce-only at bid", float(r2.get("fill_count") or 0) > 0, str(r2.get("fill_count")))
            try:
                r3 = c.place_order(t, "yes", "sell", int(held) + 50, bid)   # reduce_only caps at position
                check("oversell is capped by reduce_only", float(r3.get("fill_count") or 0) == 0)
            except KalshiError as e:
                check("oversell rejected", True, str(e))
    # 3. resting order then cancel-all (kill switch path)
    body = v2_order_body(t, "yes", "buy", 1, 0.02)
    body["time_in_force"] = "good_till_canceled"           # demo-only: rest it so cancel can be tested
    c.req("POST", "/portfolio/events/orders", body, auth=True)
    c.cancel_all_orders()
    time.sleep(1)
    check("cancel_all leaves no resting orders", not c.req("GET", "/portfolio/orders?status=resting", auth=True).get("orders"))
    # 4. insufficient balance
    try:
        c.place_order(t, "yes", "buy", 10_000_000, 0.9)
        check("insufficient balance rejected", False, "order was accepted!")
    except KalshiError as e:
        check("insufficient balance rejected", e.status == 400, f"{e}")
    print("\nNOT automated here (do by hand and record): partial fill on a thin book; an order sent in the last seconds "
          "before close (expect market_inactive / 409); settlement PnL vs the demo UI.")
    print("GATE 2 (automated part):", "PASS" if all(results) else "FAIL")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
