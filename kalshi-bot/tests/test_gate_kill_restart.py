"""Gate 1: kill switch and restart safety."""
import os
import subprocess
import sys
import textwrap
import threading
from http.server import ThreadingHTTPServer

import pytest

import board
import kill
from engine import Ctx, State, DEFAULTS, enter, reconcile, run_loop
from kalshi_client import Kalshi
from tests.helpers import FakeClient, mkmarket, mkround, mkstate, mklive, strong
from tests.net import KEY, Resp, Script, good_handler
from tests.test_gate_fail_closed import OneShot, TickFeed

T = "KXBTC15M-T1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def mkclient(handler):
    sess = Script(handler)
    c = Kalshi("kid", KEY, session=sess, sleep=lambda s: None, max_retries=1)
    return c, sess


# ------------------------------------------------------------------ kill switch
def test_kill_cancels_all_and_blocks_entries(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    c, sess = mkclient(good_handler(mkmarket(T, .5, .6)))
    assert kill.main(["--port", "1"], client=c) == 0                # no board listening: handled
    assert os.path.exists("KILL")
    assert [x for x in sess.calls if x[0] == "DELETE" and x[1].endswith("/portfolio/events/orders")]
    assert sess.posts() == []                                       # without --flatten nothing is sold
    out = capsys.readouterr().out
    assert "cancelled all resting orders" in out and "positions left open" in out
    st = State(dict(DEFAULTS), path="s.json", trades_path="t.csv", snaps_path="n.csv", kill_path="KILL")
    st.armed = True
    mkround(st)
    assert enter(FakeClient(), st, False, T, "yes", .8, 500, 1.0, "x") is False and not st.armed
    assert "kill switch" in st.rounds[T]["reason"]


def test_kill_flatten_sells_open_crypto_positions_reduce_only(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    positions = [{"ticker": "KXBTC15M-A", "position_fp": "5.00"}, {"ticker": "KXBTC15M-B", "position_fp": "-3.00"},
                 {"ticker": "KXETH15M-C", "position_fp": "0.00"}, {"ticker": "OTHER-1", "position_fp": "9.00"}]
    c, sess = mkclient(good_handler(mkmarket("KXBTC15M-A", .70, .72), order_fill="5.00", positions=positions))
    rc = kill.main(["--flatten", "--port", "1"], client=c)
    posts = sess.posts()
    assert len(posts) == 2 and all(p[2]["reduce_only"] and p[2]["time_in_force"] == "immediate_or_cancel" for p in posts)
    assert posts[0][2]["side"] == "ask" and posts[0][2]["price"] == "0.7000"   # sell YES at the bid
    assert posts[1][2]["side"] == "bid" and posts[1][2]["price"] == "0.7200"    # sell NO at no_bid 0.28 => bid at yes-price 0.72
    assert "OTHER-1" not in capsys.readouterr().out
    assert rc == 0


def test_kill_flatten_reports_unsellable_positions_and_nonzero_exit(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    c, sess = mkclient(good_handler(mkmarket("KXBTC15M-A", 0.0, .05),
                                    positions=[{"ticker": "KXBTC15M-A", "position_fp": "5.00"}]))
    assert kill.main(["--flatten", "--port", "1"], client=c) == 1
    assert "no bid" in capsys.readouterr().out and sess.posts() == []


def test_kill_reports_cancel_failure_loudly(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    c, _ = mkclient(good_handler(mkmarket(T, .5, .6), extra=lambda m, u: Resp(500) if m == "DELETE" else None))
    assert kill.main(["--port", "1"], client=c) == 1 and "CANCEL FAILED" in capsys.readouterr().out


def test_kill_without_credentials_still_engages(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("KALSHI_API_KEY_ID", raising=False)
    monkeypatch.delenv("KALSHI_PRIVATE_KEY_PATH", raising=False)
    assert kill.main(["--port", "1"]) == 0 and os.path.exists("KILL")
    kill.main(["--clear"])
    assert not os.path.exists("KILL")


def test_kill_disarms_running_board_and_blocks_rearm(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BOARD_TOKEN", "t" * 20)
    st = State(dict(DEFAULTS), path="s.json", trades_path="t.csv", snaps_path="n.csv", kill_path="KILL")
    st.armed = True
    s = ThreadingHTTPServer(("127.0.0.1", 0), board.make_handler(FakeClient(), st, False))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        assert kill.disarm_board("127.0.0.1", s.server_port, "t" * 20) and not st.armed
        kill.engage("KILL")
        import requests
        r = requests.post(f"http://127.0.0.1:{s.server_port}/api/arm", json={"armed": True},
                          headers={"X-Board": "1", "X-Token": "t" * 20})
        assert r.status_code == 409 and not st.armed
    finally:
        s.shutdown()


def test_loop_disarms_when_kill_file_appears(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    st = State(dict(DEFAULTS), path="s.json", trades_path="t.csv", snaps_path="n.csv", kill_path="KILL")
    st.armed = True
    kill.engage("KILL")
    c, sess = mkclient(good_handler(mkmarket(T, .78, .80, strike=99000.0)))
    c.allow_orders = True
    run_loop(Ctx(c, st, {"BTC": TickFeed()}, live=True), OneShot())
    assert not st.armed and sess.posts() == []


# ------------------------------------------------------------------ restart safety
CRASH = textwrap.dedent('''
    import os, sys
    sys.path.insert(0, {root!r})
    from engine import State, DEFAULTS, enter, new_round
    from pilot import Pilot, STRONG
    st = State(dict(DEFAULTS), path="state.json", trades_path="t.csv", snaps_path="n.csv", kill_path="NOKILL")
    st.armed, st.live = True, True
    st.pilot = Pilot(path="pilot.json"); st.pilot.live_enabled = True
    st.live_gate = lambda: (True, "ok")
    import time
    sig = dict(ticker="{t}", ts=time.time(), grade=STRONG, checks=[], failed=[], flip=dict(label="SAFE TO ENTER"))
    st.rounds["{t}"] = new_round("BTC", dict(ticker="{t}", close_time="2099-01-01T00:00:00Z"), dict(time="x"), [], dict(reason="r"), st)
    class C:
        def place_order(self, *a):
            open("orders.log", "a").write("order\\n")
            os._exit(9)          # hard kill: no cleanup, no finally blocks, no atexit
    enter(C(), st, True, "{t}", "yes", 0.8, 500, 1.0, "x", signal=sig)
''')


def test_hard_kill_during_live_order_then_restart_no_duplicate_no_lost_position(tmp_path):
    r = subprocess.run([sys.executable, "-c", CRASH.format(root=ROOT, t=T)], cwd=tmp_path)
    assert r.returncode == 9 and (tmp_path / "orders.log").read_text().count("order") == 1
    # --- restart
    st = State(dict(DEFAULTS), path=str(tmp_path / "state.json"), trades_path=str(tmp_path / "t.csv"),
               snaps_path=str(tmp_path / "n.csv"), kill_path=str(tmp_path / "NOKILL"))
    st.armed, st.live = True, True
    from pilot import Pilot
    st.pilot = Pilot(path=str(tmp_path / "pilot.json"))
    st.pilot.live_enabled = True
    st.live_gate = lambda: (True, "ok")
    assert T in st.attempted                       # write-ahead state survived the crash
    assert st.pilot.trades_today == 1              # ...and so did the per-day order count
    spy = FakeClient()
    assert enter(spy, st, True, T, "yes", 0.8, 500, 1.0, "retry", signal=strong(T)) is False and spy.orders == []   # no duplicate
    # Kalshi says the order DID fill before the crash: reconcile adopts it
    spy.positions_list = [{"ticker": T, "position_fp": "6.00", "market_exposure_dollars": "4.80"}]
    spy.markets[T] = mkmarket(T, .7, .8)
    st.rounds.pop(T, None)
    reconcile(spy, st)
    p = st.rounds[T]["pos"]
    assert p["count"] == 6 and p["side"] == "yes" and p["price"] == pytest.approx(0.8)
    assert enter(spy, st, True, T, "yes", 0.8, 500, 1.0, "again", signal=strong(T)) is False and spy.orders == []


def test_restart_in_paper_keeps_position_and_does_not_reenter(tmp_path):
    st = mkstate(tmp_path)
    mkround(st)
    assert enter(FakeClient(), st, False, T, "yes", .8, 500, 1.0, "x")
    n = st.rounds[T]["pos"]["count"]
    st2 = mkstate(tmp_path)                       # "restart": new process, same files
    assert st2.rounds[T]["pos"]["count"] == n and T in st2.attempted
    assert enter(FakeClient(), st2, False, T, "yes", .8, 500, 1.0, "x") is False


def test_restart_with_unfilled_order_may_retry_but_only_once_per_run(tmp_path):
    """An IOC that never filled leaves nothing on Kalshi; reconcile finds no position."""
    st = mklive(tmp_path)
    mkround(st)
    c = FakeClient()
    c.order_result = {"fill_count": "0.00"}
    enter(c, st, True, T, "yes", .8, 500, 1.0, "x", signal=strong(T))
    reconcile(c, st)
    assert not st.rounds[T]["pos"] and len(c.orders) == 1


def test_kill_with_unloadable_live_credentials_says_orders_were_not_cancelled(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KALSHI_LIVE_API_KEY_ID", "live-id-12345678")
    monkeypatch.setenv("KALSHI_LIVE_PRIVATE_KEY_PATH", str(tmp_path / "missing.pem"))
    assert kill.main(["--port", "1"]) == 1
    out = capsys.readouterr().out
    assert "NOT cancelled" in out and os.path.exists("KILL")
