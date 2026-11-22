import csv
import json
import time

import pytest

from engine import (Ctx, DEFAULTS, State, cash_out, enter, finalize_round, load_config, max_affordable_count,
                    process_asset, reconcile, resolve_live, settle_pending)
from kalshi_client import KalshiError, trade_fee
from signals import Feed
from tests.helpers import FakeClient, NoOrdersClient, iso, mkmarket, mkround, mkstate

T = "KXBTC15M-T1"


def buy(st, client=None, live=False, ticker=T, side="yes", price=0.8, size=500, reason="t"):
    return enter(client or NoOrdersClient(), st, live, ticker, side, price, size, 1.0, reason)


# ---------------------------------------------------------------- live gating
@pytest.mark.parametrize("flag,trading,expected", [(False, "paper", False), (True, "paper", False),
                                                    (False, "live", False), (True, "live", True)])
def test_live_needs_flag_and_config(flag, trading, expected):
    assert resolve_live(flag, {"trading": trading}) is expected


def test_paper_mode_never_places_orders(tmp_path):
    st = mkstate(tmp_path)
    mkround(st)
    assert buy(st, NoOrdersClient(), live=False) is True  # NoOrdersClient raises if used


def test_config_validation(tmp_path):
    p = tmp_path / "c.json"
    for bad in ({"mode": "yolo"}, {"assets": ["DOGE"]}, {"size_per_trade_usd": 0}, {"trading": "maybe"},
                {"max_losses_in_row": 0}, {"hard_max_price": 1.5}, {"daily_loss_cap_usd": -1}):
        p.write_text(json.dumps(bad))
        with pytest.raises(ValueError):
            load_config(str(p))
    p.write_text("{}")
    assert load_config(str(p))["trading"] == "paper"  # default is paper


# ---------------------------------------------------------------- risk limits
def test_disarmed_blocks(tmp_path):
    st = mkstate(tmp_path, armed=False)
    mkround(st)
    assert buy(st) is False and not st.rounds[T]["pos"]


def test_size_cap_never_exceeded_even_for_expensive_contracts(tmp_path):
    st = mkstate(tmp_path, size_per_trade_usd=5, mode="aggressive")
    mkround(st)
    assert buy(st, price=0.9)
    p = st.rounds[T]["pos"]
    assert p["price"] * p["count"] + p["fee"] <= 5.0
    d2 = tmp_path / "x"
    d2.mkdir()
    st2 = mkstate(d2, size_per_trade_usd=0.5, mode="aggressive")
    mkround(st2)
    assert buy(st2, price=0.9) is False and not st2.rounds[T]["pos"]  # $0.50 cannot buy one at 0.90 + fee


def test_mode_max_price_enforced_in_order_path_not_just_decide(tmp_path):
    st = mkstate(tmp_path, mode="conservative")   # conservative max price is 0.75
    mkround(st)
    assert buy(st, price=0.80) is False and "above max" in st.rounds[T]["reason"]
    assert buy(st, price=0.70) is True


def test_max_affordable_count_includes_fees():
    n = max_affordable_count(5.0, 0.5, 1.0)
    assert 0.5 * n + trade_fee(0.5, n) <= 5.0 and 0.5 * (n + 1) + trade_fee(0.5, n + 1) > 5.0


def test_hard_max_price(tmp_path):
    st = mkstate(tmp_path, hard_max_price=0.9)
    mkround(st)
    assert buy(st, price=0.93) is False


def test_one_position_per_round(tmp_path):
    st = mkstate(tmp_path)
    mkround(st)
    assert buy(st) is True
    assert buy(st) is False
    cash_out_client = FakeClient()
    cash_out_client.markets[T] = mkmarket(T, 0.85, 0.87)
    cash_out(cash_out_client, st, T, False)
    assert buy(st) is False  # still no re-entry after cashing out


