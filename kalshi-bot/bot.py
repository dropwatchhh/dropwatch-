#!/usr/bin/env python3
"""Kalshi 15-minute crypto bot. PAPER by default.

Live orders need BOTH  "trading": "live"  in the config AND the --live flag.
Live credentials come ONLY from KALSHI_LIVE_API_KEY_ID / KALSHI_LIVE_PRIVATE_KEY_PATH (never logged). Demo credentials
(KALSHI_DEMO_*) belong to a separate process (preflight.py). LIVE starts OFF and is enabled from the Trading tab.
"""
import argparse
import os
import sys
import threading
import time

import board
import credentials
from engine import Ctx, State, load_config, reconcile, resolve_live, run_loop
from kalshi_client import KalshiError
from livelog import Ledger
from pilot import ASSETS_ALLOWED, PILOT_MAX, Pilot
from signals import SERIES, Feed


def make_client(live):
    """Paper: public market data only, no credentials are even read. Live: ONLY the KALSHI_LIVE_* variables."""
    return credentials.load("live") if live else credentials.public_client("live")


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

    if live and list(cfg["assets"]) != list(ASSETS_ALLOWED):
        sys.exit(f"The live pilot trades {list(ASSETS_ALLOWED)} only (fees/shard behaviour verified for BTC); config has {cfg['assets']}.")
    try:
        client = make_client(live)
    except credentials.CredentialError as e:
        sys.exit(f"Credentials: {e}")
    client.allow_orders = live  # the client itself refuses to place orders unless live
    fee_mult, fee_verified = cfg["fee_multiplier"] or 1.0, False
    try:
        if not cfg["fee_multiplier"]:
            fee_mult = client.series_fee_multiplier(SERIES[cfg["assets"][0]])
        fee_verified = True
    except Exception as e:
        if live:
            sys.exit(f"Live pilot needs the series fee schedule verified from Kalshi: {e}")
        print(f"could not read series fee multiplier ({e}); assuming 1.0")
    st = State(cfg)
    st.ledger = Ledger()
    if live:
        st.live, st.pilot = True, Pilot()          # LIVE is OFF until typed in on the Trading tab
        stake = min(cfg["size_per_trade_usd"], st.pilot.limits["stake_usd"])
        client.buy_limits = (stake, cfg["hard_max_price"], int(st.pilot.limits["contracts"]))  # independent cap on every buy
        try:
            st.balance = client.balance_usd()
            reconcile(client, st)
        except KalshiError as e:
            sys.exit(f"Live startup failed (auth/reconcile): {e}")
        if st.balance < stake:
            sys.exit(f"Balance ${st.balance:.2f} is below the pilot stake ${stake:.2f}")
        st.note("*** LIVE PILOT loaded. LIVE is OFF: nothing will trade until you enable it on the Trading tab ***")
    st.armed = bool(a.arm)
    st.note(f"Starting {'LIVE (locked)' if live else 'PAPER'} | mode={cfg['mode']} | assets={cfg['assets']} | "
            f"fee_mult={fee_mult} | {'ARMED' if st.armed else 'DISARMED'}")

    ctx = Ctx(client, st, {x: Feed(x) for x in cfg["assets"]}, live, fee_mult, fee_verified=fee_verified)
    stop = threading.Event()
    deadline = time.time() + a.duration if a.duration else None
    t = threading.Thread(target=run_loop, args=(ctx, stop, deadline), daemon=True)
    t.start()
    srv = board.serve(client, st, live, a.host, a.port, fee_mult, ctx=ctx)
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
