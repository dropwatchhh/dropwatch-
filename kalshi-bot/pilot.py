"""LIVE pilot controls. Everything here can only make trading MORE restrictive.

PILOT_MAX are code constants. The UI/API can lower the working limits but never raise them, and a
hand-edited pilot.json is clamped to these maximums on load. LIVE starts OFF every process start and
needs a typed phrase to enable. Nothing here learns from losses or changes thresholds.
"""
import hmac
import json
import math
import os
import threading
import time
from datetime import datetime, timezone
from types import MappingProxyType

from signals import decide, norm_cdf

PILOT_MAX = MappingProxyType(dict(
    stake_usd=1.0,          # cost incl. fees per trade
    contracts=1,            # contracts per trade
    open_positions=1,       # open positions in total (no ADD, no second market)
    trades_per_day=3,       # orders sent per UTC day (filled or not)
    daily_pause_usd=2.0,    # pause for the UTC day at -$2 realized
    hard_stop_usd=5.0,      # hard stop at -$5 cumulative (50% of a $10 bankroll)
))
ENABLE_PHRASE = "ENABLE LIVE TRADING WITH REAL MONEY"
RESET_PHRASE_1 = "I ACCEPT THAT THE HARD STOP TRIGGERED"
RESET_PHRASE_2 = "RESET THE HARD STOP AND RESUME THE PILOT"
STRONG = "STRONG BUY NOW"
FLIP_MAX_TOUCH = 0.25     # flip-risk gate: max chance spot touches the target before close (my judgment; untested)
RESET_STAGE_TTL = 300     # seconds the first reset confirmation stays valid
ASSETS_ALLOWED = ("BTC",)  # the only series whose fee/shard behaviour has been checked


class PilotError(Exception):
    pass


def utc_today():
    return datetime.now(timezone.utc).date().isoformat()


class Pilot:
    def __init__(self, path="pilot.json", today_fn=utc_today, now_fn=time.time):
        self.path, self.today_fn, self.now_fn = path, today_fn, now_fn
        self.lock = threading.RLock()
        self.limits = dict(PILOT_MAX)
        self.live_enabled = False          # never persisted: every restart starts with LIVE off
        self.day, self.trades_today, self.daily_pnl = today_fn(), 0, 0.0
        self.pnl_total, self.baseline = 0.0, 0.0
        self.hard_stopped, self.hard_stop_reason = False, ""
        self.reset_stage, self.reset_stage_at = 0, 0.0
        self._load()

    # ---- persistence (limits clamped to the code maximums on every load)
    def _load(self):
        try:
            d = json.load(open(self.path))
        except Exception:
            return
        for k, v in (d.get("limits") or {}).items():
            if k in PILOT_MAX and isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v >= 0:
                self.limits[k] = min(v, PILOT_MAX[k])
        self.pnl_total, self.baseline = float(d.get("pnl_total", 0.0)), float(d.get("baseline", 0.0))
        self.hard_stopped, self.hard_stop_reason = bool(d.get("hard_stopped")), d.get("hard_stop_reason", "")
        if d.get("day") == self.day:
            self.trades_today, self.daily_pnl = int(d.get("trades_today", 0)), float(d.get("daily_pnl", 0.0))

    def save(self):
        with self.lock:
            tmp = self.path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(dict(limits=self.limits, day=self.day, trades_today=self.trades_today, daily_pnl=self.daily_pnl,
                               pnl_total=self.pnl_total, baseline=self.baseline, hard_stopped=self.hard_stopped,
                               hard_stop_reason=self.hard_stop_reason), f)
            os.replace(tmp, self.path)

    def _roll(self):
        today = self.today_fn()
        if today != self.day:
            self.day, self.trades_today, self.daily_pnl = today, 0, 0.0

    # ---- limits: lower only
    def lower(self, name, value):
        with self.lock:
            if name not in PILOT_MAX:
                raise PilotError(f"unknown limit {name!r}")
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise PilotError("limit must be a number >= 0")
            if value > self.limits[name] + 1e-12:
                raise PilotError(f"{name} can only be LOWERED from the UI (now {self.limits[name]}, hard maximum {PILOT_MAX[name]})")
            self.limits[name] = int(value) if isinstance(PILOT_MAX[name], int) else float(value)
            self.save()
            return self.limits[name]

    # ---- breakers
    def daily_paused(self):
        with self.lock:
            self._roll()
            return self.daily_pnl <= -self.limits["daily_pause_usd"] + 1e-9

    def drawdown(self):
        return self.pnl_total - self.baseline

    def record_order_sent(self):
        with self.lock:
            self._roll()
            self.trades_today += 1
            self.save()

    def record_pnl(self, pnl):
        """Realized live P&L (after fees). Returns 'hard_stop' / 'daily_pause' / None when a breaker trips."""
        with self.lock:
            self._roll()
            before_paused = self.daily_pnl <= -self.limits["daily_pause_usd"] + 1e-9
            self.daily_pnl += pnl
            self.pnl_total += pnl
            event = None
            if self.drawdown() <= -self.limits["hard_stop_usd"] + 1e-9 and not self.hard_stopped:
                self.hard_stopped, self.live_enabled = True, False
                self.hard_stop_reason = f"cumulative live P&L {self.drawdown():+.2f} reached -{self.limits['hard_stop_usd']:.2f}"
                event = "hard_stop"
            elif not before_paused and self.daily_pnl <= -self.limits["daily_pause_usd"] + 1e-9:
                event = "daily_pause"
            self.save()
            return event

    def check_entry(self, cost, n_open, open_cost):
        """Pilot gate inside the order path. Returns (ok, reason)."""
        with self.lock:
            self._roll()
            L = self.limits
            if not self.live_enabled:
                return False, "LIVE is not enabled (type the phrase on the Trading tab)"
            if self.hard_stopped:
                return False, f"HARD STOP: {self.hard_stop_reason}"
            if self.daily_paused():
                return False, f"paused for the day (live P&L {self.daily_pnl:+.2f} <= -{L['daily_pause_usd']:.2f})"
            if self.trades_today >= L["trades_per_day"]:
                return False, f"max {L['trades_per_day']} trades per day reached"
            if n_open >= L["open_positions"]:
                return False, "a position is already open (one at a time, no adding)"
            if cost > L["stake_usd"] + 1e-9:
                return False, f"cost ${cost:.2f} exceeds pilot stake ${L['stake_usd']:.2f}"
            if self.daily_pnl - open_cost - cost < -L["daily_pause_usd"] - 1e-9:
                return False, "this trade could take the day past the daily pause"
            if self.drawdown() - open_cost - cost < -L["hard_stop_usd"] - 1e-9:
                return False, "this trade could take cumulative P&L past the hard stop"
            return True, "ok"

    # ---- typed confirmations
    def enable(self, phrase, ready_ok, reasons):
        with self.lock:
            if not hmac.compare_digest(str(phrase).encode(), ENABLE_PHRASE.encode()):
                raise PilotError("confirmation phrase does not match")
            if self.hard_stopped:
                raise PilotError("hard stop is active; reset it first")
            if not ready_ok:
                raise PilotError("not ready: " + "; ".join(reasons))
            self.live_enabled = True

    def disable(self):
        with self.lock:
            self.live_enabled = False

    def reset_hard_stop(self, phrase):
        """Two typed confirmations, in order. A wrong phrase restarts the sequence. Never enables LIVE."""
        with self.lock:
            if not self.hard_stopped:
                raise PilotError("no hard stop to reset")
            now = self.now_fn()
            if self.reset_stage == 1 and now - self.reset_stage_at > RESET_STAGE_TTL:
                self.reset_stage = 0
            want = RESET_PHRASE_1 if self.reset_stage == 0 else RESET_PHRASE_2
            if not hmac.compare_digest(str(phrase).encode(), want.encode()):
                self.reset_stage = 0
                raise PilotError("phrase does not match; the reset sequence restarted from step 1")
            if self.reset_stage == 0:
                self.reset_stage, self.reset_stage_at = 1, now
                return "step1_ok"
            self.hard_stopped, self.hard_stop_reason, self.reset_stage = False, "", 0
            self.baseline = self.pnl_total      # the -$5 is now measured from here
            self.live_enabled = False           # LIVE must be enabled again with its own phrase
            self.save()
            return "reset"

    def status(self):
        with self.lock:
            self._roll()
            return dict(live_enabled=self.live_enabled, limits=dict(self.limits), maximums=dict(PILOT_MAX),
                        trades_today=self.trades_today, daily_pnl=round(self.daily_pnl, 4), pnl_total=round(self.pnl_total, 4),
                        drawdown=round(self.drawdown(), 4), daily_paused=self.daily_paused(),
                        hard_stopped=self.hard_stopped, hard_stop_reason=self.hard_stop_reason, reset_stage=self.reset_stage)


