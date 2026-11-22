import pytest

import backtest as bt
from engine import TRADE_COLUMNS


def row(price, count, fee, won, result=None, cashed="0", p_model="0.9", p_market="0.8", edge="0.1"):
    pnl = (count if won else 0) - price * count - fee
    return dict(action="ENTER", count=str(count), entry_price=str(price), entry_fee=str(fee), pnl=str(pnl),
                fees=str(fee), won="1" if pnl > 0 else "0", result=result or ("yes" if won else "no"),
                cashed_out=cashed, p_model=p_model, p_market=p_market, edge=edge)


def test_binomial_and_drawdown():
    assert bt.binom_p_ge(5, 5) == pytest.approx(1 / 32)
    assert bt.binom_p_ge(0, 7) == pytest.approx(1.0)
    assert bt.max_drawdown([1, -2, -1, 4, -1]) == 3 and bt.max_drawdown([1, 2]) == 0


def test_analyse_known_numbers():
    rows = [row(0.5, 10, 0.2, True), row(0.5, 10, 0.2, False), row(0.5, 10, 0.2, True)]
    rows.append(dict(action="SKIP", result="no", pnl="0", fees="0", p_model="0.4", p_market="0.45"))
    m = bt.analyse(rows)
    assert (m["rounds"], m["traded"], m["skipped"], m["wins"]) == (4, 3, 1, 2)
    assert m["fees"] == pytest.approx(0.6)
    assert m["net_pnl"] == pytest.approx(2 * (10 - 5 - 0.2) + (-5 - 0.2))
    assert m["gross_pnl"] == pytest.approx(m["net_pnl"] + 0.6)
    assert m["avg_breakeven"] == pytest.approx(0.52) and m["realized_edge"] == pytest.approx(2 / 3 - 0.52)
    assert m["max_drawdown"] == pytest.approx(5.2)
    assert "INCONCLUSIVE" in m["verdict"]  # n < 30 must never claim an edge


def test_verdict_no_edge_when_fair_prices():
    # win exactly at the price paid: 60 trades at 0.5, half win -> fees make it a loser
    rows = [row(0.5, 10, 0.18, i % 2 == 0) for i in range(60)]
    m = bt.analyse(rows)
    assert m["net_pnl"] < 0 and m["verdict"].startswith("NO DEMONSTRATED EDGE")


def test_verdict_edge_when_clearly_winning():
    rows = [row(0.5, 10, 0.18, i % 10 != 0) for i in range(100)]  # 90% wins at 0.5
    m = bt.analyse(rows)
    assert m["p_vs_price"] < 0.001 and m["p_vs_coinflip"] < 0.001 and m["verdict"].startswith("EDGE")


def test_cashouts_excluded_from_price_tests_but_counted_in_pnl():
    rows = [row(0.5, 10, 0.2, True), row(0.5, 10, 0.2, False, cashed="1")]
    m = bt.analyse(rows)
    assert m["traded"] == 2 and m["held"] == 1 and m["cashed_out"] == 1


def test_brier_compares_model_to_market():
    rows = [dict(action="SKIP", result="yes", pnl="0", fees="0", p_model="0.9", p_market="0.6"),
            dict(action="SKIP", result="no", pnl="0", fees="0", p_model="0.2", p_market="0.5")]
    m = bt.analyse(rows)
    assert m["brier_model"] < m["brier_market"] and m["calib_n"] == 2
    assert "Brier" in bt.format_report(m)


def test_empty_input_does_not_crash():
    assert "INCONCLUSIVE" in bt.format_report(bt.analyse([]))


def test_roundtrip_csv_columns_and_replay(tmp_path):
    snaps = [dict(time="2026-01-01T00:00:0%d" % i, ticker="T1", secs_left=str(300 - i), p_up=pu,
                  yes_bid="0.78", yes_ask="0.80", no_bid="0.20", no_ask="0.22")
             for i, pu in enumerate(["0.82", "0.95"])]
    outcomes = [dict(ticker="T1", result="yes", action="SKIP")]
    out = bt.replay(outcomes, snaps, "balanced", 5.0)
    assert out[0]["action"] == "ENTER" and float(out[0]["pnl"]) == pytest.approx(6 - 4.8 - 0.07)  # 2nd snapshot qualifies
    out2 = bt.replay(outcomes, snaps, "conservative", 5.0, min_edge=0.5)
    assert out2[0]["action"] == "SKIP"
    from signals import MODES
    assert "_replay" not in MODES  # replay must not leak overrides


def test_bootstrap_ci_brackets_mean_and_is_deterministic():
    xs = [1.0, -1.0, 2.0, -0.5, 0.5, 1.5, -2.0, 0.0]
    lo, hi = bt.bootstrap_mean_ci(xs)
    assert lo < sum(xs) / len(xs) < hi and bt.bootstrap_mean_ci(xs) == (lo, hi)
    assert bt.bootstrap_mean_ci([1.0]) is None
    m = bt.analyse([row(0.5, 10, 0.2, True), row(0.5, 10, 0.2, False)])
    assert m["pnl_per_trade_ci95"] and "bootstrap" in bt.format_report(m)


def test_halves_flag_runs(tmp_path, capsys):
    import csv
    snaps = tmp_path / "s.csv"
    trades = tmp_path / "t.csv"
    with open(snaps, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["time", "ticker", "secs_left", "p_up", "yes_bid", "yes_ask", "no_bid", "no_ask"])
        w.writeheader()
        for i in range(4):
            w.writerow(dict(time=f"{i:03d}", ticker=f"T{i}", secs_left=300, p_up=0.95, yes_bid=.78, yes_ask=.8, no_bid=.2, no_ask=.22))
    with open(trades, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["ticker", "action", "result"])
        w.writeheader()
        for i in range(4):
            w.writerow(dict(ticker=f"T{i}", action="SKIP", result="yes"))
    bt.main(["--trades", str(trades), "--snapshots", str(snaps), "--replay", "--halves"])
    out = capsys.readouterr().out
    assert "FIRST HALF" in out and "SECOND HALF" in out
