import time
from datetime import datetime, timezone

from engine import DEFAULTS, State, new_round
from kalshi_client import trade_fee
from livelog import Ledger
from pilot import Pilot, STRONG


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
        res = dict(self.order_result or {"fill_count": f"{count}.00"})
        res.setdefault("order_id", f"oid{len(self.orders)}")
        return res

    fills_override = None
    settlements_list = ()

    def fills(self, order_id=None):
        """Synthesize Kalshi's fill record from the last order (consistent with its response) unless overridden."""
        if self.fills_override is not None:
            return self.fills_override
        t, outcome, action, count, price = self.orders[-1]
        res = self.order_result or {}
        n = float(res.get("fill_count", count))
        if n <= 0:
            return []
        yes_leg = float(res["average_fill_price"]) if res.get("average_fill_price") else (price if outcome == "yes" else 1 - price)
        mine = yes_leg if outcome == "yes" else 1 - yes_leg
        fee = float(res["average_fee_paid"]) * n if res.get("average_fee_paid") else trade_fee(mine, n)
        return [{"count_fp": f"{n:.2f}", "yes_price_dollars": f"{yes_leg:.4f}", "no_price_dollars": f"{1 - yes_leg:.4f}",
                 "fee_cost": f"{fee:.4f}"}]

    def settlements(self, ticker):
        return list(self.settlements_list)

    def balance_detail(self):
        return self.balance_json


FakeClient.balance_json = {"balance": 1000, "balance_dollars": "10.0000",
                           "balance_breakdown": [{"exchange_index": 0, "balance": "0.0000"}, {"exchange_index": 2, "balance": "10.0000"}]}


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


def strong(ticker="KXBTC15M-T1", ts=None, grade=STRONG):
    return dict(ticker=ticker, ts=ts if ts is not None else time.time(), grade=grade, checks=[], failed=[],
                flip=dict(touch_prob=0.1, safe=True, label="SAFE TO ENTER"), side="yes", price=0.8, edge=0.1)


def mklive(tmp_path, enabled=True, **over):
    """A State in live-pilot mode: pilot attached, LIVE enabled, ledger on."""
    st = mkstate(tmp_path, **over)
    st.live = True
    st.pilot = Pilot(path=str(tmp_path / "pilot.json"))
    st.pilot.live_enabled = enabled
    st.ledger = Ledger(str(tmp_path / "ledger.jsonl"), str(tmp_path / "pm.jsonl"))
    st.live_gate = lambda: (True, "ok")      # unit tests isolate the pilot rules; tests of the real gate attach a Ctx
    return st
