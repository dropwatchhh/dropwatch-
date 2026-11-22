# READINESS: Kalshi 15-minute bot

**Final verdict: NO-GO.** Default answer is NO-GO until every gate passes; Gates 2 and 3 have not passed
(2 is blocked, 3 fails), and Gate 4 was not started. No real orders were placed at any point in this review.
No strategy parameter was changed to improve any number (the defaults in `config.json` are the ones that were
set before any data was looked at).

Reviewed: 2026-11-22, branch `claude/kalshi-crypto-bot-y1dmpx`.

| Gate | Result |
|---|---|
| 1. Code safety audit | **8 PASS, 1 FAIL** (fee coefficient unverified) |
| 2. Kalshi demo environment | **BLOCKED** (needs demo credentials only the account holder can create; harness written, not run) |
| 3. Paper trading, 14 days, 300 trades | **FAIL** (not run for 14 days; replay evidence is negative anyway) |
| 4. Live canary | **NOT STARTED** (requires Gates 1-3 to pass and your written approval) |

---

## Gate 1: Code safety audit

Reproduce everything with `cd kalshi-bot && python -m pytest` (153 tests, all network mocked, no real key needed).

| # | Item | Result | Evidence |
|---|---|---|---|
| 1.1 | Live orders impossible unless `trading: "live"` AND `--live` | **PASS** | `tests/test_gate_live_gating.py` drives `bot.main()` with the **real** `Kalshi` client and a recording HTTP layer, in all four config/flag combinations, with the loop forced to be armed and to call `enter()` plus direct `place_order()`. Orders reaching the network: paper/no-flag 0, paper/`--live` 0, live/no-flag 0, live/`--live` 3 (the intended ones). Defence in depth: the client itself refuses `place_order` unless `allow_orders` is set (only `bot.main` sets it, only when live); `--arm` is refused in live mode. |
| 1.2 | Every risk limit enforced **inside the order path** | **PASS** | `State.check_entry()` is called by `enter()` itself, so the loop, board and tests cannot bypass it. It enforces armed, kill-switch file, halted state, one position per round, price ≤ min(hard max, mode max), cost incl. fees ≤ size, daily loss cap (also counting open exposure + new cost), losing-streak stop. Tests: `test_engine.py` (each limit through `enter()`), `test_gate_coverage.py` (each limit by calling `check_entry` directly). Found and fixed during this review: the mode's max price was only checked in the decision step, not the order path. Added a second independent cap inside `Kalshi.place_order` (refuses buys without configured limits, and any buy over `size_per_trade_usd` or `hard_max_price`). |
| 1.3 | Fees included in all sizing and PnL, matching the current schedule | **FAIL (unverified)** | Fees are in sizing (`max_affordable_count`), entry, cash-out and settlement PnL, and in every backtest. Confirmed from Kalshi's docs/API: the series is `fee_type: quadratic`, `fee_multiplier: 1` (the bot reads it at startup), and the rounding rules. **The `0.07` coefficient is not stated anywhere in Kalshi's API docs that I could read**, and I could not reach the published fee-schedule document. It is from my knowledge, so I cannot call it verified. It is checked automatically by `demo_check.py` (compares the model to the API's `fee_cost`), which has not been run. |
| 1.4 | Fail closed: network dead, garbage JSON, stale prices, missing bid/ask, 429/5xx | **PASS** | `tests/test_gate_fail_closed.py`, 13 scenarios x the full armed live loop: network down, unparseable JSON, wrong-shape JSON, missing fields, 429, 500, 503, 401, no quotes, missing ask side, zero ask, null target, price >5 s old. Each: **0 order POSTs, no position, no exception escapes**. A control scenario proves the same setup *does* trade when healthy, so "no order" is meaningful. Fixed during review: an unparseable 2xx response to an order is now treated as "outcome unknown" (it previously would have raised a non-Kalshi error). Order calls that time out, 5xx, or return garbage send exactly **one** POST (never retried), then **halt and disarm**. |
| 1.5 | Kill switch `python kill.py` | **PASS (against mocks)** | New `kill.py`: writes a `KILL` file (the order path refuses every entry while it exists, even if the board is unreachable), disarms the running board, cancels all resting orders (`DELETE /portfolio/events/orders`), and with `--flatten` sells open positions at the bid (reduce-only, IOC). Failures are loud and exit non-zero (cancel failure, no bid). `--clear` re-allows arming. 10 tests in `test_gate_kill_restart.py` (kill switch and restart). **Not exercised against a real or demo account** (Gate 2). |
| 1.6 | Restart safety | **PASS (process-level, mocks)** | A subprocess is hard-killed (`os._exit(9)`, no cleanup) *inside* the order call; on restart the round is already marked attempted (state is now written **before** a live order is sent), a second order is refused, and `reconcile()` adopts the position from Kalshi's positions. Also tested: paper restart keeps position and does not re-enter; an unfilled IOC leaves no phantom position. Unverified against the real API: the reconcile code assumes `position_fp` is positive for YES and negative for NO. |
| 1.7 | Secrets audit | **PASS (with a stated limit)** | New `audit_secrets.py`. Tree + full git history of the committed branch: nothing found. Current `state.json`, `trades.csv`, `snapshots.csv`, `paper_run.log`: nothing found. `tests/test_gate_secrets.py` uses a **canary** key id and a generated RSA key, runs signing, every error type, a full paper round, state/CSV writes and the board, then scans every artifact and response: nothing leaks. The auditor is proven non-vacuous (it detects a planted key id, a PEM line and a PEM header). Limit: no real Kalshi key exists in this environment, so real key material could not be scanned for. Re-run `python audit_secrets.py . --git` with your real env vars set before going live. |
| 1.8 | Board security | **PASS** | Binds `127.0.0.1` by default (tested); non-loopback bind refuses to start without a `BOARD_TOKEN` of ≥16 chars; with a token set, status/arm/mode/cash-out all return 401 without it (token in header only, query-string tokens rejected, constant-time compare); cross-site POSTs rejected (custom header required, 403 observed on the live board); spoofed `Host` header rejected (DNS-rebinding). Note: with no token on loopback, `GET /api/status` is readable by local processes (it is read-only; arm/cash-out need the custom header). `tests/test_board.py`. |
| 1.9 | pytest + coverage on risk, settlement, cash-out | **PASS** | 153 passed. Coverage (`pytest --cov`): engine 96% (state/risk/enter/cash-out/settle/reconcile), kill 96%, signals 96%, kalshi_client 91%, board 91%, bot 84%, backtest 95%, total 92%. The uncovered engine lines are config-validation messages and error-logging branches. |

Known gaps in Gate 1 (not hidden by the PASSes above): there is **no automated stop-loss**; the strategy holds to
settlement and the only early exit is the manual one-tap cash-out (or `kill.py --flatten`). Exits use the bid at the
time of the call, with no slippage guard beyond IOC.

---

## Gate 2: Kalshi demo environment: BLOCKED

A demo environment **exists** (`https://external-api.demo.kalshi.co/trade-api/v2`, mock funds; credentials are
separate from production and must be created by you: <https://docs.kalshi.com/getting_started/demo_env.md>).
I have no demo credentials, so none of the order tests could be run.

What I could verify without credentials: the real client, pointed at the demo host, reads the demo's public market
data correctly (`KXBTC15M` open market, strike, bid/ask parsed), signs against the `/trade-api/v2` prefix, refuses
orders and authenticated calls with no credentials and no live flag.

| Item | Result |
|---|---|
| Place, partially fill, cancel, settle; logged fills/fees match the API (V2 fill-price fields) | **BLOCKED** |
| Stop-loss and cash-out incl. thin book | **BLOCKED** (and no automated stop-loss exists) |
| Insufficient balance; market closing mid-order | **BLOCKED** |

To unblock: create demo credentials, then run `python demo_check.py` (exports in its docstring). It refuses to run
unless `KALSHI_BASE_URL` is a `demo.kalshi.co` host (tested). It automates the fill-vs-fills-endpoint comparison
(price, count, **fee, which also settles item 1.3**), cash-out and reduce-only over-sell, cancel-all, and
insufficient balance. Partial fills on a thin book, an order in the final seconds, and settlement PnL still need to be
done by hand and recorded. Its resting-order step and `GET /portfolio/orders?status=resting` field names are
from the docs and untested.

---

## Gate 3: Paper trading: FAIL

The gate requires 14 continuous days of real paper trading. This session is an ephemeral container and cannot
provide that, so the gate **fails by default**. As a substitute I built a 14.2-day replay (1,350 settled BTC rounds,
8 to 22 Nov 2026, using only information available at each decision time) and scored it with `gate3.py`, with
**pessimistic fills (ask + 1 tick)**. A replay is evidence, not paper trading (end-of-minute quotes, fills at the
ask assumed), so even a pass here could not pass the gate.

Scorecard, default mode `balanced` (`python gate3.py --source history --trades hist14_trades.csv --snapshots hist14_snaps.csv`):

| Criterion | Result | Value |
|---|---|---|
| Real paper trading, not a replay | FAIL | replay |
| Duration ≥ 14 days | PASS | 14.2 days |
| ≥ 300 trades | **FAIL** | 112 |
| No crashes / risk violations in logs | FAIL | not checkable on a replay |
| Net PnL > 0 after fees + 1-tick slippage | PASS | +$26.96 |
| Bootstrap 95% CI of PnL/trade lower bound > 0 | **FAIL** | [−0.449, +0.948] (includes zero) |
| Brier better than market mid | **FAIL** | model 0.1248 vs market 0.1208 |
| Brier better in 2nd half | **FAIL** | 0.1313 vs 0.1293 |
| Both halves profitable | **FAIL** | first 7 days −$2.61 / last 7 days +$29.57 |
| Max drawdown < 3 x daily cap ($45) | PASS | $26.90 |

Other modes: `conservative` 35 trades, +$15.88, CI [−0.85, +1.76]; `aggressive` 257 trades, **−$39.57**, drawdown
$87.47. In all three modes the model is a worse probability forecaster than the market's own mid price.

What the numbers say in plain terms: in the first 7 days, balanced won 62.5% of trades at a 62.4% breakeven, which
is exactly no edge; the second week's profit is not statistically distinguishable from luck (p = 0.20), and the
earlier 10-day, mid-fill result that looked positive (+$36.74) shrinks to +$26.96 with a one-tick penalty and a
longer window. **The strategy has no demonstrated edge.**

Live paper smoke run (current code, real data, started 14:23 UTC, still running when this was written at 14:44):
0 errors/tracebacks/halts in the log, 1 round recorded, 0 trades. This is a stability sample only, not a
statistical one. Earlier runs in this session were restarted deliberately by me after code fixes, not by crashes
(0 crashes observed).

---

## Gate 4: Live canary: NOT STARTED

Prerequisites not met (Gates 2 and 3), and there is no written approval from you. Nothing was run with real money.

---

## Verdict (plain words)

**Do not trade real money with this bot yet.** The software side is in good shape: it cannot place a live order
unless you set both switches, it refuses to trade on bad or stale data, it survives being killed mid-order without
doubling up, it has a working kill switch, and it leaks no secrets. That part of the review is done, apart from one
unverified fee number. But the strategy itself has not shown it can beat Kalshi's prices after fees: over two
weeks of history its probability estimates were worse than the market's, one half of the period was flat, and the
most aggressive setting lost money. Two gates cannot even be attempted yet: the demo-environment tests need demo
credentials only you can create, and a real 14-day, 300-trade paper run has not been done. The honest conclusion
today is that this is a well-built bot with no demonstrated edge.

**To move toward GO:** (1) create demo credentials and run `demo_check.py` (this also settles the fee
coefficient); (2) run `python bot.py --arm` in paper mode continuously for 14+ days and score it with
`python gate3.py --source paper --trades trades.csv --log <logfile>`; (3) if the strategy still has no edge, which
is the likely outcome, do not go live. I'll stop here and wait for you.
