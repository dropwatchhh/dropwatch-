# Kalshi 15-minute crypto bot (self-hosted, paper by default)

Trades Kalshi's 15-minute crypto up/down rounds (`KXBTC15M`; `KXETH15M` / `KXSOL15M` optional)
from **your** machine with **your** API key, and serves a small local board you can open on a phone.
It is modelled on the feature list of NeuroBot's public page, but the strategy is original and
**has not been shown to make money**. Read `RESULTS.md` before risking anything.

> Trading involves risk of loss. This is software, not advice. Use a small, dedicated balance.

## What it does

| Feature | Where |
|---|---|
| Watches each 15-min round 24/7, skips rounds with no clear setup | `engine.process_asset`, `signals.decide` |
| Limits: size per trade, daily loss cap (UTC day), stop after N losses in a row | `engine.State.check_entry` (enforced in code, inside `enter()`) |
| Arm / disarm slider | board |
| Live round card, trade screen, one-tap **Cash out**, today's PnL, last 50 log lines | board |
| "Terminal": momentum, volatility, distance to target (in sigmas), 10-min hi/lo, most likely side | board + `signals.analyze` |
| Second engine: model vs market-implied probability, hourly-BTC-ladder implied vol, plain-English reasoning, veto | `signals.review`, `signals.ladder_implied_vol` |
| Modes: conservative / balanced / aggressive (switchable on the board) | `signals.MODES` |
| Every round (traded **or skipped**) recorded with features, decision, outcome, fees | `trades.csv`, `snapshots.csv` |
| Backtest + significance tests; large historical test from public data | `backtest.py`, `history.py` |

## Setup

```bash
cd kalshi-bot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest                      # 96 tests, all network mocked
```

### Create a Kalshi API key (needed only for live trading)

1. Log in at kalshi.com → **Account & security → API keys → Create key**.
2. Kalshi shows the private key **once**. Save it as `kalshi_key.pem` outside any git repo
   (`chmod 600`). Note the **Key ID**.
3. **Fund a small, dedicated balance** (for example $25–50). The bot can only lose what is in the account,
   so keep the account balance close to what you are willing to lose.
4. Export the credentials (never commit them; `.gitignore` already excludes `*.pem`, `.env`, `state.json`, CSVs):

```bash
export KALSHI_API_KEY_ID="your-key-id"
export KALSHI_PRIVATE_KEY_PATH="$HOME/secrets/kalshi_key.pem"
```

The key is used only to sign requests; it is never printed or logged.

## Paper mode (default; no key needed)

```bash
python bot.py --arm            # starts armed, simulated fills at the ask, real fees
python bot.py                  # starts DISARMED; slide the switch on the board to arm
python bot.py --arm --duration 3600   # stop after an hour
```

Open <http://127.0.0.1:8787>. The first ~3 minutes show "warming up" while it collects price ticks
(it will not trade on less than 3 minutes of data). Paper mode uses live market data and Kalshi's
own `result` to settle, and never calls the order endpoint.

Then analyse what it recorded:

```bash
python backtest.py                                   # what the bot actually did (trades.csv)
python backtest.py --replay --mode aggressive        # re-decide from snapshots.csv under other settings
```

### Judge the strategy on hundreds of rounds, not four

A paper hour is only ~4 rounds: statistically meaningless. `history.py` rebuilds what the bot would
have seen from public data (Kalshi settled rounds + 1-min quote candles, Coinbase 1-min candles):

```bash
python history.py --rounds 700 --out hist
python backtest.py --trades hist_trades.csv --snapshots hist_snaps.csv --replay --mode balanced
```

## Going live

All of these must be true or the bot stays in paper mode:

1. `config.json` has `"trading": "live"`, **and**
2. you start it with `--live`, **and**
3. `KALSHI_API_KEY_ID` / `KALSHI_PRIVATE_KEY_PATH` are set.

```bash
python bot.py --live
```

It starts **disarmed**; slide to arm on the board. (`--arm` is refused in live mode.) On startup it checks
auth and balance and **reconciles** positions with Kalshi. Recommended first run: `size_per_trade_usd: 1`
and watch one fill end-to-end, in particular that the recorded entry price and fees match your Kalshi
fills. The V2 order response fields (`average_fill_price` is on the YES leg) were taken from Kalshi's docs but
have not been exercised against a live account by this project.

### Limits (all enforced in code, not just config)

* `size_per_trade_usd` – cost **including fees** can never exceed it; contract count is rounded down.
* `daily_loss_cap_usd` – UTC day. Entries are also blocked if realized PnL **plus open exposure plus the new
  trade** could breach the cap.
