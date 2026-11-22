"""Kalshi REST client: RSA-PSS signing, retry/backoff, V2 orders, fee model.

Secrets: the private key is loaded from disk and used only to sign. It is never
logged, printed or included in exception text.
"""
import base64
import math
import os
import random
import time
import uuid
from datetime import datetime
from urllib.parse import urlparse

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

DEFAULT_BASE = "https://api.elections.kalshi.com/trade-api/v2"
FEE_RATE = 0.07  # quadratic taker fee: ceil_cent(0.07 * mult * C * P * (1-P))


class KalshiError(Exception):
    """ambiguous=True means we cannot know whether the request took effect."""

    def __init__(self, msg, status=None, code=None, ambiguous=False):
        super().__init__(msg)
        self.status, self.code, self.ambiguous = status, code, ambiguous


# ------------------------------------------------------------------ pure helpers
def sign_message(key, ts, method, full_path):
    """base64 RSA-PSS/SHA256 over ts + METHOD + path (query string excluded)."""
    msg = f"{ts}{method.upper()}{full_path.split('?')[0]}".encode()
    sig = key.sign(
        msg,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
        hashes.SHA256(),
    )
    return base64.b64encode(sig).decode()


def price_dollars(m, field):
    """Read a quote as dollars. Handles `<field>_dollars` strings and legacy int cents."""
    v = m.get(field + "_dollars")
    if v not in (None, ""):
        return float(v)
    v = m.get(field)
    return None if v in (None, "") else float(v) / 100.0


def size_fp(m, field):
    v = m.get(field)
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def quotes(m):
    return dict(
        yes_bid=price_dollars(m, "yes_bid"), yes_ask=price_dollars(m, "yes_ask"),
        no_bid=price_dollars(m, "no_bid"), no_ask=price_dollars(m, "no_ask"),
        yes_ask_size=size_fp(m, "yes_ask_size_fp"),
        no_ask_size=size_fp(m, "no_ask_size_fp") or size_fp(m, "yes_bid_size_fp"),
    )


