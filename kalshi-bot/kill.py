#!/usr/bin/env python3
"""Emergency kill switch.  python kill.py [--flatten] [--yes] [--clear]

1. Writes the KILL file: the bot's order path refuses every entry while it exists, even if
   the board is unreachable or the bot is mid-loop. (Works for paper and live.)
2. Disarms a running bot through its board (uses BOARD_TOKEN if set). Best effort.
3. If API credentials are set: cancels ALL resting orders (DELETE /portfolio/events/orders).
4. With --flatten: sells every open 15-min crypto position at the bid (reduce-only, IOC).
   Positions that cannot be sold (no bid / no fill) are reported, never silently ignored.
Exit code 0 only if every requested step succeeded.
"""
import argparse
import os
import sys

import requests

from engine import KILL_FILE
from kalshi_client import Kalshi, KalshiError, quotes
from signals import SERIES


def engage(path=KILL_FILE):
    with open(path, "w") as f:
        f.write("kill switch engaged\n")
    return True


def disarm_board(host="127.0.0.1", port=8787, token=None, timeout=3):
    h = {"X-Board": "1", "Content-Type": "application/json"}
    if token:
        h["X-Token"] = token
    r = requests.post(f"http://{host}:{port}/api/arm", json={"armed": False}, headers=h, timeout=timeout)
    return r.status_code == 200


def flatten(client):
    """Sell every held 15-min crypto position. Returns list of (ticker, ok, message)."""
    out = []
    prefixes = tuple(SERIES.values())
    for p in client.positions():
        t = p.get("ticker", "")
        n = float(p.get("position_fp") or p.get("position") or 0)
        if not t.startswith(prefixes) or n == 0:
            continue
        side, count = ("yes" if n > 0 else "no"), int(abs(round(n)))
        try:
            q = quotes(client.market(t))
            bid = q["yes_bid"] if side == "yes" else q["no_bid"]
            if not bid or bid <= 0:
                out.append((t, False, "no bid: cannot sell now (will settle at expiry)"))
                continue
            res = client.place_order(t, side, "sell", count, bid)
            filled = float(res.get("fill_count") or 0)
            out.append((t, filled >= count, f"sold {filled:g}/{count} {side} @ {bid:.3f}"))
        except KalshiError as e:
            out.append((t, False, f"error: {e}"))
    return out


def main(argv=None, client=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--flatten", action="store_true", help="also sell all open positions at the bid")
    ap.add_argument("--clear", action="store_true", help="remove the KILL file (re-allow arming)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8787)
    a = ap.parse_args(argv)
    if a.clear:
        if os.path.exists(KILL_FILE):
            os.remove(KILL_FILE)
        print("KILL file removed; bot stays disarmed until you arm it again.")
        return 0
    ok = True
    engage()
    print(f"[1] KILL file written ({KILL_FILE}): all entries refused")
    try:
        print("[2] board disarmed" if disarm_board(a.host, a.port, os.getenv("BOARD_TOKEN")) else "[2] board answered but did not disarm")
    except requests.RequestException:
        print("[2] board not reachable (fine if the bot is stopped; the KILL file still blocks it)")
    client = client or Kalshi.from_env()
    if not (client.key and client.key_id):
        print("[3] no API credentials in env: nothing to cancel on Kalshi")
        return 0
    try:
        client.cancel_all_orders()
        print("[3] cancelled all resting orders")
    except KalshiError as e:
        ok = False
        print(f"[3] CANCEL FAILED: {e}  -> cancel manually at kalshi.com NOW")
    if a.flatten:
        client.allow_orders = True  # explicit operator request
        for t, good, msg in flatten(client):
            ok &= good
            print(f"[4] {'ok  ' if good else 'FAIL'} {t}: {msg}")
    else:
        print("[4] positions left open (use --flatten to sell them)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
