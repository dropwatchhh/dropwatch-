"""LIVE pilot: typed enable, readiness (demo order + shard), banners, STOP, ledger, verification, post-mortems."""
import copy
import json
import os
import threading
import time
from http.server import ThreadingHTTPServer

import pytest
import requests

import board
import credentials
import pilot as pl
import preflight
from engine import Ctx, cash_out, enter, finalize_round, verify_fill, verify_settlements
from kalshi_client import KalshiError
from livelog import Ledger
from signals import Feed, MODES
from tests.helpers import FakeClient, mklive, mkmarket, mkround, mkstate, strong
from tests.net import Resp, Script, good_handler
from tests.test_pilot_core import env, keys  # noqa: F401  (fixtures)

T = "KXBTC15M-T1"
H = {"X-Board": "1"}


def write_demo(path, ok=True, age=0, host="external-api.demo.kalshi.co", fp="demo-fingerprint"):
    json.dump(dict(name="demo_order", ok=ok, ts=time.time() - age, base_host=host, key_fingerprint=fp, steps=[]), open(path, "w"))


class Stack:
    pass


def live_stack(tmp_path, keys, demo="ok", shard_balance="10.0000", enabled=False, extra=None):
    s = Stack()
    s.client = credentials.load("live", env(keys))
    s.bal = {"balance": 1000, "balance_dollars": "10.0000", "balance_breakdown": [
        {"exchange_index": 0, "balance": "0.0000"}, {"exchange_index": 2, "balance": shard_balance}]}
    s.market = mkmarket(T, .70, .72, strike=99000.0)
    s.market["exchange_index"] = 2
    s.fail = {}

    def ex(method, url):
        if "/portfolio/balance" in url:
            return Resp(200, s.bal)
        for key, resp in s.fail.items():
            if key in url or key == method:
                return resp
        return extra(method, url) if extra else None
    s.sess = Script(good_handler(s.market, extra=ex))
    s.client.s, s.client.sleep = s.sess, (lambda x: None)
    s.client.allow_orders, s.client.buy_limits = True, (1.0, 0.95, 1)
    s.st = mklive(tmp_path, enabled=enabled)
    s.st.armed = False                                    # the real bot always starts disarmed
    s.pf = str(tmp_path / "preflight.json")
    if demo == "ok":
        write_demo(s.pf)
    elif demo == "failed":
        write_demo(s.pf, ok=False)
    elif demo == "stale":
        write_demo(s.pf, age=25 * 3600)
    elif demo == "samekey":
        write_demo(s.pf, fp=s.client.fingerprint)
    elif demo == "prodhost":
        write_demo(s.pf, host="api.elections.kalshi.com")
    s.ctx = Ctx(s.client, s.st, {"BTC": Feed("BTC")}, True, 1.0, preflight_path=s.pf, fee_verified=True)
    s.srv = ThreadingHTTPServer(("127.0.0.1", 0), board.make_handler(s.client, s.st, True, 1.0, s.ctx))
    threading.Thread(target=s.srv.serve_forever, daemon=True).start()
    s.url = f"http://127.0.0.1:{s.srv.server_port}"
    return s


@pytest.fixture
def clean_env(monkeypatch):
    monkeypatch.delenv("BOARD_TOKEN", raising=False)


def post(s, path, body, headers=H):
    return requests.post(s.url + path, json=body, headers=headers)


# ------------------------------------------------------------------ 4. typed enable + readiness + banner
def test_enable_needs_the_exact_phrase_and_everything_ready(tmp_path, keys, clean_env):
    s = live_stack(tmp_path, keys)
    try:
        assert post(s, "/api/live/enable", {"phrase": "enable live trading with real money"}).status_code == 400   # case matters
        assert post(s, "/api/live/enable", {"phrase": ""}).status_code == 400
        assert post(s, "/api/live/enable", {}).status_code == 400
        assert not s.st.pilot.live_enabled
        r = post(s, "/api/live/enable", {"phrase": pl.ENABLE_PHRASE})
        assert r.status_code == 200 and s.st.pilot.live_enabled and not s.st.armed     # enabled but NOT armed
        evs = [e["event"] for e in s.st.ledger.events()]
        assert evs.count("live_enable_refused") >= 3 and "live_enabled" in evs
    finally:
        s.srv.shutdown()


