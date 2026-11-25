# LIVE pilot: what is built, what is locked

**Status: LIVE is OFF.** `config.json` is `paper`. No live or demo credentials exist in this environment, no real
order was ever placed, and nothing here turns LIVE on. You do that yourself, on the Trading tab, by typing a phrase.

**Read first:** `READINESS.md` still says **NO-GO**. This pilot is the safety machinery for a small real-money test; it is
not evidence that the strategy has an edge (over 14 days of history it did not). With a $10 bankroll the realistic
outcome is a small loss. The breakers below exist to cap that loss at about half the bankroll.

## What you asked for → what exists

| # | Request | Built | Where |
|---|---|---|---|
| 1 | Separate production key path | `KALSHI_LIVE_API_KEY_ID` + `KALSHI_LIVE_PRIVATE_KEY_PATH` (point it at your Render Secret File, e.g. `/etc/secrets/kalshi_live.pem`). Demo uses `KALSHI_DEMO_*`. Base URLs are fixed per environment (`KALSHI_BASE_URL` is ignored). Loading one while the other's variables exist in the same process is **refused**; the old shared names are refused as ambiguous; same key for both is detected. Paper mode reads no credentials at all. | `credentials.py` |
| 2 | Pilot limits, maximums fixed in code, UI can only lower | stake **$1 / 1 contract**, **1 open position total**, **3 orders/day**, no ADD. Enforced inside the order path (`State.check_entry`) and again in the client (`buy_limits`). `PILOT_MAX` is an immutable constant; `/api/limits/lower` rejects any raise; a hand-edited `pilot.json` is clamped on load. | `pilot.py`, `engine.py`, `kalshi_client.py` |
| 2b | Trade only on Strong BUY NOW incl. flip-risk SAFE TO ENTER and positive edge after fees | The order path refuses unless it is handed a **fresh (<5 s) STRONG BUY NOW for that ticker**. Grading is below. | `pilot.evaluate_signal` |
| 3 | Loss breakers | Pause for the UTC day at **−$2** (also refuses a trade that could cross it). Hard stop at **−$5** cumulative: disarms, switches LIVE off, persists across restarts, reset needs **two typed phrases in order** (wrong phrase restarts; step 1 expires after 5 min). Reset never turns LIVE on. | `pilot.py` |
| 4 | Enable LIVE: typed phrase, red banner everywhere, only while demo order + shard check pass | Phrase `ENABLE LIVE TRADING WITH REAL MONEY` on the Trading tab. Red **LIVE — REAL MONEY** banner is rendered server-side on all three pages (Board, Trading, Log). The full readiness checklist runs at enable, every 60 s while on (auto-switches LIVE off if anything fails) **and again at the moment of every order**. LIVE is off after every restart, and enabling does not arm. | `board.py`, `engine.Ctx.readiness/gate` |
| 5 | STOP TRADING NOW also cancels resting live orders | Red button on every page: engages the kill file, disarms, switches LIVE off, `DELETE /portfolio/events/orders` (cancel-all). If the cancel fails it says so loudly and stays stopped. `python kill.py` does the same from a shell (`--flatten` also sells). | `board._stop`, `kill.py` |
| 6 | Log everything; real P&L; post-mortem per loss; no auto-retune | `live_ledger.jsonl` (append-only; order logged **before** it is sent, then result, then a check of Kalshi's own fill record, then settlement and a reconciliation with Kalshi's settlement record). Log tab shows P&L after fees, fees, unverified count, the ledger, and a post-mortem for every loss. Nothing reads post-mortems back; a test proves losses leave `MODES`, config, pilot limits and the flip threshold untouched. | `livelog.py`, `postmortem.py` |
| 7 | Tests, push, report | 236 tests, 93% coverage, secrets audit clean. | `tests/` |

## Choices I made where your spec named things this codebase did not have: tell me if you disagree

* **Strong BUY NOW** = every one of: fresh data; the strictest existing rule set (conservative mode: edge ≥ 0.10 after
  fees, ask ≤ 0.75, 90–600 s left, spread ≤ 0.04); edge after fees > 0; reasoning engine does not veto (model within 0.30
  of the market mid); flip-risk SAFE; depth ≥ 1 contract. It reuses existing thresholds; **no new tuned thresholds** except:
* **Flip-risk SAFE TO ENTER** (new, my judgment, untested): the chance spot touches the target before close is ≤ **25%**
  (`2·(1−Φ(|z|))`) **and** 2-minute momentum is not against the side. It can only make the bot trade less.
* **"3 trades per day"** counts orders *sent* (filled or not), the stricter reading.
* **"Stake of $1 or 1 contract"** = both: exactly 1 contract and cost incl. fee ≤ $1.
* **Hard stop** is on cumulative live P&L since pilot start (or since the last reset, which moves the baseline). After a reset
  you could lose another $5. That is your call to make, with two typed confirmations.
* The pilot is **BTC only** and the Board's mode switch is locked (the pilot's rules are fixed). The Board shows the pilot's
  real limits, not the config's.
* STOP leaves open positions alone (use Cash out or `kill.py --flatten`) and stays locked until `python kill.py --clear`.

## What is still LOCKED (LIVE cannot be enabled until each is done)

1. **Demo test order.** Needs a Kalshi **demo** account and a **separate demo API key** that only you can create. Run it in its own
   shell with only demo variables:
   `KALSHI_DEMO_API_KEY_ID=… KALSHI_DEMO_PRIVATE_KEY_PATH=… python preflight.py demo`. It buys 1 contract on demo, verifies
   count/price/**fee** against Kalshi's fill record (this also checks the unverified `0.07` fee coefficient), and sells it back.
   Result is valid for 24 h. **Not run.**
2. **Shard funding.** Crypto markets trade on **exchange shard 2** and Kalshi requires that shard to be funded for API orders.
   Funds sitting in the default shard cannot trade them. Move the $10 to shard 2 at kalshi.com/account/exchange-indexes. The
   shard check refuses LIVE otherwise. **Not checked (no live account here).**
3. **Live credentials** (`KALSHI_LIVE_*`) in the live process only, with **no** `KALSHI_DEMO_*` variables in it.
4. **Your decision**, given `READINESS.md`: Gate 2 (demo) is blocked and Gate 3 (14-day, 300-trade paper run) failed.

## Unverified against a real account (taken from Kalshi's docs; the checks above fail closed if reality differs)

V2 order response fields (`average_fill_price` on the YES leg); `fee_cost` on fills; `balance_breakdown` shape; settlement
`revenue` / `fee_cost` meaning (P&L uses fills' fees; the settlement fee is logged for comparison, not added); positions
`position_fp` sign (+YES / −NO); cancel-all returning 204. Any mismatch in a fill or settlement halts and disarms.

## When you decide to try it

```bash
# 1. once, in a shell with ONLY demo vars:  python preflight.py demo        (must print DEMO TEST ORDER: PASS)
# 2. live process (Render: set the two LIVE env vars; add the key as a Secret File; NO demo vars):
export KALSHI_LIVE_API_KEY_ID=...  KALSHI_LIVE_PRIVATE_KEY_PATH=/etc/secrets/kalshi_live.pem
export BOARD_TOKEN="$(openssl rand -hex 16)"            # required when the board is reachable from outside
python bot.py --config config.live-pilot.json --live --host 0.0.0.0
# 3. open /trading, confirm every check is PASS, type the phrase, press Enable LIVE, then arm on the Board.
```
It starts **disarmed with LIVE off**. `python audit_secrets.py . --git` with your real vars set is worth running first.
