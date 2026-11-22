#!/usr/bin/env python3
"""Build a large historical test set from public data so the strategy can be judged on
hundreds of rounds, not the handful a paper hour produces.

Sources (all public, no key needed):
  * Kalshi settled 15-min rounds: floor_strike, result, expiration_value
  * Kalshi 1-minute candlesticks per round: yes bid/ask quotes
  * Coinbase Exchange 1-minute candles: the spot proxy

For each round we reconstruct what the bot would have seen N minutes before close using
ONLY data available at that moment (spot, trailing 10-min vol, quotes) and write
snapshots in the same format the live bot records. Then:

    python history.py --rounds 600 --out hist
    python backtest.py --trades hist_trades.csv --snapshots hist_snaps.csv --replay

Limits (stated in RESULTS.md): quotes are end-of-minute bid/ask (fills assumed at the ask),
1-min spot candles replace 2 s ticks, and the hourly-ladder part of the reasoning engine
cannot be replayed (no historical ladder), only the market-mid veto.
"""
import argparse
import csv
import math
import sys
import time

import requests

from engine import SNAP_COLUMNS
from kalshi_client import Kalshi, parse_time, price_dollars
from signals import SERIES, analyze

OFFSETS_MIN = [11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
VOL_LOOKBACK = 10  # one-minute returns


def trailing_vol(closes, t, n=VOL_LOOKBACK):
    """Per-second vol from n one-minute log returns ending at t. None if any candle is missing."""
    pts = [closes.get(t - 60 * k) for k in range(n, -1, -1)]
    if any(p is None for p in pts):
        return None
    return math.sqrt(sum(math.log(b / a) ** 2 for a, b in zip(pts, pts[1:])) / (n * 60.0))


def build_rows(rounds, closes, candles, basis_bps=2.0, shrink=0.9, offsets=OFFSETS_MIN):
    """Pure function. rounds: dicts(ticker, floor_strike, close_ts, result, expiration_value).
    closes: {minute_end_ts: coinbase close}. candles: {ticker: {end_ts: (yes_bid, yes_ask)}}.
    Returns (outcome_rows, snapshot_rows, basis_gaps_bps). Features never look past time t."""
    outcomes, snaps, gaps = [], [], []
    for r in rounds:
        any_snap = False
        for m in offsets:
            t = r["close_ts"] - 60 * m
            price, q = closes.get(t), candles.get(r["ticker"], {}).get(t)
            vol = trailing_vol(closes, t)
            if price is None or q is None or vol is None:
                continue
            yb, ya = q
            if yb is None or ya is None or not 0 < ya < 1:
                continue
            sig = analyze(price, r["floor_strike"], 60 * m, vol, 0.0, None, basis_bps, shrink)
            snaps.append(dict(time=f"{t:012d}", ticker=r["ticker"], asset="BTC", secs_left=60 * m, price=price,
                              target=r["floor_strike"], vol_ps=vol, vol_scale=1.0, momentum=0.0, p_up=sig["p_up"],
                              yes_bid=yb, yes_ask=ya, no_bid=round(1 - ya, 4), no_ask=round(1 - yb, 4)))
            any_snap = True
        if any_snap:
            outcomes.append(dict(ticker=r["ticker"], action="SKIP", result=r["result"]))
        end = closes.get(r["close_ts"])
        if end and r.get("expiration_value"):
            gaps.append((end - r["expiration_value"]) / r["expiration_value"] * 1e4)
    return outcomes, snaps, gaps


# ------------------------------------------------------------------ fetching
def fetch_settled(client, series, n):
    out, cursor = [], ""
    while len(out) < n:
        d = client.req("GET", f"/markets?series_ticker={series}&status=settled&limit=1000" + (f"&cursor={cursor}" if cursor else ""))
        for m in d.get("markets", []):
            if m.get("result") in ("yes", "no") and m.get("floor_strike") and m.get("expiration_value"):
                out.append(dict(ticker=m["ticker"], floor_strike=float(m["floor_strike"]), result=m["result"],
                                close_ts=int(parse_time(m["close_time"]).timestamp()),
                                open_ts=int(parse_time(m["open_time"]).timestamp()),
                                expiration_value=float(m["expiration_value"])))
        cursor = d.get("cursor") or ""
        if not cursor:
            break
    out.sort(key=lambda r: r["close_ts"])
    return out[-n:]


def fetch_coinbase(asset, start_ts, end_ts):
    closes, t = {}, start_ts
    while t < end_ts:
        e = min(t + 300 * 60, end_ts)
        for attempt in range(5):
            r = requests.get(f"https://api.exchange.coinbase.com/products/{asset}-USD/candles",
                             params=dict(granularity=60, start=t, end=e), timeout=15)
            if r.status_code == 200:
                break
            time.sleep(1 + attempt)
        else:
            raise RuntimeError(f"coinbase candles failed ({r.status_code})")
        for c in r.json():  # [start, low, high, open, close, volume]
            closes[int(c[0]) + 60] = float(c[4])
        t = e
        time.sleep(0.15)
    return closes


def fetch_candles(client, series, rnd):
    d = client.req("GET", f"/series/{series}/markets/{rnd['ticker']}/candlesticks"
                          f"?start_ts={rnd['open_ts']}&end_ts={rnd['close_ts']}&period_interval=1")
    out = {}
    for c in d.get("candlesticks", []):
        out[int(c["end_period_ts"])] = (price_dollars(c["yes_bid"], "close"), price_dollars(c["yes_ask"], "close"))
    return out


def write_csv(path, cols, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset", default="BTC", choices=list(SERIES))
    ap.add_argument("--rounds", type=int, default=600)
    ap.add_argument("--out", default="hist")
    ap.add_argument("--basis-bps", type=float, default=2.0)
    ap.add_argument("--shrink", type=float, default=0.9)
    a = ap.parse_args(argv)
    c = Kalshi()
    rounds = fetch_settled(c, SERIES[a.asset], a.rounds)
    print(f"{len(rounds)} settled rounds {time.strftime('%F %R', time.gmtime(rounds[0]['close_ts']))} -> "
          f"{time.strftime('%F %R', time.gmtime(rounds[-1]['close_ts']))} UTC")
    closes = fetch_coinbase(a.asset, rounds[0]["open_ts"] - 15 * 60, rounds[-1]["close_ts"] + 120)
    candles = {}
    for i, r in enumerate(rounds):
        try:
            candles[r["ticker"]] = fetch_candles(c, SERIES[a.asset], r)
        except Exception as e:
            print(f"  skip {r['ticker']}: {e}", file=sys.stderr)
        if i % 100 == 99:
            print(f"  candles {i + 1}/{len(rounds)}")
    out, snaps, gaps = build_rows(rounds, closes, candles, a.basis_bps, a.shrink)
    write_csv(f"{a.out}_trades.csv", ["ticker", "action", "result"], out)
    write_csv(f"{a.out}_snaps.csv", SNAP_COLUMNS, snaps)
    print(f"wrote {len(out)} rounds, {len(snaps)} snapshots -> {a.out}_trades.csv / {a.out}_snaps.csv")
    if gaps:
        m = sum(gaps) / len(gaps)
        sd = math.sqrt(sum((g - m) ** 2 for g in gaps) / len(gaps))
        print(f"Observed Coinbase(1-min close at expiry) minus Kalshi expiration_value: mean {m:+.2f} bps, "
              f"std {sd:.2f} bps over {len(gaps)} rounds  (basis_bps in config models this gap)")


if __name__ == "__main__":
    main()
