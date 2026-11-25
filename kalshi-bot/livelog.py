"""Append-only ledger of every live order, fill check, settlement and control action, plus real P&L."""
import json
import threading
import time
from datetime import datetime, timezone

_REDACT = ("key", "secret", "signature", "token", "password", "pem")


def _clean(v):
    if isinstance(v, dict):
        return {k: ("[redacted]" if any(w in k.lower() for w in _REDACT) and k != "api_key_fingerprint" else _clean(x))
                for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    return v


class Ledger:
    def __init__(self, path="live_ledger.jsonl", pm_path="postmortems.jsonl"):
        self.path, self.pm_path, self.lock = path, pm_path, threading.Lock()

    def _append(self, path, rec):
        with self.lock, open(path, "a") as f:
            f.write(json.dumps(rec, default=str) + "\n")

    def log(self, event, **fields):
        rec = dict(ts=datetime.now(timezone.utc).isoformat(), event=event, **_clean(fields))
        self._append(self.path, rec)
        return rec

    def postmortem(self, pm):
        self._append(self.pm_path, pm)

    @staticmethod
    def _read(path, limit=None):
        try:
            rows = [json.loads(l) for l in open(path) if l.strip()]
        except FileNotFoundError:
            return []
        return rows[-limit:] if limit else rows

    def events(self, limit=300):
        return self._read(self.path, limit)

    def postmortems(self, limit=50):
        return self._read(self.pm_path, limit)

    def summary(self, today=None):
        """Real P&L from closed trades only (after entry+exit fees)."""
        today = today or datetime.now(timezone.utc).date().isoformat()
        evs = self._read(self.path)
        closed = [e for e in evs if e["event"] == "trade_closed"]
        ok_settled = {e["ticker"] for e in evs if e["event"] == "settlement_verified"}
        for e in closed:
            e["verified"] = bool(e.get("verified")) or e["ticker"] in ok_settled
        tot = sum(e["pnl_net"] for e in closed)
        day = sum(e["pnl_net"] for e in closed if e["ts"][:10] == today)
        return dict(trades=len(closed), wins=sum(1 for e in closed if e["pnl_net"] > 0),
                    pnl_net_total=round(tot, 4), pnl_net_today=round(day, 4),
                    fees_total=round(sum(e.get("fees", 0.0) for e in closed), 4),
                    unverified=sum(1 for e in closed if not e.get("verified")))
