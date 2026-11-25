"""Scripted HTTP layer so tests drive the REAL Kalshi client (signing, retry, errors) with no network."""
import json as _json

from cryptography.hazmat.primitives.asymmetric import rsa

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class Resp:
    def __init__(self, code=200, js=None, garbage=False):
        self.status_code, self._js, self.garbage = code, js if js is not None else {}, garbage

    def json(self):
        if self.garbage:
            raise ValueError("not json")
        return self._js


class Script:
    def __init__(self, handler):
        self.handler, self.calls = handler, []

    def request(self, method, url, headers=None, json=None, timeout=None):
        self.calls.append((method, url, json))
        if method == "POST" and json and hasattr(self.handler, "last"):
            self.handler.last["body"] = json
        return self.handler(method, url)

    def posts(self):
        return [c for c in self.calls if c[0] == "POST" and "/portfolio/events/orders" in c[1]]


def good_handler(market, order_fill="1.00", positions=None, extra=None, balance_json=None):
    last = {}

    def h(method, url):
        if extra:
            r = extra(method, url)
            if r is not None:
                return r
        if method == "POST" and url.endswith("/portfolio/events/orders"):
            return Resp(201, {"order_id": "o1", "fill_count": order_fill, "remaining_count": "0.00"})
        if "/portfolio/fills" in url:        # consistent with the last order the script saw
            body = last.get("body")
            if not body:
                return Resp(200, {"fills": []})
            yes = float(body["price"])
            mine = yes if body["side"] == "bid" else 1 - yes
            from kalshi_client import trade_fee
            return Resp(200, {"fills": [{"count_fp": order_fill, "yes_price_dollars": f"{yes:.4f}",
                                         "no_price_dollars": f"{1 - yes:.4f}", "fee_cost": f"{trade_fee(mine, float(order_fill)):.4f}"}]})
        if method == "DELETE" and url.endswith("/portfolio/events/orders"):
            return Resp(204)
        if "/portfolio/positions" in url:
            return Resp(200, {"market_positions": positions or []})
        if "/portfolio/balance" in url:
            return Resp(200, balance_json or {"balance": 1000, "balance_dollars": "10.0000", "balance_breakdown": [
                {"exchange_index": 0, "balance": "0.0000"}, {"exchange_index": 2, "balance": "10.0000"}]})
        if "/series/" in url and "/candlesticks" not in url:
            return Resp(200, {"series": {"fee_type": "quadratic", "fee_multiplier": 1}})
        if "series_ticker=KXBTC15M" in url:
            return Resp(200, {"markets": [market]})
        if "series_ticker=KXBTC&" in url:
            return Resp(200, {"markets": []})
        if "/markets/" in url:
            return Resp(200, {"market": market})
        return Resp(404, {"error": {"code": "not_found", "message": "x"}})
    h.last = last
    return h
