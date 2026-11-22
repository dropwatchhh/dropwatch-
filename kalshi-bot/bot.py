#!/usr/bin/env python3
"""Kalshi 15-minute crypto bot. PAPER by default.

Live orders need BOTH  "trading": "live"  in the config AND the --live flag.
Credentials come from KALSHI_API_KEY_ID and KALSHI_PRIVATE_KEY_PATH (never logged).
"""
import argparse
import os
import sys
import threading
import time

import board
from engine import Ctx, State, load_config, reconcile, resolve_live, run_loop
from kalshi_client import Kalshi, KalshiError
from signals import SERIES, Feed


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--live", action="store_true", help="place REAL orders (also needs trading=live in config)")
    ap.add_argument("--arm", action="store_true", help="start armed (paper mode only; live is armed from the board)")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--host", default="127.0.0.1", help="non-loopback needs BOARD_TOKEN (use behind Tailscale/VPN)")
    ap.add_argument("--duration", type=float, default=0, help="stop after N seconds (0 = run forever)")
    a = ap.parse_args(argv)

    try:
        cfg = load_config(a.config)
    except Exception as e:
        sys.exit(f"Bad config: {e}")
    live = resolve_live(a.live, cfg)
    if a.live and not live:
        print("--live given but config trading != 'live': staying in PAPER mode.")
    if cfg["trading"] == "live" and not a.live:
        print("config says live but --live not given: staying in PAPER mode.")
    if a.arm and live:
        sys.exit("--arm is paper-only; arm a live bot from the board.")

    client = Kalshi.from_env()
    client.allow_orders = live  # the client itself refuses to place orders unless live
    client.buy_limits = (cfg["size_per_trade_usd"], cfg["hard_max_price"])  # second, independent cap on every buy
    fee_mult = cfg["fee_multiplier"] or 1.0
    try:
        if not cfg["fee_multiplier"]:
            fee_mult = client.series_fee_multiplier(SERIES[cfg["assets"][0]])
    except Exception as e:
        print(f"could not read series fee multiplier ({e}); assuming 1.0")
    st = State(cfg)
    if live:
        if not client.key:
            sys.exit("Live trading needs KALSHI_API_KEY_ID and KALSHI_PRIVATE_KEY_PATH")
        try:
            st.balance = client.balance_usd()
            reconcile(client, st)
        except KalshiError as e:
            sys.exit(f"Live startup failed (auth/reconcile): {e}")
        if st.balance < cfg["size_per_trade_usd"]:
            sys.exit(f"Balance ${st.balance:.2f} is below size_per_trade_usd")
        st.note("*** LIVE TRADING: real orders will be placed once you ARM on the board ***")
    st.armed = bool(a.arm)
    st.note(f"Starting {'LIVE' if live else 'PAPER'} | mode={cfg['mode']} | assets={cfg['assets']} | "
            f"fee_mult={fee_mult} | {'ARMED' if st.armed else 'DISARMED'}")

    ctx = Ctx(client, st, {x: Feed(x) for x in cfg["assets"]}, live, fee_mult)
    stop = threading.Event()
    deadline = time.time() + a.duration if a.duration else None
    t = threading.Thread(target=run_loop, args=(ctx, stop, deadline), daemon=True)
    t.start()
    srv = board.serve(client, st, live, a.host, a.port, fee_mult)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    st.note(f"Board: http://{a.host}:{a.port}" + ("  (token required: add ?t=TOKEN)" if os.getenv("BOARD_TOKEN") else ""))
    try:
        while t.is_alive():
            t.join(1)
    except KeyboardInterrupt:
        stop.set()
    srv.shutdown()
    st.save()
    st.note("Stopped. State saved.")


if __name__ == "__main__":
    main()
