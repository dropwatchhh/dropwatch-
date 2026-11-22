import math
import time

import pytest

from kalshi_client import quotes
from signals import (Feed, analyze, decide, ladder_implied_vol, mid_prob, norm_cdf, review, vol_scale_from)
from tests.helpers import iso, mkmarket

V = 0.0002  # per-second vol (~0.15%/min... realistic order of magnitude for BTC)


def test_norm_cdf():
    assert abs(norm_cdf(0) - 0.5) < 1e-12 and abs(norm_cdf(1.96) - 0.975) < 1e-3


def test_at_the_money_is_a_coin_flip():
    s = analyze(100000, 100000, 600, V, shrink=1.0)
    assert abs(s["p_up"] - 0.5) < 1e-9


def test_direction_and_monotonic_in_distance():
    hi = analyze(100100, 100000, 400, V)["p_up"]
    lo = analyze(99900, 100000, 400, V)["p_up"]
    far = analyze(100500, 100000, 400, V)["p_up"]
    assert lo < 0.5 < hi < far
    assert analyze(99900, 100000, 400, V)["side"] == "no"


def test_more_time_means_less_certainty():
    assert analyze(100200, 100000, 800, V)["p_up"] < analyze(100200, 100000, 120, V)["p_up"]


def test_shrink_pulls_toward_half_and_probabilities_are_clamped():
    raw = analyze(100300, 100000, 300, V, shrink=1.0)["p_up"]
    shr = analyze(100300, 100000, 300, V, shrink=0.8)["p_up"]
    assert 0.5 < shr < raw
    assert analyze(200000, 100000, 100, V, shrink=1.0)["p_up"] == 0.99


def test_basis_error_limits_confidence_near_expiry():
    # with 5s left and price $50 above target, only basis error keeps this from certainty
    tight = analyze(100050, 100000, 5, V, basis_bps=0.0, shrink=1.0)["p_up"]
    loose = analyze(100050, 100000, 5, V, basis_bps=5.0, shrink=1.0)["p_up"]
    assert tight > loose > 0.5


def test_averaging_window_reduces_variance_vs_point_in_time():
    # std for T=120 is sqrt(60+20)=8.9s-equivalent, not sqrt(120)=11s
    s = analyze(100000, 100000, 120, V, basis_bps=0.0)
    assert abs(s["std_price"] - 100000 * V * math.sqrt(80)) < 1e-6


def test_observed_part_of_average_window_is_locked_in():
    # 30s left; the first 30s of the window averaged well above target => likelier YES
    base = analyze(100000, 100000, 30, V, window_mean=100000)["p_up"]
    locked = analyze(100000, 100000, 30, V, window_mean=100100)["p_up"]
    assert locked > base and abs(base - 0.5) < 1e-9


def test_analyze_returns_none_when_unusable():
    assert analyze(100000, 100000, 0, V) is None
    assert analyze(100000, 100000, 100, None) is None
    assert analyze(100000, 0, 100, V) is None


def test_momentum_weight_nudges_only_when_enabled():
    a = analyze(100000, 100000, 300, V, momentum=0.002, momentum_weight=0.0)["p_up"]
    b = analyze(100000, 100000, 300, V, momentum=0.002, momentum_weight=1.0)["p_up"]
    assert abs(a - 0.5) < 1e-9 and b > 0.5


# ---- feed
def test_feed_staleness():
    f = Feed("BTC")
    assert not f.is_fresh()
    f.add(100, ts=1000.0)
    assert f.is_fresh(5, now=1004.9) and not f.is_fresh(5, now=1005.1)


def test_realized_vol_recovers_known_volatility():
    import random
    random.seed(7)
    f, p, t0 = Feed("BTC"), 100000.0, 10_000.0
    sig = 0.0003
    for i in range(400):
        p *= math.exp(random.gauss(0, sig * math.sqrt(2)))
        f.add(p, t0 + 2 * i)
    v = f.realized_vol(600, now=t0 + 800)
    assert v == pytest.approx(sig, rel=0.2)


def test_vol_needs_enough_data():
    f = Feed("BTC")
    for i in range(10):
        f.add(100 + i, 1000 + i)
    assert f.vol(now=1010) is None


def test_momentum_and_mean_since():
    f = Feed("BTC")
    for i in range(100):
        f.add(100 + i * 0.01, 1000 + i * 2)
    assert f.momentum(120, now=1198) > 0
    assert f.mean_since(1190) == pytest.approx(sum(100 + i * 0.01 for i in range(95, 100)) / 5)


# ---- decide
def Q(**kw):
    return dict(dict(yes_bid=0.78, yes_ask=0.80, no_bid=0.20, no_ask=0.22), **kw)


def sig(p_side=0.95, side="yes"):
    return dict(side=side, p_side=p_side, p_up=p_side if side == "yes" else 1 - p_side, z=2, dist=100)