def test_daily_loss_cap_blocks_and_open_exposure_counts(tmp_path):
    st = mkstate(tmp_path, daily_loss_cap_usd=15)
    mkround(st)
    st.pnl = -15.0
    assert buy(st) is False
    st.pnl = -11.0  # a ~$4.9 buy could take us past -15
    assert buy(st) is False and "breach" in st.rounds[T]["reason"]
    st.pnl = -9.0
    assert buy(st) is True


def test_loss_streak_stop_and_reset_on_win(tmp_path):
    st = mkstate(tmp_path, max_losses_in_row=3)
    for _ in range(3):
        st.realize(-1.0)
    mkround(st)
    assert buy(st) is False and "in a row" in st.rounds[T]["reason"]
    st.realize(+1.0)
    assert st.loss_streak == 0 and buy(st) is True


def test_day_roll_resets_pnl_and_streak(tmp_path):
    day = ["2026-01-01"]
    st = mkstate(tmp_path, today_fn=lambda: day[0])
    st.pnl, st.loss_streak = -15.0, 3
    mkround(st)
    assert buy(st) is False
    day[0] = "2026-01-02"
    assert buy(st) is True and st.pnl == 0.0 + 0 and st.loss_streak == 0 and st.day == "2026-01-02"


def test_state_persists_and_day_mismatch_discards_pnl(tmp_path):
    st = mkstate(tmp_path)
    mkround(st)
    buy(st)
    st.pnl, st.loss_streak = -3.0, 2
    st.save()
    st2 = mkstate(tmp_path)
    assert st2.pnl == -3.0 and st2.rounds[T]["pos"] and T in st2.attempted
    st3 = mkstate(tmp_path, today_fn=lambda: "1999-01-01")
    assert st3.pnl == 0.0 and st3.rounds[T]["pos"]  # open position survives the day roll


# ---------------------------------------------------------------- live order handling
def test_live_fill_converts_yes_leg_price_for_no_side(tmp_path):
    st = mkstate(tmp_path)
    mkround(st)
    c = FakeClient()
    c.order_result = {"fill_count": "6.00", "average_fill_price": "0.7000", "average_fee_paid": "0.0100"}
    assert buy(st, c, live=True, side="no", price=0.30)
    p = st.rounds[T]["pos"]
    assert c.orders == [(T, "no", "buy", 15, 0.30)] and p["count"] == 6
    assert p["price"] == pytest.approx(0.30) and p["fee"] == pytest.approx(0.06)


def test_live_unfilled_ioc_leaves_no_position_and_no_retry(tmp_path):
    st = mkstate(tmp_path)
    mkround(st)
    c = FakeClient()
    c.order_result = {"fill_count": "0.00"}
    assert buy(st, c, live=True) is False
    assert not st.rounds[T]["pos"] and buy(st, c, live=True) is False and len(c.orders) == 1


def test_live_ambiguous_order_halts_and_disarms(tmp_path):
    st = mkstate(tmp_path)
    mkround(st)
    c = FakeClient()
    c.order_error = KalshiError("timeout", ambiguous=True)
    assert buy(st, c, live=True) is False
    assert st.halted and not st.armed
    mkround(st, "KXBTC15M-T2")
    assert buy(st, c, live=True, ticker="KXBTC15M-T2") is False and len(c.orders) == 1


def test_live_rejection_does_not_halt(tmp_path):
    st = mkstate(tmp_path)
    mkround(st)
    c = FakeClient()
    c.order_error = KalshiError("HTTP 400 invalid_price", 400, "invalid_price")
    assert buy(st, c, live=True) is False and not st.halted and st.armed


# ---------------------------------------------------------------- settlement PnL
def read_rows(st):
    with open(st.trades_path) as f:
        return list(csv.DictReader(f))


def test_settlement_win_pnl_includes_fee(tmp_path):
    st = mkstate(tmp_path)
    r = mkround(st)
    buy(st, price=0.80)
    pos = r["pos"]
    finalize_round(st, r, "yes")
    expected = pos["count"] * 1.0 - 0.8 * pos["count"] - pos["fee"]
    assert st.pnl == pytest.approx(expected) and expected > 0
    row = read_rows(st)[0]
    assert row["action"] == "ENTER" and row["won"] == "1" and float(row["pnl"]) == pytest.approx(expected, abs=1e-4)
    assert T not in st.rounds and st.loss_streak == 0