# ------------------------------------------------------------------ signal grading
def evaluate_signal(ticker, sig, q, secs_left, momentum, fresh, fee_mult, hard_max, review_fn, now=None):
    """Grade a setup. STRONG BUY NOW only if EVERY check passes. Reuses the strictest existing
    rule set (conservative mode); the only new numbers are the flip-risk gates."""
    checks = []

    def add(name, ok, detail):
        checks.append(dict(name=name, ok=bool(ok), detail=detail))

    add("price data fresh", fresh, "ok" if fresh else "stale or missing")
    dec = decide(sig, q, secs_left, "conservative", fee_mult, hard_max) if (sig and fresh) else \
        dict(enter=False, side=None, price=None, edge=None, reason="no signal")
    add("conservative rules (edge>=0.10 after fees, ask<=0.75, 90-600s left, spread<=0.04)", dec["enter"], dec["reason"])
    add("edge after fees is positive", dec["edge"] is not None and dec["edge"] > 0,
        "n/a" if dec["edge"] is None else f"{dec['edge']:+.3f}")
    rv = review_fn(dec) if sig else dict(verdict="veto", lines=["no signal"])
    add("reasoning engine agrees (no veto)", rv["verdict"] == "ok", rv["lines"][0] if rv["lines"] else "")
    touch, adverse = None, None
    if sig:
        touch = 2 * (1 - norm_cdf(abs(sig["z"])))
        adverse = (dec["side"] == "yes" and momentum < 0) or (dec["side"] == "no" and momentum > 0)
    safe = sig is not None and touch <= FLIP_MAX_TOUCH and not adverse
    add("flip risk: SAFE TO ENTER", safe,
        "no signal" if not sig else f"chance spot touches target before close {touch:.0%} (max {FLIP_MAX_TOUCH:.0%}); "
                                    f"2-min momentum {'AGAINST' if adverse else 'not against'} the side")
    side_size = None if not dec["side"] else (q["yes_ask_size"] if dec["side"] == "yes" else q["no_ask_size"])
    add("depth for 1 contract at the ask", side_size is None or side_size >= 1, f"ask size {side_size}")
    strong = all(c["ok"] for c in checks)
    return dict(ticker=ticker, ts=now or time.time(), grade=STRONG if strong else "WAIT", checks=checks,
                side=dec["side"], price=dec["price"], edge=dec["edge"],
                flip=dict(touch_prob=touch, safe=safe, label="SAFE TO ENTER" if safe else "NOT SAFE"),
                failed=[c["name"] for c in checks if not c["ok"]])