def test_decide_enters_with_edge_after_fees():
    d = decide(sig(0.95), Q(), 300, "balanced")
    assert d["enter"] and d["side"] == "yes" and d["price"] == 0.80 and d["edge"] < 0.15  # fee deducted


def test_decide_skips_for_each_reason():
    assert "warming" in decide(None, Q(), 300, "balanced")["reason"]
    assert "window" in decide(sig(), Q(), 20, "balanced")["reason"]
    assert "window" in decide(sig(), Q(), 800, "balanced")["reason"]
    assert "above max" in decide(sig(), Q(yes_ask=0.90, yes_bid=0.89), 300, "balanced")["reason"]
    assert "spread" in decide(sig(), Q(yes_bid=0.60), 300, "balanced")["reason"]
    assert "no clear setup" in decide(sig(0.82), Q(), 300, "balanced")["reason"]
    assert "no ask" in decide(sig(), Q(yes_ask=None), 300, "balanced")["reason"]


def test_decide_no_side_uses_no_ask():
    d = decide(sig(0.95, "no"), Q(no_ask=0.30, no_bid=0.28, yes_bid=0.70, yes_ask=0.72), 300, "balanced")
    assert d["enter"] and d["side"] == "no" and d["price"] == 0.30


def test_modes_are_ordered_by_strictness():
    s, q = sig(0.88), Q()
    assert not decide(s, q, 300, "conservative")["enter"]
    assert decide(s, q, 300, "aggressive")["enter"]


def test_hard_max_price_overrides_mode():
    q = Q(yes_ask=0.91, yes_bid=0.90)
    assert not decide(sig(0.999), q, 300, "aggressive", hard_max=0.90)["enter"]


# ---- second engine
def ladder_from_vol(spot, vol_ps, T=1800, strikes=None):
    from statistics import NormalDist
    out = []
    for k in strikes or [spot * (1 + d) for d in (-0.004, -0.002, 0.002, 0.004)]:
        p = NormalDist().cdf(math.log(spot / k) / (vol_ps * math.sqrt(T)))
        out.append({"strike_type": "greater", "floor_strike": k, "close_time": iso(time.time() + T),
                    "yes_bid_dollars": f"{p - 0.01:.4f}", "yes_ask_dollars": f"{p + 0.01:.4f}"})
    return out


def test_ladder_implied_vol_recovers_input():
    r = ladder_implied_vol(100000, ladder_from_vol(100000, 0.0004), time.time())
    assert r["n"] >= 2 and r["vol_ps"] == pytest.approx(0.0004, rel=0.15)


def test_ladder_ignores_wide_far_and_nonsensical_markets():
    bad = [{"strike_type": "between", "floor_strike": 1, "close_time": iso(time.time() + 900)},
           {"strike_type": "greater", "floor_strike": 100000, "close_time": iso(time.time() + 900),
            "yes_bid_dollars": "0.0000", "yes_ask_dollars": "0.0100"},
           {"strike_type": "greater", "floor_strike": 150000, "close_time": iso(time.time() + 900),
            "yes_bid_dollars": "0.40", "yes_ask_dollars": "0.60"}]
    assert ladder_implied_vol(100000, bad, time.time()) is None


def test_vol_scale_only_widens():
    assert vol_scale_from(0.0002, 0.0001) == 1.0
    assert vol_scale_from(0.0002, 0.0003) == pytest.approx(1.5)
    assert vol_scale_from(0.0002, 0.01) == 2.0
    assert vol_scale_from(None, 0.0003) == 1.0


def test_review_vetoes_extreme_disagreement_and_explains():
    s = sig(0.95)
    dec = decide(s, Q(yes_bid=0.50, yes_ask=0.52), 300, "balanced")
    rv = review(s, Q(yes_bid=0.50, yes_ask=0.52), dec, 0.0002, 1.0, None, 0.001)
    assert rv["verdict"] == "veto" and any("VETO" in l for l in rv["lines"])


def test_review_ok_and_mentions_ladder_and_momentum():
    s = sig(0.90)
    dec = decide(s, Q(), 300, "balanced")
    rv = review(s, Q(), dec, 0.0002, 1.4, {"vol_ps": 0.00028, "n": 5}, 0.001)
    text = " ".join(rv["lines"])
    assert rv["verdict"] == "ok" and "ladder" in text and "momentum" in text and "x1.40" in text


def test_mid_prob():
    assert mid_prob(Q()) == pytest.approx(0.79)
    assert mid_prob(dict(yes_bid=None, yes_ask=0.5)) is None


def test_short_window_alone_cannot_unlock_vol():
    f = Feed("BTC")
    for i in range(30):  # 60s of ticks: enough for the 2-min window, not the 10-min one
        f.add(100000 + (i % 3), 1000 + 2 * i)
    assert f.realized_vol(120, now=1060) is not None
    assert f.vol(now=1060) is None
