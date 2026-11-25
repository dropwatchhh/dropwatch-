"""LIVE pilot: credentials, hard-coded limits, breakers, Strong BUY NOW grading, order-path enforcement."""
import copy
import json
import time

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

import credentials
import pilot as pl
from engine import enter, finalize_round, cash_out
from kalshi_client import quotes
from signals import MODES, analyze, review
from tests.helpers import FakeClient, mklive, mkmarket, mkround, strong, mkstate

T = "KXBTC15M-T1"


# ------------------------------------------------------------------ 1. credentials never mix
@pytest.fixture
def keys(tmp_path):
    out = {}
    for n in ("live", "demo"):
        k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        (tmp_path / f"{n}.pem").write_bytes(pem)
        out[n] = str(tmp_path / f"{n}.pem")
    return out


def env(keys, live=True, demo=False):
    e = {}
    if live:
        e.update(KALSHI_LIVE_API_KEY_ID="LIVE-ID-aaaa1111", KALSHI_LIVE_PRIVATE_KEY_PATH=keys["live"])
    if demo:
        e.update(KALSHI_DEMO_API_KEY_ID="DEMO-ID-bbbb2222", KALSHI_DEMO_PRIVATE_KEY_PATH=keys["demo"])
    return e


def test_live_and_demo_load_separately_with_fixed_base_urls(keys):
    live = credentials.load("live", env(keys, True, False))
    demo = credentials.load("demo", env(keys, False, True))
    assert live.base == credentials.PROD_BASE and demo.base == credentials.DEMO_BASE
    assert live.key_id == "LIVE-ID-aaaa1111" and demo.key_id == "DEMO-ID-bbbb2222"
    assert live.fingerprint != demo.fingerprint


def test_mixing_is_refused_in_both_directions(keys):
    with pytest.raises(credentials.CredentialError, match="never be mixed"):
        credentials.load("live", env(keys, True, True))
    with pytest.raises(credentials.CredentialError, match="never be mixed"):
        credentials.load("demo", env(keys, True, True))


def test_legacy_shared_variables_and_base_url_override_are_not_honoured(keys):
    e = dict(env(keys), KALSHI_API_KEY_ID="x", KALSHI_PRIVATE_KEY_PATH=keys["live"])
    with pytest.raises(credentials.CredentialError, match="ambiguous"):
        credentials.load("live", e)
    e = dict(env(keys), KALSHI_BASE_URL="https://external-api.demo.kalshi.co/trade-api/v2")
    assert credentials.load("live", e).base == credentials.PROD_BASE          # override ignored
    from kalshi_client import Kalshi
    assert Kalshi.from_env().key is None and Kalshi.from_env().base == credentials.PROD_BASE


def test_missing_or_bad_key_errors_name_variables_not_values(keys, tmp_path):
    with pytest.raises(credentials.CredentialError, match="KALSHI_LIVE_API_KEY_ID"):
        credentials.load("live", {})
    (tmp_path / "bad.pem").write_text("not a key SECRETVALUE")
    with pytest.raises(credentials.CredentialError) as e:
        credentials.load("live", dict(env(keys), KALSHI_LIVE_PRIVATE_KEY_PATH=str(tmp_path / "bad.pem")))
    assert "SECRETVALUE" not in str(e.value) and "LIVE-ID-aaaa1111" not in str(e.value)


def test_same_key_for_live_and_demo_is_detected(keys):
    live = credentials.load("live", env(keys))
    with pytest.raises(credentials.CredentialError):
        credentials.assert_distinct(live, live.fingerprint)
    credentials.assert_distinct(live, "someotherfingerprint")


def test_paper_client_reads_no_credentials():
    c = credentials.public_client()
    assert c.key is None and c.key_id == "" and c.base == credentials.PROD_BASE


# ------------------------------------------------------------------ 2. limits: maxima fixed, UI can only lower
def test_maximums_are_the_requested_constants_and_immutable():
    assert dict(pl.PILOT_MAX) == dict(stake_usd=1.0, contracts=1, open_positions=1, trades_per_day=3,
                                      daily_pause_usd=2.0, hard_stop_usd=5.0)
    with pytest.raises(TypeError):
        pl.PILOT_MAX["stake_usd"] = 100


