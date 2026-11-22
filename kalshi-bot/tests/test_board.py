import json
import threading
from http.server import ThreadingHTTPServer

import pytest
import requests

import board
from tests.helpers import FakeClient, mkmarket, mkround, mkstate
from engine import enter

T = "KXBTC15M-T1"


@pytest.fixture
def srv(tmp_path, monkeypatch):
    monkeypatch.delenv("BOARD_TOKEN", raising=False)
    st = mkstate(tmp_path, armed=False)
    c = FakeClient()
    s = ThreadingHTTPServer(("127.0.0.1", 0), board.make_handler(c, st, False))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{s.server_port}", st, c
    s.shutdown()


H = {"X-Board": "1"}


def test_status_page_and_arm_toggle(srv):
    url, st, _ = srv
    assert "<title>Kalshi Board</title>" in requests.get(url + "/").text
    assert requests.post(url + "/api/arm", json={"armed": True}, headers=H).status_code == 200 and st.armed
    d = requests.get(url + "/api/status").json()
    assert d["armed"] and d["live"] is False and d["pnl"] == 0 and d["modes"] == ["conservative", "balanced", "aggressive"]
    requests.post(url + "/api/arm", json={"armed": False}, headers=H)
    assert not st.armed


def test_post_requires_custom_header_blocking_cross_site_forms(srv):
    url, st, _ = srv
    r = requests.post(url + "/api/arm", data='{"armed": true}', headers={"Content-Type": "text/plain"})
    assert r.status_code == 403 and not st.armed


def test_rebinding_host_header_rejected(srv):
    url, *_ = srv
    assert requests.get(url + "/api/status", headers={"Host": "evil.example.com"}).status_code == 403


def test_mode_switch_validates(srv):
    url, st, _ = srv
    assert requests.post(url + "/api/mode", json={"mode": "aggressive"}, headers=H).status_code == 200
    assert st.cfg["mode"] == "aggressive"
    assert requests.post(url + "/api/mode", json={"mode": "yolo"}, headers=H).status_code == 400


def test_cannot_arm_while_halted(srv):
    url, st, _ = srv
    st.halt("unknown order")
    assert requests.post(url + "/api/arm", json={"armed": True}, headers=H).status_code == 409 and not st.armed


def test_cashout_endpoint(srv):
    url, st, c = srv
    st.armed = True
    mkround(st)
    enter(c, st, False, T, "yes", 0.8, 500, 1.0, "t")
    c.markets[T] = mkmarket(T, 0.7, 0.72)
    r = requests.post(url + "/api/cashout", json={"ticker": T}, headers=H).json()
    assert "sold" in r["result"] and st.rounds[T]["pos"]["closed"]


def test_token_required_when_set(tmp_path, monkeypatch):
    monkeypatch.setenv("BOARD_TOKEN", "x" * 20)
    st = mkstate(tmp_path)
    s = ThreadingHTTPServer(("127.0.0.1", 0), board.make_handler(FakeClient(), st, False))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{s.server_port}"
    try:
        assert requests.get(url + "/api/status").status_code == 401
        assert requests.get(url + "/api/status?t=" + "x" * 20).status_code == 401   # query tokens not accepted
        assert requests.get(url + "/api/status", headers={"X-Token": "wrong"}).status_code == 401
        assert requests.get(url + "/api/status", headers={"X-Token": "x" * 20}).status_code == 200
        assert requests.post(url + "/api/arm", json={"armed": True}, headers=H).status_code == 401
        assert requests.post(url + "/api/arm", json={"armed": True}, headers={**H, "X-Token": "x" * 20}).status_code == 200
    finally:
        s.shutdown()


def test_non_loopback_bind_requires_strong_token():
    for host in ("0.0.0.0", "100.64.1.2"):
        with pytest.raises(SystemExit):
            board.validate_bind(host, None)
        with pytest.raises(SystemExit):
            board.validate_bind(host, "short")
        board.validate_bind(host, "a" * 16)
    board.validate_bind("127.0.0.1", None)