@pytest.mark.parametrize("variant,expect", [("missing", "demo test order"), ("failed", "FAILED"), ("stale", "old"),
                                            ("samekey", "same key"), ("prodhost", "not from a demo host")])
def test_demo_test_order_must_have_passed_recently_with_a_different_key(tmp_path, keys, clean_env, variant, expect):
    s = live_stack(tmp_path, keys, demo=variant)
    try:
        r = post(s, "/api/live/enable", {"phrase": pl.ENABLE_PHRASE})
        assert r.status_code == 400 and expect in r.json()["error"] and not s.st.pilot.live_enabled
    finally:
        s.srv.shutdown()


def test_shard_check_blocks_when_funds_are_on_the_wrong_shard(tmp_path, keys, clean_env):
    s = live_stack(tmp_path, keys, shard_balance="0.0000")
    try:
        r = post(s, "/api/live/enable", {"phrase": pl.ENABLE_PHRASE})
        assert r.status_code == 400 and "shard" in r.json()["error"].lower() and "exchange-indexes" in r.json()["error"]
        assert not s.st.pilot.live_enabled
    finally:
        s.srv.shutdown()


@pytest.mark.parametrize("what", ["killfile", "hardstop", "halted", "notbtc"])
def test_other_blockers(tmp_path, keys, clean_env, what):
    s = live_stack(tmp_path, keys)
    try:
        if what == "killfile":
            open(s.st.kill_path, "w").close()
        elif what == "hardstop":
            s.st.pilot.record_pnl(-5)
        elif what == "halted":
            s.st.halted = "unknown order"
        else:
            s.st.cfg["assets"] = ["BTC", "ETH"]
        assert post(s, "/api/live/enable", {"phrase": pl.ENABLE_PHRASE}).status_code == 400 and not s.st.pilot.live_enabled
    finally:
        s.srv.shutdown()
        if what == "killfile":
            os.remove(s.st.kill_path)


def test_red_live_banner_and_stop_button_on_every_page(tmp_path, keys, clean_env):
    s = live_stack(tmp_path, keys)
    try:
        for path in ("/", "/trading", "/log"):
            html = requests.get(s.url + path).text
            assert 'id=banner class="locked"' in html and "STOP TRADING NOW" in html, path
        post(s, "/api/live/enable", {"phrase": pl.ENABLE_PHRASE})
        for path in ("/", "/trading", "/log"):
            html = requests.get(s.url + path).text
            assert 'id=banner class="live"' in html and "LIVE — REAL MONEY" in html and "STOP TRADING NOW" in html, path
        assert requests.get(s.url + "/api/status").json()["live_enabled"] is True
    finally:
        s.srv.shutdown()


def test_paper_pages_show_paper_banner_and_no_live_endpoints(tmp_path, clean_env):
    st = mkstate(tmp_path, armed=False)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), board.make_handler(FakeClient(), st, False))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_port}"
    try:
        assert 'class="paper"' in requests.get(url + "/trading").text
        assert requests.post(url + "/api/live/enable", json={"phrase": pl.ENABLE_PHRASE}, headers=H).status_code == 404
    finally:
        srv.shutdown()


def test_cannot_arm_a_live_process_until_live_is_enabled(tmp_path, keys, clean_env):
    s = live_stack(tmp_path, keys)
    try:
        assert post(s, "/api/arm", {"armed": True}).status_code == 409 and not s.st.armed
        post(s, "/api/live/enable", {"phrase": pl.ENABLE_PHRASE})
        assert post(s, "/api/arm", {"armed": True}).status_code == 200 and s.st.armed
    finally:
        s.srv.shutdown()


