import time
from datetime import datetime, timezone

from engine import DEFAULTS, State, new_round


class FakeClient:
    """Stands in for Kalshi. Any real network use would fail loudly."""

    def __init__(self):
        self.markets, self.orders, self.order_result, self.order_error = {}, [], None, None
        self.positions_list, self.ladder, self.open = [], [], None

    def market(self, t):
        return self.markets[t]

    def open_market(self, series, now=None):
        return self.open

    def btc_ladder(self):
        return self.ladder

    def positions(self):
        return self.positions_list

    def place_order(self, ticker, outcome, action, count, price):
        self.orders.append((ticker, outcome, action, count, price))
        if self.order_error:
            raise self.order_error
        return self.order_result or {"fill_count": f"{count}.00"}


class NoOrdersClient(FakeClient):
    def place_order(self, *a, **k):
        raise AssertionError("a real order was attempted")


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat().replace("+00:00", "Z")


def mkstate(tmp_path, today_fn=None, armed=True, **over):
    cfg = {**DEFAULTS, **over}
    kw = dict(path=str(tmp_path / "state.json"), trades_path=str(tmp_path / "trades.csv"),
              snaps_path=str(tmp_path / "snaps.csv"))
    if today_fn:
        kw["today_fn"] = today_fn
    st = State(cfg, **kw)
    st.armed = armed
    return st


def mkround(st, ticker="KXBTC15M-T1", close_in=300):
    m = dict(ticker=ticker, close_time=iso(time.time() + close_in))
    dec = dict(reason="test", edge=0.1, side="yes")
    r = new_round("BTC", m, dict(time="t", trading="paper"), ["r"], dec, st)
    st.rounds[ticker] = r
    return r


def mkmarket(ticker, yb, ya, nb=None, na=None, result="", close_in=300, strike=100000.0, ask_size="500.00"):
    return {"ticker": ticker, "close_time": iso(time.time() + close_in), "floor_strike": strike,
            "yes_bid_dollars": f"{yb:.4f}", "yes_ask_dollars": f"{ya:.4f}",
            "no_bid_dollars": f"{(1 - ya if nb is None else nb):.4f}", "no_ask_dollars": f"{(1 - yb if na is None else na):.4f}",
            "yes_ask_size_fp": ask_size, "yes_bid_size_fp": ask_size, "result": result}
