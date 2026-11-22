import json

import pytest

import backtest as bt
import gate3


def test_tick_grid_and_pessimistic_slippage_lowers_pnl():
    assert bt.tick_at(0.5) == 0.01 and bt.tick_at(0.95) == 0.001 and bt.tick_at(0.05) == 0.001
    snaps = [dict(time="1", ticker="T1", secs_left="300", p_up="0.95", yes_bid="0.78", yes_ask="0.80", no_bid="0.20", no_ask="0.22")]
    out = [dict(ticker="T1", action="SKIP", result="yes")]
    base = bt.replay(out, snaps, "balanced", 5.0)[0]
    slip = bt.replay(out, snaps, "balanced", 5.0, slip_ticks=1)[0]
    assert float(slip["entry_price"]) == pytest.approx(0.81) and float(slip["pnl"]) < float(base["pnl"])


def test_slippage_past_mode_max_price_skips_trade():
    snaps = [dict(time="1", ticker="T1", secs_left="300", p_up="0.99", yes_bid="0.84", yes_ask="0.85", no_bid="0.15", no_ask="0.16")]
    out = [dict(ticker="T1", action="SKIP", result="yes")]
    assert bt.replay(out, snaps, "balanced", 5.0)[0]["action"] == "ENTER"
    assert bt.replay(out, snaps, "balanced", 5.0, slip_ticks=1)[0]["action"] == "SKIP"   # 0.86 > 0.85


def row(t, price, n, fee, pnl, ticker="T"):
    return dict(time=t, ticker=ticker, action="ENTER", count=str(n), entry_price=str(price), entry_fee=str(fee), pnl=str(pnl))


CFG = dict(size_per_trade_usd=5, hard_max_price=0.95, daily_loss_cap_usd=15, max_losses_in_row=3)


def test_violation_detector_catches_each_breach():
    assert gate3.violations([row("2026-01-01T00:00:01", .5, 9, .2, -4.7)], CFG) == []
    assert any("size cap" in v for v in gate3.violations([row("2026-01-01T00:00:01", .5, 12, .2, 1)], CFG))
    assert any("hard max" in v for v in gate3.violations([row("2026-01-01T00:00:01", .96, 1, .0, 1)], CFG))
    losses = [row(f"2026-01-01T00:0{i}:00", .5, 2, .1, -1.1, f"T{i}") for i in range(4)]
    assert any("losses in a row" in v for v in gate3.violations(losses, CFG))
    big = [row("2026-01-01T00:00:00", .5, 9, .2, -15.0), row("2026-01-01T00:01:00", .5, 2, .1, 1.0)]
    assert any("daily loss cap" in v for v in gate3.violations(big, CFG))
    assert gate3.violations([row("2026-01-02T00:00:00", .5, 2, .1, 1)], CFG) == []   # next day: cap reset


def test_history_source_can_never_pass(tmp_path, capsys):
    import csv
    t, s = tmp_path / "t.csv", tmp_path / "s.csv"
    with open(s, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["time", "ticker", "secs_left", "p_up", "yes_bid", "yes_ask", "no_bid", "no_ask"])
        w.writeheader()
        for i in range(6):
            w.writerow(dict(time=f"{i:012d}", ticker=f"T{i}", secs_left=300, p_up=.95, yes_bid=.78, yes_ask=.8, no_bid=.2, no_ask=.22))
    with open(t, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["ticker", "action", "result"])
        w.writeheader()
        for i in range(6):
            w.writerow(dict(ticker=f"T{i}", action="SKIP", result="yes"))
    rc = gate3.main(["--source", "history", "--trades", str(t), "--snapshots", str(s)])
    out = capsys.readouterr().out
    assert rc == 1 and "[FAIL] Source is real paper trading" in out and "GATE 3: FAIL" in out and ">= 300 trades" in out


def test_demo_harness_refuses_production(monkeypatch):
    import demo_check
    for url in ("", "https://api.elections.kalshi.com/trade-api/v2", "https://external-api.kalshi.com/trade-api/v2",
                "https://evil.com/demo.kalshi.co"):
        monkeypatch.setenv("KALSHI_BASE_URL", url)
        with pytest.raises(SystemExit) as e:
            demo_check.main()
        assert "REFUSING" in str(e.value)