def test_live_switches_itself_off_if_a_check_stops_passing(tmp_path, keys, clean_env):
    s = live_stack(tmp_path, keys)
    try:
        post(s, "/api/live/enable", {"phrase": pl.ENABLE_PHRASE})
        s.st.armed = True
        s.ctx.ready_at = 0
        s.ctx.periodic(now=time.time())
        assert s.st.pilot.live_enabled and s.st.armed                 # still healthy
        s.bal["balance_breakdown"][1]["balance"] = "0.0000"           # funds moved off the shard
        s.ctx.ready_at = 0
        s.ctx.periodic(now=time.time())
        assert not s.st.pilot.live_enabled and not s.st.armed
        ev = [e for e in s.st.ledger.events() if e["event"] == "live_disabled"]
        assert ev and "shard" in ev[-1]["reason"].lower()
    finally:
        s.srv.shutdown()


def test_limits_endpoint_only_lowers(tmp_path, keys, clean_env):
    s = live_stack(tmp_path, keys)
    try:
        assert post(s, "/api/limits/lower", {"name": "stake_usd", "value": 0.5}).status_code == 200
        r = post(s, "/api/limits/lower", {"name": "stake_usd", "value": 1.0})
        assert r.status_code == 400 and "LOWERED" in r.json()["error"] and s.st.pilot.limits["stake_usd"] == 0.5
        assert post(s, "/api/limits/lower", {"name": "hard_stop_usd", "value": 50}).status_code == 400
        assert post(s, "/api/limits/lower", {"name": "contracts", "value": "lots"}).status_code == 400
    finally:
        s.srv.shutdown()


def test_hard_stop_reset_endpoint_two_steps(tmp_path, keys, clean_env):
    s = live_stack(tmp_path, keys)
    try:
        s.st.pilot.record_pnl(-5)
        assert post(s, "/api/hardstop/reset", {"phrase": pl.RESET_PHRASE_2}).status_code == 400
        assert post(s, "/api/hardstop/reset", {"phrase": pl.RESET_PHRASE_1}).json()["stage"] == "step1_ok"
        assert s.st.pilot.hard_stopped
        assert post(s, "/api/hardstop/reset", {"phrase": pl.RESET_PHRASE_2}).json()["stage"] == "reset"
        assert not s.st.pilot.hard_stopped and not s.st.pilot.live_enabled
        t = requests.get(s.url + "/api/trading").json()
        assert t["enable_phrase"] == pl.ENABLE_PHRASE and not t["pilot"]["hard_stopped"]
    finally:
        s.srv.shutdown()


def test_pilot_endpoints_need_the_board_token_when_set(tmp_path, keys, monkeypatch):
    monkeypatch.setenv("BOARD_TOKEN", "z" * 20)
    s = live_stack(tmp_path, keys)
    try:
        for path, body in (("/api/live/enable", {"phrase": pl.ENABLE_PHRASE}), ("/api/stop", {}), ("/api/limits/lower", {"name": "stake_usd", "value": .5})):
            assert post(s, path, body).status_code == 401
        assert requests.get(s.url + "/api/trading").status_code == 401 and requests.get(s.url + "/api/ledger").status_code == 401
        assert not s.st.pilot.live_enabled
    finally:
        s.srv.shutdown()


# ------------------------------------------------------------------ 5. STOP TRADING NOW
def test_stop_cancels_all_resting_orders_disarms_and_locks(tmp_path, keys, clean_env):
    s = live_stack(tmp_path, keys)
    try:
        post(s, "/api/live/enable", {"phrase": pl.ENABLE_PHRASE})
        s.st.armed = True
        r = post(s, "/api/stop", {}).json()
        assert r["ok"] and any("cancelled ALL resting live orders" in x for x in r["steps"])
        assert [c for c in s.sess.calls if c[0] == "DELETE" and c[1].endswith("/portfolio/events/orders")]
        assert not s.st.armed and not s.st.pilot.live_enabled and os.path.exists(s.st.kill_path)
        assert any(e["event"] == "stop_pressed" and e["cancel_ok"] for e in s.st.ledger.events())
        assert post(s, "/api/arm", {"armed": True}).status_code == 409           # stays locked until kill.py --clear
    finally:
        s.srv.shutdown()
        os.path.exists(s.st.kill_path) and os.remove(s.st.kill_path)