def test_limits_can_be_lowered_never_raised(tmp_path):
    p = pl.Pilot(path=str(tmp_path / "p.json"))
    assert p.lower("stake_usd", 0.5) == 0.5 and p.lower("trades_per_day", 2) == 2
    for name, bad in [("stake_usd", 0.6), ("stake_usd", 1.01), ("contracts", 2), ("hard_stop_usd", 6), ("daily_pause_usd", 3),
                      ("stake_usd", -1), ("stake_usd", float("nan")), ("stake_usd", True), ("stake_usd", "9"), ("bogus", 1)]:
        with pytest.raises(pl.PilotError):
            p.lower(name, bad)
    assert p.limits["stake_usd"] == 0.5
    assert pl.Pilot(path=str(tmp_path / "p.json")).limits["stake_usd"] == 0.5     # lowered values persist


def test_hand_edited_pilot_file_is_clamped_to_the_maximums(tmp_path):
    f = tmp_path / "p.json"
    f.write_text(json.dumps(dict(limits=dict(stake_usd=50, contracts=99, hard_stop_usd=1000, trades_per_day=-3, bogus=1))))
    p = pl.Pilot(path=str(f))
    assert p.limits["stake_usd"] == 1.0 and p.limits["contracts"] == 1 and p.limits["hard_stop_usd"] == 5.0
    assert p.limits["trades_per_day"] == 3 and "bogus" not in p.limits


def test_live_is_off_after_every_restart(tmp_path):
    p = pl.Pilot(path=str(tmp_path / "p.json"))
    p.live_enabled = True
    p.save()
    assert pl.Pilot(path=str(tmp_path / "p.json")).live_enabled is False


# ------------------------------------------------------------------ 2b. stake / contracts / one open / 3 per day / no add
@pytest.mark.parametrize("price", [0.05, 0.10, 0.30, 0.5, 0.72, 0.9, 0.95])
def test_every_buy_is_exactly_one_contract_and_at_most_one_dollar(tmp_path, price):
    st = mklive(tmp_path / "d" if (tmp_path / "d").mkdir() is None else tmp_path, size_per_trade_usd=50, mode="aggressive")
    mkround(st)
    c = FakeClient()
    ok = enter(c, st, True, T, "yes", price, 500, 1.0, "t", signal=strong())
    if price <= 0.95:
        pos = st.rounds[T]["pos"]
        if ok:
            assert pos["count"] == 1 and pos["price"] * pos["count"] + pos["fee"] <= 1.0 + 1e-9
    assert all(o[3] == 1 for o in c.orders)


def test_only_one_open_position_in_total_and_no_adding(tmp_path):
    st = mklive(tmp_path)
    c = FakeClient()
    for t in ("T1", "T2"):
        mkround(st, t)
    assert enter(c, st, True, "T1", "yes", .7, 500, 1.0, "t", signal=strong("T1"))
    assert not enter(c, st, True, "T2", "yes", .7, 500, 1.0, "t", signal=strong("T2")) and "already open" in st.rounds["T2"]["reason"]
    assert not enter(c, st, True, "T1", "yes", .7, 500, 1.0, "add", signal=strong("T1"))      # ADD refused
    assert len(c.orders) == 1
    c.markets["T1"] = mkmarket("T1", .6, .62)
    cash_out(c, st, "T1", True)                       # closed: a new position may open
    assert enter(c, st, True, "T2", "yes", .7, 500, 1.0, "t", signal=strong("T2"))


def test_max_three_orders_per_day_even_when_unfilled_and_resets_next_utc_day(tmp_path):
    day = ["2026-01-01"]
    st = mklive(tmp_path)
    st.today_fn = lambda: day[0]
    st.pilot.today_fn = lambda: day[0]
    st.pilot.day = day[0]
    c = FakeClient()
    c.order_result = {"fill_count": "0.00"}              # IOC never fills: attempts still count
    for i in range(3):
        mkround(st, f"T{i}")
        enter(c, st, True, f"T{i}", "yes", .7, 500, 1.0, "t", signal=strong(f"T{i}"))
    mkround(st, "T3")
    assert len(c.orders) == 3
    assert not enter(c, st, True, "T3", "yes", .7, 500, 1.0, "t", signal=strong("T3")) and len(c.orders) == 3
    assert "per day" in st.rounds["T3"]["reason"]
    day[0] = "2026-01-02"
    enter(c, st, True, "T3", "yes", .7, 500, 1.0, "t", signal=strong("T3"))
    assert len(c.orders) == 4                              # a new UTC day allows orders again (this IOC just did not fill)
    assert st.pilot.trades_today == 1


