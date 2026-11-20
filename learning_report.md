# Learning report: strategy ideas for trading_desk.py

Status: **harness built, no idea tested.** There is not enough real recorded data yet (0 of the 300 tokens required),
so per the task rules this stops at Step 3. Every verdict below is "need more data".

## Sources
| Source | Type | License | Notes |
|---|---|---|---|
| YouTube videos | none | n/a | `videos.txt` is empty. Add one URL per line and I will extract ideas. Transcript tools (`youtube-transcript-api`, `yt-dlp`) are installed in `.venv`. |
| slightlyuseless/memecoin-trading-bot | GitHub bot | MIT | Read README and `config.json` only. Numbers are the author's defaults, no backtest shown. Not run. |
| vellichorlabs/zeroclaw-token-risk-check | rug-check plugin | MIT | Read README rule table only. Structural checks, no performance claim. Not run. |

Skipped: repos with keyword-stuffed descriptions, "free premium sniper" repos (a common malware pattern), repos that
want a private key in a wallet file for use as-is (reviewed for ideas only, nothing run), and AGPL or unlicensed repos
(not read). No prompt-injection text was found in anything I read.

## Ideas (full list in `ideas.jsonl`; none rated above "medium" trust)
| id | idea | trust | verdict |
|---|---|---|---|
| buysell_1_5 | require buy/sell ratio >= 1.5 | low | need more data |
| momentum_5pct | require +5% change and ratio >= 2 | low | need more data |
| stop_30 | stop loss -30% instead of -15% | low | need more data |
| trail_50_20 | trail activates at +50%, trail 20% | low | need more data |
| ladder_1_8_3 | sell 40% at 1.8x and 40% at 3x | low | need more data (not implemented) |
| dev_sell_exit | exit if dev wallet sells | low | need more data (feed lacks dev trades) |
| unique_buyers | >=3 unique buyers, max single buyer 60% | low | need more data (feed lacks wallet data) |
| top10_35 | reject if top 10 holders > 35% | medium | need more data (recorder has no on-chain fields yet) |
| top1_50 | reject if top holder >= 50% | medium | need more data; the top account is usually the pool, so likely too crude |
| t22_extensions | reject transfer-hook / permanent-delegate / default-frozen mints | medium | already in the bot's Safety stage; structural, not a performance claim |
| fee_close_auth | reject transfer fee >= 10% or a close authority | medium | need more data |

## What was built (nothing edited in `trading_desk.py`)
- `record.py`: paper-only recorder; saves every scanned token's features and a 90-step price path to `data/snapshots.jsonl`.
  Checked against the live DexScreener feed: 21 tokens recorded on the first scan.
- `backtest.py`: replays snapshots through the real `Desk` class (3% round-trip cost, stop loss, partial exit, break-even
  stop, max hold). Chronological 70/30 split, test part evaluated once. Reports trades, win rate, average return per trade,
  max drawdown, baseline winners blocked, baseline losers avoided, and average return without the top 2 winners.
  Pass rule: more than baseline on the held-out 30%, at least 100 trades, and still better after removing the top 2 winners.
  Pause and kill limits are off in replay so signals get a fair sample; drawdown is reported instead.
- `strategies/candidates.py`: testable ideas as separate parameter sets. Nothing imports them into the live bot.
- Plumbing was checked on simulated data only. The backtest refuses simulated data unless `--allow-sim` is passed, and that output is not evidence.

## To get real data, then test
    . .venv/bin/activate
    python3 record.py --feed dexscreener --steps 20000 --delay 20     # paper only, no keys; run for many hours
    python3 backtest.py                                               # refuses until >= 300 complete tokens

## Observations that are not conclusions
- In the first live scan most tokens were only a few minutes old, while the bot requires age >= 30 minutes.
  This was one scan and is not a finding, but the baseline may trade rarely on this feed. Check the trade counts.
- Fixed parameters were taken from sources, not tuned, so the 70% tune split is reference only.

## What the data does and does not prove
Currently it proves nothing: there is no real data and no idea has been tested. Even after recording, backtests on
DexScreener snapshots will not capture real fills, slippage on thin pools, failed sells, honeypots, or bots front-running
you; the 3% cost is an assumption. A held-out pass can show an idea is not worse than the baseline on that sample. It
cannot show the idea makes money live. Treat any pass as a reason for longer paper trading, not for real money.