def test_stop_still_stops_and_says_so_loudly_when_cancel_fails(tmp_path, keys, clean_env):
    s = live_stack(tmp_path, keys)
    try:
        post(s, "/api/live/enable", {"phrase": pl.ENABLE_PHRASE})
        s.st.armed = True
        s.fail["DELETE"] = Resp(500)
        r = post(s, "/api/stop", {}).json()
        assert r["ok"] is False and any("CANCEL FAILED" in x for x in r["steps"])
        assert not s.st.armed and not s.st.pilot.live_enabled
    finally:
        s.srv.shutdown()
        os.path.exists(s.st.kill_path) and os.remove(s.st.kill_path)


def test_stop_in_paper_does_not_touch_any_account(tmp_path, clean_env, monkeypatch):
    monkeypatch.chdir(tmp_path)
    st = mkstate(tmp_path, armed=True)
    c = FakeClient()
    c.cancel_all_orders = lambda: (_ for _ in ()).throw(AssertionError("no account should be touched in paper"))
    srv = ThreadingHTTPServer(("127.0.0.1", 0), board.make_handler(c, st, False))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        r = requests.post(f"http://127.0.0.1:{srv.server_port}/api/stop", json={}, headers=H).json()
        assert r["ok"] and not st.armed and any("nothing to cancel" in x for x in r["steps"])
    finally:
        srv.shutdown()


# ------------------------------------------------------------------ 6. ledger, fill/settlement verification, real P&L
def test_order_is_logged_before_it_is_sent_and_after_with_the_result(tmp_path, keys):
    s = live_stack(tmp_path, keys, enabled=True)
    s.srv.shutdown()
    s.st.armed = True
    seen = {}

    def ex(method, url):
        if method == "POST":
            seen["before"] = [e["event"] for e in s.st.ledger.events()]
    s.sess.handler = good_handler(s.market, extra=ex)
    mkround(s.st)
    assert enter(s.client, s.st, True, T, "yes", .72, 50, 1.0, "t", signal=strong())
    assert "order_sent" in seen["before"]                                     # write-ahead: logged before the POST
    ev = [e["event"] for e in s.st.ledger.events()]
    assert ev[:3] == ["order_sent", "order_result", "fill_check"] and s.st.ledger.events()[2]["ok"] is True


def test_logged_order_contains_the_signal_checks_but_no_secrets(tmp_path):
    lg = Ledger(str(tmp_path / "l.jsonl"), str(tmp_path / "p.jsonl"))
    lg.log("x", api_key="SHHH", nested=dict(private_key="SHHH2", ok=1), signature="SHHH3", fine="visible")
    txt = open(lg.path).read()
    assert "SHHH" not in txt and "visible" in txt and '"ok": 1' in txt


def test_fill_that_does_not_match_kalshi_halts_but_keeps_the_position(tmp_path):
    st = mklive(tmp_path)
    mkround(st)
    c = FakeClient()
    c.fills_override = [{"count_fp": "1.00", "yes_price_dollars": "0.7600", "no_price_dollars": "0.2400", "fee_cost": "0.0100"}]
    c.order_result = {"fill_count": "1.00", "average_fill_price": "0.7200"}
    assert enter(c, st, True, T, "yes", .72, 50, 1.0, "t", signal=strong())
    pos = st.rounds[T]["pos"]
    assert pos["price"] == pytest.approx(0.76)               # Kalshi's number wins, so P&L is real
    assert st.halted and not st.armed and "fill check FAILED" in st.halted
    assert [e for e in st.ledger.events() if e["event"] == "fill_check"][0]["ok"] is False


@pytest.mark.parametrize("mode", ["none", "error"])
def test_missing_or_unreadable_fills_halt_and_never_lose_the_position(tmp_path, mode):
    st = mklive(tmp_path)
    mkround(st)
    c = FakeClient()
    c.fills_override = [] if mode == "none" else None
    if mode == "error":
        c.fills = lambda oid=None: (_ for _ in ()).throw(KalshiError("HTTP 500"))
    assert enter(c, st, True, T, "yes", .72, 50, 1.0, "t", signal=strong())      # no exception escapes
    assert st.rounds[T]["pos"] and st.halted