def test_live_off_blocks_every_order(tmp_path):
    st = mklive(tmp_path, enabled=False)
    mkround(st)
    c = FakeClient()
    assert not enter(c, st, True, T, "yes", .7, 500, 1.0, "t", signal=strong()) and c.orders == []
    assert "not enabled" in st.rounds[T]["reason"]


# ------------------------------------------------------------------ Strong BUY NOW is required in the order path
@pytest.mark.parametrize("sig", [None, "WAIT", "wrongticker", "stale"])
def test_order_path_refuses_anything_but_a_fresh_strong_signal_for_this_ticker(tmp_path, sig):
    st = mklive(tmp_path)
    mkround(st)
    s = {None: None, "WAIT": strong(grade="WAIT"), "wrongticker": strong("OTHER"), "stale": strong(ts=time.time() - 60)}[sig]
    c = FakeClient()
    assert not enter(c, st, True, T, "yes", .7, 500, 1.0, "t", signal=s) and c.orders == []


def good_inputs(**over):
    """A setup that satisfies every check: price ~$150 above target with tiny vol, ask 0.72."""
    kw = dict(price=100150.0, target=100000.0, secs=300, vol=0.00005, mom=0.0005)
    kw.update(over)
    sig = analyze(kw["price"], kw["target"], kw["secs"], kw["vol"], kw["mom"])
    q = dict(yes_bid=0.70, yes_ask=0.72, no_bid=0.28, no_ask=0.30, yes_ask_size=50.0, no_ask_size=50.0)
    q.update(over.get("q", {}))
    return sig, q, kw


def grade(**over):
    sig, q, kw = good_inputs(**over)
    rv = lambda d: review(sig, q, d, kw["vol"], 1.0, None, kw["mom"], 0.30)
    return pl.evaluate_signal(T, sig, q, over.get("secs", 300), kw["mom"], over.get("fresh", True), 1.0, 0.95, rv)


def test_strong_buy_now_when_every_check_passes():
    ev = grade()
    assert ev["grade"] == pl.STRONG and ev["failed"] == [] and ev["flip"]["label"] == "SAFE TO ENTER"
    assert ev["side"] == "yes" and ev["edge"] > 0.10


@pytest.mark.parametrize("name,over,failed_part", [
    ("stale data", dict(fresh=False), "fresh"),
    ("ask too high for conservative", dict(q=dict(yes_ask=0.80, yes_bid=0.78)), "conservative"),
    ("thin edge", dict(price=100010.0), "conservative"),
    ("too early", dict(secs=700), "conservative"),
    ("too late", dict(secs=60), "conservative"),
    ("wide spread", dict(q=dict(yes_bid=0.60)), "conservative"),
    ("market disagrees (veto)", dict(q=dict(yes_bid=0.40, yes_ask=0.42)), "reasoning"),
    ("adverse momentum", dict(mom=-0.0005), "flip risk"),
    ("no depth", dict(q=dict(yes_ask_size=0.0)), "depth"),
])
def test_each_failed_check_blocks_strong(name, over, failed_part):
    ev = grade(**over)
    assert ev["grade"] == "WAIT" and any(failed_part in f for f in ev["failed"]), (name, ev["failed"])


def test_flip_risk_gate_blocks_when_target_is_too_close_to_hold():
    # a setup that passes the rules but sits within ~1 sigma of the target: touch chance > 25%
    ev = grade(price=100020.0, vol=0.00012, q=dict(yes_bid=0.60, yes_ask=0.62, no_bid=0.38, no_ask=0.40))
    assert ev["flip"]["touch_prob"] > pl.FLIP_MAX_TOUCH and ev["flip"]["label"] == "NOT SAFE" and ev["grade"] == "WAIT"


