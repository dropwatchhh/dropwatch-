"""Gate 1: close the remaining gaps in risk / settlement / cash-out coverage."""
import time

import pytest

from engine import cash_out, enter, finalize_round, settle_pending
from kalshi_client import KalshiError
from tests.helpers import FakeClient, mkmarket, mkround, mkstate

T = "KXBTC15M-T1"


def test_check_entry_itself_rejects_oversize_cost(tmp_path):
    st = mkstate(tmp_path, size_per_trade_usd=5)
    ok, why = st.check_entry(T, 0.5, 5.01)       # called directly: no caller can slip past it
    assert not ok and "size cap" in why
    assert st.check_entry(T, 0.5, 5.00)[0]


def test_check_entry_rejects_each_limit_directly(tmp_path):
    st = mkstate(tmp_path, armed=False)
    assert st.check_entry(T, 0.5, 1)[1] == "disarmed"
    st.armed = True
    assert "above max" in st.check_entry(T, 0.96, 1)[1]
    st.pnl = -15
    assert "daily loss cap" in st.check_entry(T, 0.5, 1)[1]
    st.pnl, st.loss_streak = 0, 3
    assert "in a row" in st.check_entry(T, 0.5, 1)[1]
    st.loss_streak = 0
    st.attempted.add(T)
    assert "already" in st.check_entry(T, 0.5, 1)[1]


def held(tmp_path, price=0.5):
    st = mkstate(tmp_path)
    r = mkround(st)
    enter(FakeClient(), st, False, T, "yes", price, 500, 1.0, "x")
    return st, r


def test_live_cash_out_ambiguous_failure_halts(tmp_path):
    st, r = held(tmp_path)
    c = FakeClient()
    c.markets[T] = mkmarket(T, .55, .57)
    c.order_error = KalshiError("timeout", ambiguous=True)
    assert "failed" in cash_out(c, st, T, live=True) and st.halted and not r["pos"]["closed"]


def test_live_cash_out_unfilled_keeps_position(tmp_path):
    st, r = held(tmp_path)
    c = FakeClient()
    c.markets[T] = mkmarket(T, .55, .57)
    c.order_result = {"fill_count": "0.00"}
    assert "not filled" in cash_out(c, st, T, live=True) and not r["pos"]["closed"] and st.pnl == 0


def test_live_cash_out_no_side_converts_yes_leg_fill_price(tmp_path):
    st = mkstate(tmp_path)
    r = mkround(st)
    enter(FakeClient(), st, False, T, "no", 0.30, 500, 1.0, "x")
    n = r["pos"]["count"]
    c = FakeClient()
    c.markets[T] = mkmarket(T, .60, .62, nb=.38, na=.40)
    c.order_result = {"fill_count": f"{n}.00", "average_fill_price": "0.6000"}   # YES-leg => NO price 0.40
    cash_out(c, st, T, live=True)
    assert r["cash"]["price"] == pytest.approx(0.40) and c.orders[-1][:3] == (T, "no", "sell")


def test_unheld_round_that_never_resolves_is_closed_out_after_an_hour(tmp_path):
    st = mkstate(tmp_path)
    c = FakeClient()
    r = mkround(st, close_in=-4000)
    c.markets[T] = mkmarket(T, .5, .6, result="")
    settle_pending(c, st)
    assert T not in st.rounds


def test_held_round_that_never_resolves_is_never_silently_dropped(tmp_path):
    st, r = held(tmp_path)
    c = FakeClient()
    r["close_time"] = mkmarket(T, .5, .6, close_in=-4000)["close_time"]
    c.markets[T] = mkmarket(T, .5, .6, result="")
    settle_pending(c, st)
    assert T in st.rounds and r["pos"] and not r["pos"]["closed"]


def test_settlement_error_in_lookup_does_not_crash_or_settle(tmp_path):
    st, r = held(tmp_path)
    r["close_time"] = mkmarket(T, .5, .6, close_in=-100)["close_time"]
    settle_pending(FakeClient(), st)           # market() raises KeyError inside; must be swallowed
    assert T in st.rounds and st.pnl == 0