def test_verify_fill_unit(tmp_path):
    c = FakeClient()
    c.orders.append((T, "no", "buy", 1, 0.3))
    c.order_result = {"fill_count": "1.00", "average_fill_price": "0.7000", "order_id": "o"}
    assert verify_fill(c, c.order_result, "no", 1, 1.0, sleep=lambda s: None)["ok"]
    c.fills_override = [{"count_fp": "2.00", "yes_price_dollars": "0.7", "no_price_dollars": "0.3", "fee_cost": "0.03"}]
    assert "count 2" in verify_fill(c, c.order_result, "no", 1, 1.0, sleep=lambda s: None)["detail"]
    c.fills_override = [{"count_fp": "1.00", "yes_price_dollars": "0.7", "no_price_dollars": "0.3", "fee_cost": "0.50"}]
    assert "fee" in verify_fill(c, c.order_result, "no", 1, 1.0, sleep=lambda s: None)["detail"]
    assert not verify_fill(c, {"fill_count": "1"}, "no", 1, 1.0)["ok"]


def test_settlement_and_cashout_are_logged_and_real_pnl_is_after_fees(tmp_path):
    st = mklive(tmp_path)
    r1 = mkround(st, "T1")
    enter(FakeClient(), st, True, "T1", "yes", .72, 50, 1.0, "t", signal=strong("T1"))
    pos = dict(r1["pos"])
    finalize_round(st, r1, "yes")
    win = 1 - pos["price"] - pos["fee"]
    r2 = mkround(st, "T2")
    c = FakeClient()
    enter(c, st, True, "T2", "yes", .60, 50, 1.0, "t", signal=strong("T2"))
    c.markets["T2"] = mkmarket("T2", .50, .52)
    cash_out(c, st, "T2", True)
    sm = st.ledger.summary()
    closed = [e for e in st.ledger.events() if e["event"] == "trade_closed"]
    assert [e["exit_kind"] for e in closed] == ["settlement", "cashout"]
    assert closed[0]["pnl_net"] == pytest.approx(win, abs=1e-3) and closed[1]["pnl_net"] < 0
    assert sm["trades"] == 2 and sm["wins"] == 1 and sm["pnl_net_total"] == pytest.approx(sum(e["pnl_net"] for e in closed), abs=1e-3)
    assert sm["fees_total"] > 0 and sm["unverified"] == 1                 # the settlement is not yet matched with Kalshi's record


def test_settlement_reconciliation_with_kalshi_record(tmp_path):
    st = mklive(tmp_path)
    r = mkround(st)
    enter(FakeClient(), st, True, T, "yes", .72, 50, 1.0, "t", signal=strong())
    finalize_round(st, r, "yes")
    c = FakeClient()
    c.settlements_list = [dict(ticker=T, revenue=100, yes_total_cost_dollars="0.7200", no_total_cost_dollars="0.0000", fee_cost="0.0200")]
    verify_settlements(c, st)
    assert any(e["event"] == "settlement_verified" for e in st.ledger.events()) and not st.halted
    assert st.ledger.summary()["unverified"] == 0


def test_settlement_mismatch_halts(tmp_path):
    st = mklive(tmp_path)
    r = mkround(st)
    enter(FakeClient(), st, True, T, "yes", .72, 50, 1.0, "t", signal=strong())
    finalize_round(st, r, "yes")
    c = FakeClient()
    c.settlements_list = [dict(ticker=T, revenue=0, yes_total_cost_dollars="0.7200", no_total_cost_dollars="0", fee_cost="0.02")]
    verify_settlements(c, st)
    assert st.halted and any(e["event"] == "settlement_mismatch" for e in st.ledger.events())


