"""Separate credential paths for PRODUCTION ("live") and DEMO. They are never mixed.

  live:  KALSHI_LIVE_API_KEY_ID  + KALSHI_LIVE_PRIVATE_KEY_PATH   (e.g. a Render Secret File: /etc/secrets/kalshi_live.pem)
  demo:  KALSHI_DEMO_API_KEY_ID  + KALSHI_DEMO_PRIVATE_KEY_PATH

Rules, enforced here:
  * Each environment has a FIXED base URL. KALSHI_BASE_URL is ignored.
  * Loading one environment while the other's variables exist in the same process is refused: run the
    demo test order in its own process (`python preflight.py demo`) with only the DEMO variables set.
  * The old shared names (KALSHI_API_KEY_ID / KALSHI_PRIVATE_KEY_PATH) are refused as ambiguous.
  * The same key id or the same key file for both environments is refused.
Key material is only ever used to sign; error messages name variables, never values.
"""
import hashlib
import os

from cryptography.hazmat.primitives import serialization

from kalshi_client import Kalshi

PROD_BASE = "https://api.elections.kalshi.com/trade-api/v2"
DEMO_BASE = "https://external-api.demo.kalshi.co/trade-api/v2"
ENVS = {
    "live": dict(id="KALSHI_LIVE_API_KEY_ID", path="KALSHI_LIVE_PRIVATE_KEY_PATH", base=PROD_BASE),
    "demo": dict(id="KALSHI_DEMO_API_KEY_ID", path="KALSHI_DEMO_PRIVATE_KEY_PATH", base=DEMO_BASE),
}
LEGACY = ("KALSHI_API_KEY_ID", "KALSHI_PRIVATE_KEY_PATH")


class CredentialError(Exception):
    pass


def fingerprint(key):
    """Public-key fingerprint: safe to log/compare (proves live and demo keys differ)."""
    der = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    return hashlib.sha256(der).hexdigest()[:16]


def public_client(env="live"):
    """Unauthenticated client (market data only). Reads no credentials at all."""
    c = Kalshi(base=ENVS[env]["base"])
    c.env = env
    return c


def load(env, environ=None):
    """Authenticated client for exactly one environment."""
    if env not in ENVS:
        raise CredentialError(f"unknown environment {env!r}")
    e = os.environ if environ is None else environ
    spec, other = ENVS[env], ENVS["demo" if env == "live" else "live"]
    legacy = [v for v in LEGACY if e.get(v)]
    if legacy:
        raise CredentialError(f"{', '.join(legacy)} is ambiguous and no longer supported; use "
                              f"{spec['id']} / {spec['path']} for {env}")
    foreign = [v for v in (other["id"], other["path"]) if e.get(v)]
    if foreign:
        raise CredentialError(f"refusing to load {env} credentials while {', '.join(foreign)} is set in the same "
                              f"process: demo and live credentials must never be mixed (use separate processes)")
    kid, path = e.get(spec["id"], ""), e.get(spec["path"], "")
    if not kid or not path:
        raise CredentialError(f"{env} credentials missing: set {spec['id']} and {spec['path']}")
    try:
        with open(path, "rb") as f:
            key = serialization.load_pem_private_key(f.read(), password=None)
    except Exception as ex:
        raise CredentialError(f"cannot read the private key named by {spec['path']} ({type(ex).__name__})") from None
    c = Kalshi(kid, key, base=spec["base"])
    c.env, c.fingerprint = env, fingerprint(key)
    return c


def assert_distinct(live_client, demo_fingerprint):
    """The demo test order must have been made with a DIFFERENT key than the live one."""
    if demo_fingerprint and live_client.fingerprint == demo_fingerprint:
        raise CredentialError("live and demo are using the same key; use two separate Kalshi API keys")