def parse_time(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def fee_per_contract(price, mult=1.0):
    """Unrounded per-contract fee, used for edge estimates."""
    return FEE_RATE * mult * price * (1 - price)


def trade_fee(price, count, mult=1.0):
    """Order fee in dollars, rounded UP to the cent (conservative)."""
    raw = FEE_RATE * mult * count * price * (1 - price)
    return math.ceil(round(raw * 100, 6)) / 100.0


def v2_order_body(ticker, outcome, action, count, price, client_order_id=None):
    """Map (yes|no, buy|sell) onto the V2 YES-leg book.

    bid = buy YES, ask = sell YES; buying NO at q is an ask at 1-q. All orders
    are immediate-or-cancel limit orders; exits are reduce_only.
    """
    if outcome not in ("yes", "no") or action not in ("buy", "sell"):
        raise ValueError("bad outcome/action")
    if not 0 < price < 1 or count < 1:
        raise ValueError("bad price/count")
    book = "bid" if (outcome == "yes") == (action == "buy") else "ask"
    yes_price = price if outcome == "yes" else 1 - price
    body = {
        "ticker": ticker,
        "client_order_id": client_order_id or uuid.uuid4().hex,
        "side": book,
        "count": f"{int(count)}.00",
        "price": f"{yes_price:.4f}",
        "time_in_force": "immediate_or_cancel",
        "self_trade_prevention_type": "taker_at_cross",
    }
    if action == "sell":
        body["reduce_only"] = True
    return body


# ------------------------------------------------------------------ client
class Kalshi:
    def __init__(self, key_id="", key=None, base=None, session=None, sleep=time.sleep, max_retries=4):
        self.key_id, self.key = key_id, key
        self.base = (base or os.getenv("KALSHI_BASE_URL") or DEFAULT_BASE).rstrip("/")
        self.prefix = urlparse(self.base).path  # e.g. /trade-api/v2 (what gets signed)
        self.s = session or requests.Session()
        self.sleep, self.max_retries = sleep, max_retries
        self.allow_orders = False  # bot.py sets this True ONLY for live mode (trading=live AND --live)
        self.buy_limits = None     # (max_cost_usd, max_price): the client refuses buys without it, and above it

    @classmethod
    def from_env(cls):
        key_id = os.getenv("KALSHI_API_KEY_ID", "")
        path = os.getenv("KALSHI_PRIVATE_KEY_PATH", "")
        key = None
        if path and os.path.exists(path):
            with open(path, "rb") as f:
                key = serialization.load_pem_private_key(f.read(), password=None)
        return cls(key_id, key)

    def _headers(self, method, path, auth):
        h = {"Content-Type": "application/json"}
        if auth:
            if not (self.key and self.key_id):
                raise KalshiError("API credentials not configured")
            ts = str(int(time.time() * 1000))
            h.update({
                "KALSHI-ACCESS-KEY": self.key_id,
                "KALSHI-ACCESS-TIMESTAMP": ts,
                "KALSHI-ACCESS-SIGNATURE": sign_message(self.key, ts, method, self.prefix + path),
            })
        return h

    def _backoff(self, attempt):
        self.sleep(min(8.0, 0.5 * 2 ** attempt) * (0.5 + random.random()))

    def req(self, method, path, body=None, auth=False):
        """GETs retry on network errors, 429 and 5xx. POSTs retry only on 429
        (never processed); a POST network error/5xx is ambiguous and is raised."""
        is_get = method == "GET"
        last = None
        for attempt in range(self.max_retries + 1):
            try:
                r = self.s.request(method, self.base + path, headers=self._headers(method, path, auth),
                                   json=body, timeout=10)
            except requests.RequestException as e:
                last = KalshiError(f"network error: {type(e).__name__}", ambiguous=not is_get)
                if not is_get:
                    raise last
                self._backoff(attempt)
                continue
            if r.status_code == 429:
                last = KalshiError("rate limited", 429, "too_many_requests")
                self._backoff(attempt)
                continue
            if r.status_code >= 500:
                last = KalshiError(f"server error {r.status_code}", r.status_code, ambiguous=not is_get)
                if not is_get:
                    raise last
                self._backoff(attempt)
                continue
            if r.status_code >= 400:
                code, msg = None, ""
                try:
                    e = r.json().get("error", {})
                    code, msg = e.get("code"), e.get("message", "")
                except Exception:
                    pass
                raise KalshiError(f"HTTP {r.status_code} {code or ''} {msg}".strip(), r.status_code, code)
            if r.status_code == 204:
                return {}
            try:
                return r.json()
            except ValueError:
                # a 2xx we cannot parse: for a write we cannot know what happened
                raise KalshiError("unparseable response", r.status_code, ambiguous=not is_get)
        raise last or KalshiError("request failed")

    # ---- public market data
    def open_market(self, series, now=None):
        """Soonest-closing open market in the series = the current round."""
        d = self.req("GET", f"/markets?series_ticker={series}&status=open&limit=10")
        now = now or time.time()
        ms = [m for m in d.get("markets", []) if parse_time(m["close_time"]).timestamp() > now]
        ms.sort(key=lambda m: m["close_time"])
        return ms[0] if ms else None

    def market(self, ticker):
        return self.req("GET", f"/markets/{ticker}")["market"]

    def series_fee_multiplier(self, series):
        s = self.req("GET", f"/series/{series}")["series"]
        if s.get("fee_type") != "quadratic":
            raise KalshiError(f"unsupported fee type {s.get('fee_type')}")
        return float(s.get("fee_multiplier", 1))

    def btc_ladder(self, series="KXBTC"):
        """Open strike ladder for the soonest-closing BTC event (for the reasoning engine)."""
        d = self.req("GET", f"/markets?series_ticker={series}&status=open&limit=1000")
        ms = d.get("markets", [])
        if not ms:
            return []
        soonest = min(m["close_time"] for m in ms)
        return [m for m in ms if m["close_time"] == soonest]

    # ---- authenticated
    def balance_usd(self):
        b = self.req("GET", "/portfolio/balance", auth=True)
        return float(b["balance_dollars"]) if b.get("balance_dollars") else b["balance"] / 100.0

    def positions(self):
        out, cursor = [], ""
        for _ in range(20):
            d = self.req("GET", "/portfolio/positions?limit=200" + (f"&cursor={cursor}" if cursor else ""), auth=True)
            out += d.get("market_positions", [])
            cursor = d.get("cursor") or ""
            if not cursor:
                break
        return out

    def place_order(self, ticker, outcome, action, count, price):
        if not self.allow_orders:
            raise KalshiError("order refused: client not enabled for live orders")
        if action == "buy":
            if not self.buy_limits:
                raise KalshiError("order refused: buy limits not configured")
            max_cost, max_price = self.buy_limits
            if price > max_price + 1e-9 or price * count > max_cost + 1e-9:
                raise KalshiError(f"order refused: {count} @ {price} exceeds client-level limits")
        return self.req("POST", "/portfolio/events/orders",
                        v2_order_body(ticker, outcome, action, count, price), auth=True)

    def cancel_all_orders(self):
        """Cancel every resting event-market order (DELETE /portfolio/events/orders, 204)."""
        return self.req("DELETE", "/portfolio/events/orders", auth=True)

    def fills(self, order_id=None):
        """Fills for an order (or recent fills). Used to verify logged prices/fees against Kalshi."""
        out, cursor = [], ""
        for _ in range(10):
            q = "/portfolio/fills?limit=200" + (f"&order_id={order_id}" if order_id else "") + (f"&cursor={cursor}" if cursor else "")
            d = self.req("GET", q, auth=True)
            out += d.get("fills", [])
            cursor = d.get("cursor") or ""
            if not cursor:
                break
        return out
