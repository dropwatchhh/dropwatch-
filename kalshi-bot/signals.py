"""Price feed, probability model ("terminal"), decision rules, and the second
"reasoning" engine that cross-checks the model against the market.

Model in one paragraph: a round resolves YES if the average of the last 60 s of
CF Benchmarks' BRTI is >= floor_strike. We only see Coinbase spot (a proxy), so
we treat log-price as a driftless random walk with realized volatility, account
for the 60 s averaging (which shrinks variance), add an explicit Coinbase-vs-BRTI
basis error term, and shrink the result toward 0.5 for fat tails.
"""
import math
import statistics
import time
from collections import deque
from statistics import NormalDist

import requests

from kalshi_client import fee_per_contract, parse_time, price_dollars

COINBASE = "https://api.coinbase.com/v2/prices/{}-USD/spot"
SERIES = {"BTC": "KXBTC15M", "ETH": "KXETH15M", "SOL": "KXSOL15M"}
AVG_WINDOW = 60.0  # seconds of BRTI averaged at settlement

MODES = {
    "conservative": dict(min_edge=0.10, max_price=0.75, min_left=90, max_left=600, max_spread=0.04),
    "balanced":     dict(min_edge=0.07, max_price=0.85, min_left=60, max_left=720, max_spread=0.06),
    "aggressive":   dict(min_edge=0.04, max_price=0.92, min_left=30, max_left=840, max_spread=0.10),
}
_ND = NormalDist()


def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


# ------------------------------------------------------------------ feed
class Feed:
    def __init__(self, asset, maxlen=3600):
        self.asset = asset
        self.ticks = deque(maxlen=maxlen)  # (ts, price)

    def add(self, price, ts=None):
        self.ticks.append((ts if ts is not None else time.time(), float(price)))

    def poll(self):
        r = requests.get(COINBASE.format(self.asset), timeout=5)
        r.raise_for_status()
        p = float(r.json()["data"]["amount"])
        self.add(p)
        return p

    def last(self):
        return self.ticks[-1][1] if self.ticks else None

    def age(self, now=None):
        return float("inf") if not self.ticks else (now or time.time()) - self.ticks[-1][0]

    def is_fresh(self, max_age=5.0, now=None):
        return self.age(now) <= max_age

    def _win(self, secs, now=None):
        cut = (now or time.time()) - secs
        return [(t, p) for t, p in self.ticks if t >= cut]

    def momentum(self, secs=120, now=None):
        w = self._win(secs, now)
        if len(w) < 5 or w[-1][0] - w[0][0] < secs * 0.5:
            return 0.0
        return (w[-1][1] - w[0][1]) / w[0][1]

    def realized_vol(self, secs=600, now=None):
        """Per-second vol of log price: sqrt(sum r^2 / sum dt). None until enough data."""
        w = self._win(secs, now)
        if len(w) < 20 or w[-1][0] - w[0][0] < secs * 0.3:
            return None
        sr2 = sum(math.log(b[1] / a[1]) ** 2 for a, b in zip(w, w[1:]))
        dt = w[-1][0] - w[0][0]
        return math.sqrt(sr2 / dt) if dt > 0 else None

    def vol(self, now=None):
        """Per-second vol used by the model: the 10-min realized estimate (needs >= 3 min of
        ticks, so the bot never trades on a short noisy window). history.py uses the same."""
        return self.realized_vol(600, now)

    def high_low(self, secs=600, now=None):
        w = [p for _, p in self._win(secs, now)]
        return (max(w), min(w)) if w else (None, None)

    def mean_since(self, ts):
        w = [p for t, p in self.ticks if t >= ts]
        return statistics.fmean(w) if w else None


# ------------------------------------------------------------------ model
def analyze(price, target, secs_left, vol_ps, momentum=0.0, window_mean=None,
            basis_bps=2.0, shrink=0.9, momentum_weight=0.0, vol_scale=1.0):
    """P(60s-average index at close >= target). Returns None if not computable.

    T > 60s: average of last 60s of a random walk has variance s^2*(T-60 + 60/3).
    T <= 60s: part of the window is already observed (window_mean); only the
    remaining s seconds are uncertain, each weighted s/60.
    """
    if vol_ps is None or secs_left <= 0 or price <= 0 or target <= 0:
        return None
    s_ps = vol_ps * vol_scale
    T = secs_left
    if T > AVG_WINDOW:
        std_log = s_ps * math.sqrt((T - AVG_WINDOW) + AVG_WINDOW / 3.0)
        expected = price
    else:
        obs = window_mean if window_mean else price
        w_future = T / AVG_WINDOW
        std_log = s_ps * math.sqrt(T / 3.0) * w_future
        expected = (1 - w_future) * obs + w_future * price
    std_price = math.hypot(price * std_log, price * basis_bps / 1e4)
    expected *= 1 + momentum_weight * momentum
    z = (expected - target) / std_price
    p = 0.5 + shrink * (norm_cdf(z) - 0.5)
    p = min(max(p, 0.01), 0.99)
    return dict(p_up=p, side="yes" if p >= 0.5 else "no", p_side=max(p, 1 - p),
                z=z, std_price=std_price, dist=price - target)


def mid_prob(q):
    """Market-implied P(yes) from the mid of the yes book, or None."""
    b, a = q.get("yes_bid"), q.get("yes_ask")
    if b is None or a is None or a <= 0:
        return None
    return (b + a) / 2.0