def test_settlement_loss_pnl_and_streak(tmp_path):
    st = mkstate(tmp_path)
    r = mkround(st)
    buy(st, price=0.80)
    pos = dict(r["pos"])
    finalize_round(st, r, "no")
    assert st.pnl == pytest.approx(-(0.8 * pos["count"] + pos["fee"])) and st.loss_streak == 1
    assert read_rows(st)[0]["won"] == "0"


def test_no_side_wins_when_result_is_no(tmp_path):
    st = mkstate(tmp_path)
    r = mkround(st)
    buy(st, side="no", price=0.30)
    finalize_round(st, r, "no")
    assert st.pnl > 0


def test_skipped_round_is_recorded_with_outcome(tmp_path):
    st = mkstate(tmp_path)
    r = mkround(st)
    finalize_round(st, r, "yes")
    row = read_rows(st)[0]
    assert row["action"] == "SKIP" and row["result"] == "yes" and row["pnl"] == "0.0" and st.pnl == 0


def test_settle_pending_waits_for_result_and_close(tmp_path):
    st = mkstate(tmp_path)
    c = FakeClient()
    r = mkround(st, close_in=-10)
    buy(st)
    c.markets[T] = mkmarket(T, 0.5, 0.6, result="")
    settle_pending(c, st)
    assert T in st.rounds                      # not resolved yet
    c.markets[T]["result"] = "yes"
    st.rounds[T]["next_check"] = 0
    settle_pending(c, st)
    assert T not in st.rounds and st.pnl > 0
    r2 = mkround(st, "KXBTC15M-FUTURE", close_in=500)
    settle_pending(c, st)                      # market() would KeyError if it looked up an unclosed round
    assert "KXBTC15M-FUTURE" in st.rounds


# ---------------------------------------------------------------- cash out
def test_cash_out_pnl_with_both_fees_and_streak(tmp_path):
    st = mkstate(tmp_path)
    r = mkround(st)
    buy(st, price=0.80)
    pos = dict(r["pos"])
    c = FakeClient()
    c.markets[T] = mkmarket(T, 0.70, 0.72)
    msg = cash_out(c, st, T, live=False)
    exp = 0.70 * pos["count"] - trade_fee(0.70, pos["count"]) - (0.8 * pos["count"] + pos["fee"])
    assert st.pnl == pytest.approx(exp) and st.loss_streak == 1 and "sold" in msg
    assert r["pos"]["closed"] and cash_out(c, st, T, False) == "no open position"
    finalize_round(st, r, "yes")                 # later settlement must not double count
    assert st.pnl == pytest.approx(exp)
    assert read_rows(st)[0]["cashed_out"] == "1"


def test_cash_out_refuses_without_bid_instead_of_selling_at_1c(tmp_path):
    st = mkstate(tmp_path)
    mkround(st)
    buy(st)
    c = FakeClient()
    c.markets[T] = mkmarket(T, 0.0, 0.05)
    assert "no bid" in cash_out(c, st, T, False) and not st.rounds[T]["pos"]["closed"] and not c.orders


def test_cash_out_works_when_disarmed_and_uses_no_bid_for_no_side(tmp_path):
    st = mkstate(tmp_path)
    mkround(st)
    buy(st, side="no", price=0.30)
    st.armed = False
    c = FakeClient()
    c.markets[T] = mkmarket(T, 0.60, 0.62, nb=0.38, na=0.40)
    cash_out(c, st, T, False)
    assert st.pnl > 0


def test_live_partial_cash_out_keeps_remainder(tmp_path):
    st = mkstate(tmp_path)
    r = mkround(st)
    buy(st, price=0.50)
    n = r["pos"]["count"]
    c = FakeClient()
    c.markets[T] = mkmarket(T, 0.55, 0.57)
    c.order_result = {"fill_count": "4.00"}
    cash_out(c, st, T, live=True)
    assert c.orders[-1][:3] == (T, "yes", "sell") and not r["pos"]["closed"] and r["pos"]["count"] == n - 4