# ------------------------------------------------------------------ 3. loss breakers
def test_daily_pause_at_minus_two_blocks_until_next_utc_day(tmp_path):
    day = ["2026-01-01"]
    st = mklive(tmp_path)
    st.pilot.today_fn = lambda: day[0]
    st.pilot.day = day[0]
    assert st.pilot.record_pnl(-1.0) is None and not st.pilot.daily_paused()
    assert st.pilot.record_pnl(-1.0) == "daily_pause" and st.pilot.daily_paused()
    mkround(st)
    assert not enter(FakeClient(), st, True, T, "yes", .7, 500, 1.0, "t", signal=strong()) and "paused" in st.rounds[T]["reason"]
    day[0] = "2026-01-02"
    assert not st.pilot.daily_paused() and enter(FakeClient(), st, True, T, "yes", .7, 500, 1.0, "t", signal=strong())


def test_trade_that_could_cross_the_daily_pause_is_blocked_beforehand(tmp_path):
    st = mklive(tmp_path)
    st.pilot.record_pnl(-1.5)
    mkround(st)
    assert not enter(FakeClient(), st, True, T, "yes", .7, 500, 1.0, "t", signal=strong())
    assert "daily pause" in st.rounds[T]["reason"] and st.pilot.daily_pnl == -1.5


def test_hard_stop_at_minus_five_disarms_disables_live_and_survives_restart(tmp_path):
    st = mklive(tmp_path)
    st.armed = True
    st.pilot.record_pnl(-2.0)
    st.pilot.today_fn = lambda: "2099-01-01"      # a later day: the cumulative stop is not a daily one
    st.realize(-3.0)
    assert st.pilot.hard_stopped and not st.pilot.live_enabled and not st.armed
    assert any(e["event"] == "breaker" for e in st.ledger.events())
    p2 = pl.Pilot(path=str(tmp_path / "pilot.json"))
    assert p2.hard_stopped and not p2.live_enabled and p2.pnl_total == pytest.approx(-5.0)
    with pytest.raises(pl.PilotError, match="hard stop"):
        p2.enable(pl.ENABLE_PHRASE, True, [])


def test_hard_stop_needs_two_typed_confirmations_in_order(tmp_path):
    p = pl.Pilot(path=str(tmp_path / "p.json"))
    p.record_pnl(-5.0)
    assert p.hard_stopped
    with pytest.raises(pl.PilotError):
        p.reset_hard_stop(pl.RESET_PHRASE_2)                     # wrong order
    assert p.reset_hard_stop(pl.RESET_PHRASE_1) == "step1_ok" and p.hard_stopped
    with pytest.raises(pl.PilotError, match="restarted"):
        p.reset_hard_stop("wrong")                               # a wrong phrase restarts the sequence
    assert p.reset_stage == 0 and p.hard_stopped
    p.reset_hard_stop(pl.RESET_PHRASE_1)
    assert p.reset_hard_stop(pl.RESET_PHRASE_2) == "reset" and not p.hard_stopped


def test_reset_does_not_turn_live_on_and_moves_the_baseline(tmp_path):
    p = pl.Pilot(path=str(tmp_path / "p.json"))
    p.live_enabled = True
    p.record_pnl(-5.0)
    p.reset_hard_stop(pl.RESET_PHRASE_1)
    p.reset_hard_stop(pl.RESET_PHRASE_2)
    assert not p.live_enabled and p.drawdown() == 0 and p.pnl_total == -5.0
    p.live_enabled = True
    p.record_pnl(-4.0)
    assert not p.hard_stopped                                    # measured from the reset point
    p.record_pnl(-1.0)
    assert p.hard_stopped


def test_first_reset_confirmation_expires(tmp_path):
    now = [1000.0]
    p = pl.Pilot(path=str(tmp_path / "p.json"), now_fn=lambda: now[0])
    p.record_pnl(-5.0)
    p.reset_hard_stop(pl.RESET_PHRASE_1)
    now[0] += pl.RESET_STAGE_TTL + 1
    with pytest.raises(pl.PilotError):
        p.reset_hard_stop(pl.RESET_PHRASE_2)


def test_breakers_use_net_pnl_after_fees_from_settlement(tmp_path):
    st = mklive(tmp_path)
    r = mkround(st)
    enter(FakeClient(), st, True, T, "yes", .7, 500, 1.0, "t", signal=strong())
    finalize_round(st, r, "no")
    assert st.pilot.daily_pnl == pytest.approx(-(0.7 + r["pos"]["fee"]), abs=1e-4)