def decide(sig, q, secs_left, mode, fee_mult=1.0, hard_max=0.95):
    """Rules gate. Returns dict(enter, side, price, edge, reason, in_window)."""
    cfg = MODES[mode]
    out = dict(enter=False, side=None, price=None, edge=None, reason="", in_window=False)
    if sig is None:
        out["reason"] = "warming up (not enough price data)"
        return out
    side = sig["side"]
    ask = q["yes_ask"] if side == "yes" else q["no_ask"]
    bid = q["yes_bid"] if side == "yes" else q["no_bid"]
    out["side"] = side
    if ask is None or not 0 < ask < 1:
        out["reason"] = "no ask available"
        return out
    out["price"] = ask
    out["edge"] = sig["p_side"] - ask - fee_per_contract(ask, fee_mult)
    out["in_window"] = cfg["min_left"] <= secs_left <= cfg["max_left"]
    if not out["in_window"]:
        out["reason"] = f"outside entry window ({int(secs_left)}s left)"
    elif ask > min(cfg["max_price"], hard_max):
        out["reason"] = f"ask {ask:.2f} above max {min(cfg['max_price'], hard_max):.2f}"
    elif bid is not None and ask - bid > cfg["max_spread"]:
        out["reason"] = f"spread {ask - bid:.2f} too wide"
    elif out["edge"] < cfg["min_edge"]:
        out["reason"] = f"no clear setup (edge {out['edge']:+.3f} < {cfg['min_edge']:.2f} after fees)"
    else:
        out["enter"] = True
        out["reason"] = f"edge {out['edge']:+.3f} after fees: model {sig['p_side']:.2f} vs ask {ask:.2f}"
    return out


# ------------------------------------------------------------------ second engine
def ladder_implied_vol(spot, markets, now_ts, max_dist=0.02):
    """Invert the open hourly BTC strike ladder into an implied per-second vol.

    For each 'greater' strike K near spot with a tight two-sided book, solve
    p = Phi(ln(S/K) / (sigma*sqrt(T))) for sigma. Returns median or None.
    """
    est = []
    for m in markets:
        if m.get("strike_type") != "greater" or not m.get("floor_strike"):
            continue
        bid, ask = price_dollars(m, "yes_bid"), price_dollars(m, "yes_ask")
        if bid is None or ask is None or bid <= 0 or ask >= 1 or ask - bid > 0.05:
            continue
        p = (bid + ask) / 2
        T = parse_time(m["close_time"]).timestamp() - now_ts
        x = math.log(spot / float(m["floor_strike"]))
        if not 0.08 <= p <= 0.92 or T < 300 or abs(x) > max_dist:
            continue
        z = _ND.inv_cdf(p)
        if abs(z) < 0.2 or x * z <= 0:
            continue
        est.append((x / z) / math.sqrt(T))
    if len(est) < 2:
        return None
    return dict(vol_ps=statistics.median(est), n=len(est))


def vol_scale_from(realized, implied, cap=2.0):
    """Widen (never narrow) our uncertainty if the market expects bigger moves."""
    if not realized or not implied:
        return 1.0
    return min(max(implied / realized, 1.0), cap)


def review(sig, q, decision, realized_vol, vol_scale, ladder, momentum, max_disagreement=0.30):
    """Plain-English cross-check of the model against the market.

    verdict 'veto' blocks an entry; 'ok' lets the rules gate stand.
    """
    lines, verdict = [], "ok"
    if sig is None:
        return dict(verdict="ok", lines=["Not enough data to form a view yet."])
    side = decision["side"] or sig["side"]
    label = "UP" if side == "yes" else "DOWN"
    mid = mid_prob(q)
    if mid is None:
        lines.append(f"Model likes {label} at {sig['p_side']:.0%}, but the market has no two-sided quote to compare.")
    else:
        mkt = mid if side == "yes" else 1 - mid
        gap = sig["p_side"] - mkt
        lines.append(f"Model: {label} wins {sig['p_side']:.0%}. Market-implied (mid): {mkt:.0%}. Gap {gap:+.0%}.")
        if gap > max_disagreement:
            verdict = "veto"
            lines.append(f"VETO: a {gap:.0%} disagreement with the market is more likely a model error "
                         f"(Coinbase vs the real index, stale data) than a real edge.")
        elif abs(gap) < 0.03:
            lines.append("Model and market agree: no informational edge on this side.")
    if ladder:
        impl = ladder["vol_ps"] * math.sqrt(60) * 100
        real = (realized_vol or 0) * math.sqrt(60) * 100
        lines.append(f"Hourly BTC ladder ({ladder['n']} strikes) implies {impl:.3f}%/min vol vs my realized "
                     f"{real:.3f}%/min" + (f" -> widened my uncertainty x{vol_scale:.2f}." if vol_scale > 1.001
                                          else " -> consistent, no adjustment."))
    else:
        lines.append("Hourly ladder unavailable (no tight two-sided strikes near spot); using realized vol only.")
    if abs(momentum) > 0:
        mom_dir = "UP" if momentum > 0 else "DOWN"
        note = "with" if mom_dir == label else "against"
        lines.append(f"2-min momentum {momentum * 100:+.3f}% is {note} this side (informational; weight in model is configurable).")
    lines.append(f"Distance to target {sig['dist']:+.2f} = {sig['z']:+.2f} sigma.")
    lines.append(f"Decision: {'ENTER ' + label if decision['enter'] and verdict == 'ok' else 'SKIP'} - {decision['reason']}")
    return dict(verdict=verdict, lines=lines)