# ---------------------------------------------------------------- reconcile
def test_reconcile_adopts_unknown_and_drops_phantom(tmp_path):
    st = mkstate(tmp_path)
    mkround(st, "KXBTC15M-PHANTOM")
    st.rounds["KXBTC15M-PHANTOM"]["pos"] = dict(side="yes", count=3, price=0.5, fee=0.05, closed=False)
    c = FakeClient()
    c.positions_list = [{"ticker": "KXBTC15M-REAL", "position_fp": "-7.00", "market_exposure_dollars": "2.10"},
                        {"ticker": "KXOTHER-1", "position_fp": "5"}]
    c.markets["KXBTC15M-REAL"] = mkmarket("KXBTC15M-REAL", .3, .4)
    reconcile(c, st)
    p = st.rounds["KXBTC15M-REAL"]["pos"]
    assert p["side"] == "no" and p["count"] == 7 and p["price"] == pytest.approx(0.30)
    assert st.rounds["KXBTC15M-PHANTOM"]["pos"] is None and "KXOTHER-1" not in st.rounds
    assert "KXBTC15M-REAL" in st.attempted


# ---------------------------------------------------------------- full paper flow
class TickFeed(Feed):
    def poll(self):
        self.add(self.price)
        return self.price


def run_flow(tmp_path, price, target, bid, ask, stale=False, ladder=None):
    st = mkstate(tmp_path)
    c = NoOrdersClient()
    c.open = mkmarket(T, bid, ask, strike=target, close_in=300)
    c.markets[T] = c.open
    c.ladder = ladder or []
    f = TickFeed("BTC")
    f.price = price
    now = time.time()
    for i in range(350):
        f.add(price * (1 + 0.00005 * ((-1) ** i)), now - 700 + 2 * i)
    if stale:
        f.poll = lambda: (_ for _ in ()).throw(RuntimeError("coinbase down"))
        f.ticks = type(f.ticks)([(t - 60, p) for t, p in f.ticks], maxlen=f.ticks.maxlen)
    ctx = Ctx(c, st, {"BTC": f}, live=False)
    process_asset(ctx, "BTC", now=now)
    return st, c, ctx, now


def test_full_paper_round_enter_then_settle(tmp_path):
    st, c, ctx, now = run_flow(tmp_path, 100000, 99000, 0.78, 0.80)
    pos = st.rounds[T]["pos"]
    assert pos and pos["side"] == "yes" and pos["count"] == 6 and st.last["BTC"]["action"] == "ENTER YES"
    assert st.last["BTC"]["reasoning"]
    c.markets[T]["result"] = "yes"
    st.rounds[T]["next_check"] = 0
    settle_pending(c, st, now=now + 400)
    row = read_rows(st)[0]
    assert float(row["pnl"]) == pytest.approx(6 - 4.8 - 0.07) and row["result"] == "yes"
    assert row["p_model"] and row["p_market"] and row["yes_ask"] == "0.8"
    assert open(st.snaps_path).read().count("\n") >= 2


def test_no_trade_without_clear_setup(tmp_path):
    st, *_ = run_flow(tmp_path, 100000, 99995, 0.49, 0.51)
    assert not st.rounds[T]["pos"] and "no clear setup" in st.last["BTC"]["why"]


def test_stale_price_data_skips_round(tmp_path):
    st, c, ctx, now = run_flow(tmp_path, 100000, 99000, 0.78, 0.80, stale=True)
    assert not st.rounds[T]["pos"] and "stale" in st.last["BTC"]["why"] and st.last["BTC"]["fresh"] is False


def test_reasoning_engine_veto_blocks_trade(tmp_path):
    # model sees ~94% YES but the market says ~50/50 AND prices YES at 0.55: a 'huge edge' we don't trust
    st, *_ = run_flow(tmp_path, 100000, 99000, 0.50, 0.55)
    assert not st.rounds[T]["pos"] and "veto" in st.last["BTC"]["why"]
