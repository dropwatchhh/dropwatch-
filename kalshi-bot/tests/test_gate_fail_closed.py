"""Gate 1: fail closed. Network dead, garbage, stale, missing quotes, 429, 5xx => no order, no crash."""
import json
import threading
import time

import pytest
import requests

from engine import Ctx, run_loop
from kalshi_client import Kalshi
from signals import Feed
from tests.helpers import mkmarket, mkstate, mklive
from tests.net import KEY, Resp, Script, good_handler

T = "KXBTC15M-T1"
GOOD = lambda: dict(mkmarket(T, 0.70, 0.72, strike=99000.0, close_in=300), exchange_index=2)   # satisfies the strict pilot rules


class OneShot(threading.Event):
    """Stop event whose first wait() ends the loop => run_loop does exactly one iteration."""
    def wait(self, timeout=None):
        self.set()
        return True


class TickFeed(Feed):
    def __init__(self, stale=False):
        super().__init__("BTC")
        self.stale, self.fail = stale, False
        now = time.time() - (60 if stale else 0)
        for i in range(350):                       # gentle uptrend + noise: momentum is not adverse for YES
            self.add(100000 + 0.2 * i + 5 * ((-1) ** i), now - 700 + 2 * i)

    def poll(self):
        if self.stale or self.fail:
            raise RuntimeError("price source down")
        self.add(self.ticks[-1][1] + 0.2)


def run_once(tmp_path, handler, live, stale=False):
    sess = Script(handler)
    client = Kalshi("kid", KEY, session=sess, sleep=lambda s: None, max_retries=2)
    client.allow_orders = live
    client.buy_limits = (5.0, 0.95)
    st = mklive(tmp_path) if live else mkstate(tmp_path, armed=True)
    st.armed = True
    pf = str(tmp_path / "preflight.json")
    json.dump(dict(ok=True, ts=time.time(), base_host="external-api.demo.kalshi.co", key_fingerprint="demo-fp"), open(pf, "w"))
    client.env, client.fingerprint = "live", "live-fp"
    ctx = Ctx(client, st, {"BTC": TickFeed(stale)}, live=live, preflight_path=pf, fee_verified=True)   # real readiness gate
    run_loop(ctx, OneShot())                      # must not raise
    return st, sess


def test_control_the_baseline_scenario_does_trade(tmp_path):
    """Without this, 'no order' below could just mean the setup was never tradeable."""
    st, sess = run_once(tmp_path, good_handler(GOOD()), live=True)
    assert st.rounds[T]["pos"] and len(sess.posts()) == 1 and st.rounds[T]["pos"]["count"] == 1


def boom(method, url):
    raise requests.ConnectionError("network down")


def garbage_json(method, url):
    return Resp(200, garbage=True)


def wrong_shape(method, url):
    return Resp(200, {"markets": "garbage", "market": 5})


def missing_fields(method, url):
    return Resp(200, {"markets": [{"ticker": T}], "market": {"ticker": T}})


def always(code):
    return lambda m, u: Resp(code, {"error": {"code": "x", "message": "y"}})


def no_quotes(method, url):
    m = {"ticker": T, "close_time": GOOD()["close_time"], "floor_strike": 99000.0, "result": ""}
    return good_handler(m)(method, url)


def null_strike(method, url):
    m = GOOD()
    m["floor_strike"] = None
    return good_handler(m)(method, url)


def one_sided(method, url):
    m = GOOD()
    m.pop("yes_ask_dollars")
    m.pop("no_ask_dollars")
    return good_handler(m)(method, url)


def zero_ask(method, url):
    m = GOOD()
    m["yes_ask_dollars"] = "0.0000"
    return good_handler(m)(method, url)


SCENARIOS = {
    "network_down": (boom, False), "garbage_json": (garbage_json, False), "wrong_shape": (wrong_shape, False),
    "missing_fields": (missing_fields, False), "http_429": (always(429), False), "http_500": (always(500), False),
    "http_503": (always(503), False), "http_401": (always(401), False), "missing_bid_ask": (no_quotes, False),
    "no_ask_side": (one_sided, False), "zero_ask": (zero_ask, False), "null_target": (null_strike, False),
    "stale_price_over_5s": (good_handler(GOOD()), True),
}


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_no_order_and_no_crash(tmp_path, name):
    handler, stale = SCENARIOS[name]
    st, sess = run_once(tmp_path, handler, live=True, stale=stale)
    assert sess.posts() == [], f"{name}: an order was sent"
    assert not any((r.get("pos")) for r in st.rounds.values())


def test_stale_boundary_is_five_seconds():
    f = Feed("BTC")
    f.add(1.0, ts=100.0)
    assert f.is_fresh(5.0, now=105.0) and not f.is_fresh(5.0, now=105.01)


# ---- failures on the ORDER call itself: never retried, bot halts rather than guessing
@pytest.mark.parametrize("name,resp", [("timeout", requests.Timeout("t")), ("http500", Resp(500)),
                                         ("garbage_201", Resp(201, garbage=True)),
                                         ("connreset", requests.ConnectionError("x"))])
def test_ambiguous_order_result_sends_exactly_one_post_then_halts(tmp_path, name, resp):
    def extra(method, url):
        if method == "POST":
            if isinstance(resp, Exception):
                raise resp
            return resp
    st, sess = run_once(tmp_path, good_handler(GOOD(), extra=extra), live=True)
    assert len(sess.posts()) == 1 and st.halted and not st.armed
