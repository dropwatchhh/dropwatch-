import math

import pytest

import backtest as bt
import history as h

CLOSE = 1_800_000_000 // 60 * 60


def synth(drift_close=100.0):
    closes = {CLOSE - 60 * k: 100000.0 + k for k in range(0, 30)}   # price rises toward close
    candles = {"T1": {CLOSE - 60 * m: (0.78, 0.80) for m in h.OFFSETS_MIN}}
    rounds = [dict(ticker="T1", floor_strike=99990.0, close_ts=CLOSE, result="yes", expiration_value=100000.0)]
    return rounds, closes, candles


def test_trailing_vol_needs_complete_history():
    c = {CLOSE - 60 * k: 100000.0 * (1 + 0.0001 * (-1) ** k) for k in range(11)}
    assert h.trailing_vol(c, CLOSE) == pytest.approx(math.sqrt(sum(
        math.log(c[CLOSE - 60 * (k - 1)] / c[CLOSE - 60 * k]) ** 2 for k in range(10, 0, -1)) / 600), rel=1e-9)
    del c[CLOSE - 120]
    assert h.trailing_vol(c, CLOSE) is None


def test_build_rows_makes_snapshots_for_every_offset_and_outcomes():
    rounds, closes, candles = synth()
    out, snaps, gaps = h.build_rows(rounds, closes, candles)
    assert len(out) == 1 and out[0]["result"] == "yes" and len(snaps) == len(h.OFFSETS_MIN)
    assert {s["secs_left"] for s in snaps} == {60 * m for m in h.OFFSETS_MIN}
    assert len(gaps) == 1


def test_features_are_causal_result_and_future_prices_do_not_leak():
    rounds, closes, candles = synth()
    _, base, _ = h.build_rows(rounds, closes, candles)
    rounds2 = [dict(rounds[0], result="no", expiration_value=1.0)]
    closes2 = dict(closes)
    for k in (0, 1, 2, 3, 4):             # corrupt prices after the 5-min-before-close decision time
        closes2[CLOSE - 60 * k] = 1.0
    _, alt, _ = h.build_rows(rounds2, closes2, candles)
    key = lambda s: s["secs_left"]
    b5 = [s for s in base if s["secs_left"] == 300][0]
    a5 = [s for s in alt if s["secs_left"] == 300][0]
    assert a5["p_up"] == b5["p_up"] and a5["price"] == b5["price"]


def test_missing_data_is_skipped_not_invented():
    rounds, closes, candles = synth()
    candles["T1"].pop(CLOSE - 300)
    _, snaps, _ = h.build_rows(rounds, closes, candles)
    assert all(s["secs_left"] != 300 for s in snaps)
    out, snaps, _ = h.build_rows(rounds, {}, candles)
    assert out == [] and snaps == []


def test_history_feeds_backtest_end_to_end(tmp_path):
    rounds, closes, candles = synth()
    out, snaps, _ = h.build_rows(rounds, closes, candles)
    res = bt.replay(out, [{k: str(v) for k, v in s.items()} for s in snaps], "aggressive", 5.0)
    assert len(res) == 1 and res[0]["p_model"]
    m = bt.analyse(res)
    assert m["resolved"] == 1 and "INCONCLUSIVE" in m["verdict"]
