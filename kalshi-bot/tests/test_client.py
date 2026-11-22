import base64

import pytest
import requests
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from kalshi_client import (Kalshi, KalshiError, fee_per_contract, price_dollars, quotes, sign_message,
                           trade_fee, v2_order_body)


@pytest.fixture(scope="module")
def key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def test_signature_verifies_and_excludes_query(key):
    ts = "1700000000000"
    sig = sign_message(key, ts, "get", "/trade-api/v2/markets?series_ticker=X&status=open")
    key.public_key().verify(base64.b64decode(sig), f"{ts}GET/trade-api/v2/markets".encode(),
                            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
                            hashes.SHA256())


def test_headers_have_ms_timestamp_and_sign_full_path(key):
    c = Kalshi("kid", key)
    h = c._headers("POST", "/portfolio/events/orders", True)
    assert h["KALSHI-ACCESS-KEY"] == "kid" and len(h["KALSHI-ACCESS-TIMESTAMP"]) == 13
    msg = (h["KALSHI-ACCESS-TIMESTAMP"] + "POST/trade-api/v2/portfolio/events/orders").encode()
    key.public_key().verify(base64.b64decode(h["KALSHI-ACCESS-SIGNATURE"]), msg,
                            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
                            hashes.SHA256())


def test_auth_without_credentials_fails_closed():
    with pytest.raises(KalshiError):
        Kalshi()._headers("GET", "/portfolio/balance", True)


def test_price_parsing_dollars_and_legacy_cents():
    assert price_dollars({"yes_ask_dollars": "0.8500"}, "yes_ask") == 0.85
    assert price_dollars({"yes_ask": 85}, "yes_ask") == 0.85
    assert price_dollars({}, "yes_ask") is None
    assert quotes({"yes_bid_dollars": "0.0010", "yes_ask_dollars": "0.0100"})["yes_bid"] == 0.001


def test_fee_model():
    assert trade_fee(0.5, 10) == 0.18          # 0.175 rounds UP to the cent
    assert trade_fee(0.5, 100) == 1.75         # float noise must not push this to 1.76
    assert trade_fee(0.99, 1) == 0.01          # always at least a cent when nonzero
    assert trade_fee(0.3, 7) == trade_fee(0.7, 7)  # symmetric in P
    assert abs(fee_per_contract(0.5) - 0.0175) < 1e-12
    assert trade_fee(0.5, 10, mult=2) > trade_fee(0.5, 10)


@pytest.mark.parametrize("outcome,action,side,price,reduce", [
    ("yes", "buy", "bid", "0.6000", False),
    ("no", "buy", "ask", "0.6000", False),    # buy NO at 0.40 == ask at yes-price 0.60
    ("yes", "sell", "ask", "0.4000", True),
    ("no", "sell", "bid", "0.6000", True),
])
def test_v2_order_mapping(outcome, action, side, price, reduce):
    p = 0.6 if (outcome, action) in (("yes", "buy"),) else 0.4
    if outcome == "no":
        p = 0.4
    b = v2_order_body("T", outcome, action, 5, p)
    assert b["side"] == side and b["price"] == price
    assert b["count"] == "5.00" and b["time_in_force"] == "immediate_or_cancel"
    assert b.get("reduce_only", False) is reduce and b["self_trade_prevention_type"] == "taker_at_cross"


def test_v2_order_rejects_bad_input():
    for args in [("T", "yes", "buy", 0, 0.5), ("T", "yes", "buy", 1, 1.0), ("T", "up", "buy", 1, 0.5)]:
        with pytest.raises(ValueError):
            v2_order_body(*args)


class Resp:
    def __init__(self, code, js=None):
        self.status_code, self._js = code, js or {}

    def json(self):
        return self._js


class Sess:
    def __init__(self, seq):
        self.seq, self.calls = list(seq), 0

    def request(self, *a, **k):
        self.calls += 1
        x = self.seq.pop(0)
        if isinstance(x, Exception):
            raise x
        return x


def client(seq):
    sleeps = []
    return Kalshi(session=Sess(seq), sleep=sleeps.append), sleeps


def test_get_retries_with_backoff_on_429_and_5xx_and_network():
    c, sleeps = client([Resp(429), Resp(503), requests.ConnectionError(), Resp(200, {"ok": 1})])
    assert c.req("GET", "/x") == {"ok": 1}
    assert len(sleeps) == 3 and sleeps[2] > sleeps[0] * 0.9  # grows


def test_get_gives_up_after_max_retries():
    c, _ = client([Resp(429)] * 10)
    with pytest.raises(KalshiError):
        c.req("GET", "/x")
    assert c.s.calls == c.max_retries + 1


def test_post_never_retried_on_ambiguous_failures():
    for first in (requests.Timeout(), Resp(500)):
        c, _ = client([first, Resp(201, {"order_id": "x"})])
        with pytest.raises(KalshiError) as e:
            c.req("POST", "/o", {}, auth=False)
        assert e.value.ambiguous and c.s.calls == 1


def test_post_retries_429_only():
    c, _ = client([Resp(429), Resp(201, {"order_id": "x"})])
    assert c.req("POST", "/o", {})["order_id"] == "x"


def test_4xx_raises_with_code_and_not_retried():
    c, _ = client([Resp(400, {"error": {"code": "invalid_price", "message": "bad"}})])
    with pytest.raises(KalshiError) as e:
        c.req("GET", "/x")
    assert e.value.code == "invalid_price" and not e.value.ambiguous and c.s.calls == 1


def test_open_market_picks_soonest_closing_and_ignores_expired():
    import time as t
    from tests.helpers import iso
    c, _ = client([Resp(200, {"markets": [
        {"ticker": "B", "close_time": iso(t.time() + 900)}, {"ticker": "A", "close_time": iso(t.time() + 300)},
        {"ticker": "OLD", "close_time": iso(t.time() - 5)}]})])
    assert c.open_market("KXBTC15M")["ticker"] == "A"