# ------------------------------------------------------------------ 6b. post-mortems; no auto-retrain
def test_loss_produces_a_post_mortem_and_win_does_not(tmp_path):
    st = mklive(tmp_path)
    r1 = mkround(st, "W")
    enter(FakeClient(), st, True, "W", "yes", .72, 50, 1.0, "t", signal=strong("W"))
    finalize_round(st, r1, "yes")
    assert st.ledger.postmortems() == []
    r2 = mkround(st, "L")
    r2["snap"] = dict(target=100000.0, p_model=0.9, p_market=0.7, secs_left=300, z_sigma=1.5, price=100100.0, yes_ask=0.72, no_ask=0.3)
    enter(FakeClient(), st, True, "L", "yes", .72, 50, 1.0, "t", signal=strong("L"))
    open(st.snaps_path, "w").write("time,ticker,secs_left,price,target\n" + "".join(
        f"t,L,{sl},{px},100000.0\n" for sl, px in ((250, 100080), (150, 100040), (90, 99990), (30, 99950))))
    finalize_round(st, r2, "no", {"expiration_value": "99940.00"})
    pm = st.ledger.postmortems()
    assert len(pm) == 1 and pm[0]["ticker"] == "L" and pm[0]["mode"] == "live" and pm[0]["pnl"] < 0
    text = " ".join(pm[0]["lines"])
    assert "late flip" in " ".join(pm[0]["tags"]) and "lost its lead" in text and "bps" in text and "1 in" in text
    assert "No thresholds, limits or model parameters were changed" in text


def test_losses_never_change_thresholds_modes_or_limits(tmp_path):
    st = mklive(tmp_path)
    before = (copy.deepcopy(MODES), copy.deepcopy(st.cfg), dict(st.pilot.limits), dict(pl.PILOT_MAX), pl.FLIP_MAX_TOUCH)
    for i in range(3):
        r = mkround(st, f"L{i}")
        r["snap"] = dict(target=100000.0, p_model=0.9, p_market=0.7, secs_left=300, z_sigma=1.5)
        st.pilot.today_fn = lambda i=i: f"2026-02-{i + 1:02d}"      # one trade per day so the daily breakers stay out of the way
        assert enter(FakeClient(), st, True, f"L{i}", "yes", .72, 50, 1.0, "t", signal=strong(f"L{i}"))
        finalize_round(st, r, "no")
    assert (MODES, st.cfg, st.pilot.limits, dict(pl.PILOT_MAX), pl.FLIP_MAX_TOUCH) == before
    assert len(st.ledger.postmortems()) == 3
    # the only reaction to a losing run is the pre-existing streak stop, not a retune
    mkround(st, "L3")
    st.pilot.today_fn = lambda: "2026-02-09"
    assert not enter(FakeClient(), st, True, "L3", "yes", .72, 50, 1.0, "t", signal=strong("L3"))
    assert "in a row" in st.rounds["L3"]["reason"] and st.cfg == before[1]


# ------------------------------------------------------------------ preflight units
def test_shard_check_unit():
    c = FakeClient()
    m = {"exchange_index": 2}
    assert preflight.shard_check(c, m, 1.0)["ok"]
    c.balance_json = dict(c.balance_json, balance_breakdown=[{"exchange_index": 0, "balance": "10.0000"}, {"exchange_index": 2, "balance": "0.0000"}])
    r = preflight.shard_check(c, m, 1.0)
    assert not r["ok"] and "shard 2" in r["detail"] and "exchange-indexes" in r["detail"]
    c.balance_json = {"balance": 1000, "balance_dollars": "10.0000"}
    assert "missing" in preflight.shard_check(c, m, 1.0)["detail"]
    assert "no exchange_index" in preflight.shard_check(c, {}, 1.0)["detail"]
    c.balance_detail = lambda: (_ for _ in ()).throw(KalshiError("HTTP 500"))
    assert not preflight.shard_check(c, m, 1.0)["ok"]                      # errors fail closed, never raise


class FakeDemo(FakeClient):
    base = "https://external-api.demo.kalshi.co/trade-api/v2"
    fingerprint = "demo-fp"

    def __init__(self, ask=0.50, fee_ok=True):
        super().__init__()
        self.ask, self.fee_ok = ask, fee_ok
        self.markets["D"] = mkmarket("D", ask - 0.02, ask)
        self.open = dict(self.markets["D"])
        self.open["yes_ask_size_fp"] = "20.00"
        self.markets["D"]["yes_bid_dollars"] = f"{ask - 0.02:.4f}"
    allow_orders = False

    def fills(self, order_id=None):
        f = super().fills(order_id)
        if f and not self.fee_ok and len(self.orders) == 1:
            f[0]["fee_cost"] = "0.5000"
        return f


