"""Gate 1: no key material in code, logs, state, CSVs, board responses or error text."""
import base64
import json
import os
import threading
from http.server import ThreadingHTTPServer

import pytest
import requests
from cryptography.hazmat.primitives import serialization

import audit_secrets
import board
from engine import Ctx, State, DEFAULTS, enter, run_loop, finalize_round
from kalshi_client import Kalshi, KalshiError
from tests.helpers import FakeClient, mkmarket, mkround
from tests.net import Resp, Script, good_handler
from tests.test_gate_fail_closed import OneShot, TickFeed

T = "KXBTC15M-T1"
CANARY_ID = "CANARY-KEY-ID-7f3a9c21"


@pytest.fixture
def secrets_env(tmp_path, monkeypatch):
    from cryptography.hazmat.primitives.asymmetric import rsa
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    (tmp_path / "k.pem").write_bytes(pem)
    monkeypatch.setenv("KALSHI_API_KEY_ID", CANARY_ID)
    monkeypatch.setenv("KALSHI_PRIVATE_KEY_PATH", str(tmp_path / "k.pem"))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_auditor_is_not_vacuous(tmp_path, secrets_env):
    (secrets_env / "leak.txt").write_text(f"oops {CANARY_ID}\n")
    (secrets_env / "leak2.txt").write_text((secrets_env / "k.pem").read_text().splitlines()[1] + "\n")
    (secrets_env / "leak3.txt").write_text("-----BEGIN " + "PRIVATE KEY-----\nabc\n")
    hits = audit_secrets.scan_paths([str(secrets_env / n) for n in ("leak.txt", "leak2.txt", "leak3.txt")], audit_secrets.env_secrets())
    kinds = {k.split("-")[0] for _, _, k in hits}
    assert len(hits) >= 3 and "api" in kinds and "pem" in kinds and "PEM private key block" in {k for _, _, k in hits}


def test_full_exercise_leaks_nothing(secrets_env):
    """Run signing, errors, trading, settlement, state/CSV writing and board; scan everything."""
    out = secrets_env / "artifacts"
    out.mkdir()
    client = Kalshi.from_env()
    assert client.key and client.key_id == CANARY_ID
    texts = [repr(client), str(client.__dict__.keys())]
    # errors of every flavour: their messages must not contain headers/keys
    for h in (lambda m, u: Resp(401, {"error": {"code": "bad_signature", "message": "invalid"}}),
              lambda m, u: (_ for _ in ()).throw(requests.ConnectionError("boom")),
              lambda m, u: Resp(500), lambda m, u: Resp(200, garbage=True)):
        client.s, client.sleep, client.max_retries = Script(h), (lambda s: None), 1
        try:
            client.balance_usd()
        except KalshiError as e:
            texts.append(str(e))
    # full paper round + persistence + board
    st = State(dict(DEFAULTS), path=str(out / "state.json"), trades_path=str(out / "trades.csv"),
               snaps_path=str(out / "snaps.csv"), kill_path=str(out / "NOKILL"))
    st.armed = True
    client.s = Script(good_handler(mkmarket(T, .78, .80, strike=99000.0)))
    client.allow_orders = False
    run_loop(Ctx(client, st, {"BTC": TickFeed()}, live=False), OneShot())
    finalize_round(st, st.rounds[T], "yes")
    s = ThreadingHTTPServer(("127.0.0.1", 0), board.make_handler(client, st, False))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{s.server_port}"
        texts += [requests.get(base + "/").text, requests.get(base + "/api/status").text]
    finally:
        s.shutdown()
    (out / "responses.txt").write_text("\n".join(texts))
    (out / "log.txt").write_text("\n".join(st.log))
    assert (out / "trades.csv").exists() and (out / "state.json").exists()
    hits = audit_secrets.scan_paths([str(out)], audit_secrets.env_secrets())
    assert hits == [], hits


def test_source_tree_has_no_key_material():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hits = [h for h in audit_secrets.scan_paths([here], {}) ]
    assert hits == [], hits


def test_gitignore_covers_secret_and_runtime_files():
    gi = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".gitignore")).read().split()
    for must in ("*.pem", ".env", "state.json", "trades.csv"):
        assert must in gi
