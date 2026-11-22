"""Gate 1: live orders are impossible unless config trading=live AND --live."""
import json
import threading

import pytest

import bot
import engine
from kalshi_client import Kalshi, KalshiError
from tests.helpers import mkmarket, mkround
from tests.net import KEY, Script, good_handler

T = "KXBTC15M-T1"


class DummySrv:
    def serve_forever(self): pass
    def shutdown(self): pass


@pytest.mark.parametrize("trading,flag,expect_live", [
    ("paper", False, False), ("paper", True, False), ("live", False, False), ("live", True, True)])
def test_every_combination_places_orders_only_when_both_set(tmp_path, monkeypatch, trading, flag, expect_live):
    monkeypatch.chdir(tmp_path)
    cfg = tmp_path / "c.json"
    cfg.write_text(json.dumps({"trading": trading}))
    sess = Script(good_handler(mkmarket(T, .78, .80)))
    client = Kalshi("CANARY", KEY, session=sess, sleep=lambda s: None)
    monkeypatch.setattr(bot.Kalshi, "from_env", classmethod(lambda cls: client))
    monkeypatch.setattr(bot.board, "serve", lambda *a, **k: DummySrv())
    seen = {}

    def fake_loop(ctx, stop, deadline=None):
        seen["live"], seen["allow"] = ctx.live, ctx.client.allow_orders
        ctx.st.armed = True                      # worst case: armed and eager
        mkround(ctx.st, T)
        engine.enter(ctx.client, ctx.st, ctx.live, T, "yes", 0.80, 500, 1.0, "gate test")
        for live_arg in (False, True):           # a buggy caller passing the wrong flag must still be stopped
            try:
                ctx.client.place_order(T, "yes", "buy", 1, 0.8)
            except KalshiError:
                pass
        stop.set()

    monkeypatch.setattr(bot, "run_loop", fake_loop)
    argv = ["--config", str(cfg)] + (["--live"] if flag else [])
    bot.main(argv)
    assert seen["live"] is expect_live and seen["allow"] is expect_live
    n_posts = len(sess.posts())
    if expect_live:
        assert n_posts == 3          # enter() + two direct place_order calls
    else:
        assert n_posts == 0, "an order reached the network without trading=live AND --live"


def test_arm_flag_refused_in_live_mode(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = tmp_path / "c.json"
    cfg.write_text(json.dumps({"trading": "live"}))
    with pytest.raises(SystemExit):
        bot.main(["--config", str(cfg), "--live", "--arm"])


def test_default_config_is_paper_and_client_refuses_orders_by_default():
    import json as j
    assert j.load(open("config.json"))["trading"] == "paper"
    with pytest.raises(KalshiError):
        Kalshi("k", KEY, session=Script(good_handler({}))).place_order(T, "yes", "buy", 1, 0.5)


def test_board_default_host_is_loopback(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = tmp_path / "c.json"
    cfg.write_text("{}")
    client = Kalshi("k", KEY, session=Script(good_handler(mkmarket(T, .5, .6))))
    monkeypatch.setattr(bot.Kalshi, "from_env", classmethod(lambda cls: client))
    got = {}
    monkeypatch.setattr(bot.board, "serve", lambda c, st, live, host, port, fm=1.0: got.setdefault("host", host) and DummySrv())
    monkeypatch.setattr(bot, "run_loop", lambda ctx, stop, deadline=None: stop.set())
    bot.main(["--config", str(cfg)])
    assert got["host"] == "127.0.0.1"