def test_demo_test_order_passes_and_records(tmp_path):
    d = FakeDemo()
    d.order_result = {"fill_count": "1.00", "average_fill_price": "0.5000"}
    res = preflight.demo_test_order(d, sleep=lambda s: None)
    assert res["ok"] and [o[2] for o in d.orders] == ["buy", "sell"]
    f = tmp_path / "pf.json"
    preflight.save_demo_result(str(f), res)
    assert preflight.demo_fresh(str(f), "live-fp")[0] and not preflight.demo_fresh(str(f), "demo-fp")[0]
    assert not preflight.demo_fresh(str(f), "x", now=time.time() + 25 * 3600)[0]


def test_demo_test_order_fails_on_fee_mismatch_and_never_runs_against_production(tmp_path):
    d = FakeDemo(fee_ok=False)
    d.order_result = {"fill_count": "1.00", "average_fill_price": "0.5000"}
    assert not preflight.demo_test_order(d, sleep=lambda s: None)["ok"]
    prod = FakeDemo()
    prod.base = "https://api.elections.kalshi.com/trade-api/v2"
    assert not preflight.demo_test_order(prod)["ok"] and prod.orders == []


def test_board_shows_the_real_pilot_limits_and_locks_the_mode(tmp_path, keys, clean_env):
    s = live_stack(tmp_path, keys)
    try:
        s.st.cfg.update(size_per_trade_usd=5, daily_loss_cap_usd=15, mode="aggressive")
        d = requests.get(s.url + "/api/status").json()
        assert d["size"] == 1.0 and d["cap"] == 2.0 and d["modes"] == [] and "fixed" in d["mode"]
        s.st.pilot.lower("stake_usd", 0.5)
        assert requests.get(s.url + "/api/status").json()["size"] == 0.5
        assert post(s, "/api/mode", {"mode": "aggressive"}).status_code == 409 and s.st.cfg["mode"] == "aggressive"
    finally:
        s.srv.shutdown()


# ------------------------------------------------------------------ the readiness check also runs AT ORDER TIME
def armed_live(tmp_path, keys, **kw):
    s = live_stack(tmp_path, keys, enabled=True, **kw)
    s.srv.shutdown()
    s.st.armed = True
    s.st.live_gate = s.ctx.gate                       # the real gate, as Ctx installs it
    mkround(s.st)
    return s


def test_order_time_gate_blocks_when_shard_funds_vanish_between_polls(tmp_path, keys):
    s = armed_live(tmp_path, keys)
    s.bal["balance_breakdown"][1]["balance"] = "0.0000"          # nothing polled it yet; the order must still be refused
    assert not enter(s.client, s.st, True, T, "yes", .72, 50, 1.0, "t", signal=strong())
    assert "shard" in s.st.rounds[T]["reason"].lower() and s.sess.posts() == []


def test_order_time_gate_blocks_when_demo_result_goes_stale(tmp_path, keys):
    s = armed_live(tmp_path, keys)
    write_demo(s.pf, age=25 * 3600)
    assert not enter(s.client, s.st, True, T, "yes", .72, 50, 1.0, "t", signal=strong())
    assert "demo" in s.st.rounds[T]["reason"].lower() and s.sess.posts() == []


def test_order_time_gate_passes_when_everything_is_healthy(tmp_path, keys):
    s = armed_live(tmp_path, keys)
    assert enter(s.client, s.st, True, T, "yes", .72, 50, 1.0, "t", signal=strong()) and len(s.sess.posts()) == 1


def test_a_live_state_without_a_gate_refuses_orders(tmp_path):
    st = mklive(tmp_path)
    st.live_gate = None
    mkround(st)
    assert not enter(FakeClient(), st, True, T, "yes", .72, 50, 1.0, "t", signal=strong())
    st.live_gate = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    assert not enter(FakeClient(), st, True, T, "yes", .72, 50, 1.0, "t", signal=strong()) and "errored" in st.rounds[T]["reason"]