* `max_losses_in_row` – stops entries until a win or the next UTC day.
* One position per round (no re-entry, even after a cash-out). Limit orders only (immediate-or-cancel at the ask,
  so nothing rests on the book). `hard_max_price` (default 0.95) caps what you will ever pay per contract.
* Fail closed: errors skip the round; an order whose outcome is unknown (timeout / 5xx) **halts and disarms**
  the bot until restart/reconcile. Prices older than `stale_seconds` (5) skip the round.

## Reaching the board from a phone

The board binds to `127.0.0.1` and is unreachable from other devices by default. Options:

* **Tailscale (recommended).** Install Tailscale on the bot machine and the phone, then:
  ```bash
  export BOARD_TOKEN="$(openssl rand -hex 16)"
  python bot.py --host 0.0.0.0 --port 8787     # or bind to the machine's tailscale IP
  ```
  Open `http://<tailscale-ip-or-name>:8787/?t=<BOARD_TOKEN>` on the phone. The bot refuses to bind a
  non-loopback address without a `BOARD_TOKEN` of at least 16 characters. Binding `0.0.0.0` also listens
  on your LAN, so bind to the Tailscale IP if the LAN is untrusted.
* Never port-forward the board to the public internet. The page is plain HTTP; the token travels in a header.
* The board also rejects cross-site POSTs (custom header required) and unexpected `Host` headers (DNS rebinding)
  when no token is set.

## Config (`config.json`)

| key | default | meaning |
|---|---|---|
| `trading` | `paper` | `live` only takes effect with `--live` |
| `mode` | `balanced` | `conservative` / `balanced` / `aggressive` (min edge, max price, entry window, max spread) |
| `assets` | `["BTC"]` | any of BTC, ETH, SOL |
| `size_per_trade_usd`, `daily_loss_cap_usd`, `max_losses_in_row` | 5, 15, 3 | limits |
| `hard_max_price` | 0.95 | absolute cap per contract, whatever the mode |
| `stale_seconds` | 5 | skip rounds when spot data is older |
| `basis_bps` | 2.0 | assumed 1-sigma gap between Coinbase and Kalshi's index (BRTI) |
| `shrink` | 0.9 | pull model probabilities toward 0.5 (fat tails / model error) |
| `momentum_weight` | 0.0 | optional drift from 2-min momentum; off because it has no demonstrated value |
| `max_disagreement` | 0.30 | reasoning engine vetoes entries where model − market mid exceeds this |
| `fee_multiplier` | auto | read from the series; override if Kalshi changes fees |

## How the strategy works (and where it can be wrong)

A round resolves **YES** if the average of the last 60 s of CF Benchmarks' BRTI is ≥ `floor_strike`
(the previous round's final average). The bot only sees Coinbase spot, so:

1. Per-second volatility = realized vol of the last 10 min of ticks.
2. P(YES) = Φ(z), with the std dev accounting for the **60-s averaging** and an explicit
   **Coinbase-vs-BRTI basis** term, then shrunk toward 0.5.
3. Edge = P(side) − ask − expected fee. Enter only if edge ≥ the mode's threshold, the ask ≤ the mode's max
   price, spread is tight, and time left is inside the mode's window.
4. The **reasoning engine** compares P(side) with the market-implied mid, inverts the open hourly BTC strike
   ladder into an implied volatility (widening, never narrowing, the model's uncertainty if the market expects
   bigger moves), and vetoes trades where the model disagrees with the market by more than
   `max_disagreement` (that is far more often a model error than a real edge). It prints its reasoning on
   the board and into `trades.csv`.

Fees: Kalshi's quadratic taker fee `ceil_to_cent(0.07 × multiplier × C × P × (1−P))`, charged on entry
and again on a cash-out; none at settlement. The "round up to the cent" rule is a conservative reading of
Kalshi's fee-rounding docs.

## Files

`bot.py` entry point · `engine.py` state/risk/trading/loop · `signals.py` model, rules, reasoning ·
`kalshi_client.py` API, signing, fees · `board.py` web UI · `backtest.py` · `history.py` · `tests/`.
Runtime files (git-ignored): `state.json`, `trades.csv`, `snapshots.csv`.

**API note:** Kalshi removed the legacy `POST /portfolio/orders` (now `410 Gone`). Orders use
`POST /portfolio/events/orders` (V2: `bid`/`ask` on the YES leg, string prices/counts). Buying NO at q is an
`ask` at 1−q; the client handles that mapping and it is unit-tested.
