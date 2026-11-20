#!/usr/bin/env python3
"""
Solana memecoin trading desk with hard risk limits.

Pipeline: Scout -> Filter -> Analyst -> Safety -> Executor -> Risk -> Logger
A token is only traded if it passes every stage. Rejections are logged, and
re-checked later so you can see whether your filters are too strict or loose.

MODES
  python3 trading_desk.py --feed sim --steps 300                  offline test, fake money
  python3 trading_desk.py --feed dexscreener --steps 200          live market data, fake money
  python3 trading_desk.py --live --feed dexscreener --steps 100000   REAL MONEY (max $50)

LIVE SETUP (environment variables, never put keys in this file)
  SOLANA_PRIVATE_KEY   base58 key of a NEW wallet holding <= $50 USDC + ~$2 SOL
  JUPITER_API_KEY      free key from developers.jup.ag/portal
  SOLANA_RPC_URL       (recommended) your own RPC URL; the public one rate-limits
  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID   (optional) phone alerts
  pip install solders

No bot can guarantee profit. Most new memecoins go to zero. Only risk money you
can lose completely. The live executor was written against Jupiter's docs but
could not be tested with real money when it was built: start small and watch it.
"""
import argparse, base64, json, os, random, sys, time, urllib.parse, urllib.request
from dataclasses import dataclass, asdict

CFG = {
    "start_equity": 1000.0,
    "position_pct": 0.05,          # 5% of equity per trade
    "max_open": 3,
    "stop_loss": 0.15,             # exit at -15%
    "take_profit": 0.40,           # exit at +40%
    "trail_pct": 0.12,             # trailing stop once in profit
    "daily_loss_limit": 0.05,      # pause for the day at -5% equity
    "max_drawdown": 0.20,          # KILL SWITCH: stop everything at -20% from peak
    "max_trades_per_day": 15,
    "loss_cooldown_steps": 5,      # pause buying after a losing exit
    "min_liquidity": 25_000,
    "min_age_min": 30,
    "max_buy_sell_skew": 3.0,
    "min_score": 60,
    "max_top_holders_pct": 40.0,   # holders #2-#10 combined (#1 is usually the pool)
    "followup_steps": 30,          # re-check rejected tokens after this many steps
    "fee_slippage": 0.03,          # paper-mode round-trip cost assumption
    "log_file": "trades.jsonl",
    "state_file": "positions.json",
}

USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
JUP = "https://api.jup.ag/swap/v2"
RPC_URL = os.environ.get("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
HARD_CAP_USD = 50.0                # the bot can never have more than this deployed
KILL_FILE = "KILLED"               # written when the kill switch trips; delete by hand to re-arm


# ---------- helpers ----------
def http_json(method, url, body=None, headers=None, timeout=20):
    h = {"User-Agent": "desk", "Content-Type": "application/json"}
    h.update(headers or {})
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, method=method, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)

def rpc(method, params):
    r = http_json("POST", RPC_URL, {"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    if "error" in r: raise RuntimeError(r["error"])
    return r.get("result")

def alert(msg):
    print(msg, flush=True)
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if tok and chat:
        try: http_json("POST", f"https://api.telegram.org/bot{tok}/sendMessage",
                       {"chat_id": chat, "text": msg}, timeout=10)
        except Exception: pass


@dataclass
class Token:
    addr: str; symbol: str; price: float; liquidity: float
    age_min: float; buys: int; sells: int; vol_5m: float; change_5m: float

@dataclass
class Position:
    token: Token; entry: float; size: float; peak: float; tokens_raw: int = 0


# ---------- feeds ----------
class SimFeed:
    """Synthetic market: most tokens rug, a few run. For testing the logic only."""
    def __init__(self, seed=7):
        self.r = random.Random(seed); self.prices = {}; self.n = 0
    def new_pairs(self):
        out = []
        for _ in range(self.r.randint(3, 8)):
            self.n += 1
            t = Token(f"SIM{self.n}", f"SIM{self.n}", self.r.uniform(1e-6, 1e-4),
                      self.r.choice([2e3, 8e3, 30e3, 60e3, 150e3]), self.r.uniform(1, 240),
                      self.r.randint(5, 400), self.r.randint(1, 300),
                      self.r.uniform(1e3, 8e4), self.r.uniform(-20, 60))
            self.prices[t.addr] = (t.price, self.r.random())
            out.append(t)
        return out
    def price(self, tok):
        p, fate = self.prices[tok.addr]
        p *= 1 + self.r.gauss(-0.03 if fate < 0.7 else 0.04, 0.08)   # 70% decay, 30% run
        self.prices[tok.addr] = (max(p, 1e-12), fate)
        return p

class DexScreenerFeed:
    def new_pairs(self):
        out = []
        try:
            prof = http_json("GET", "https://api.dexscreener.com/token-profiles/latest/v1")
            addrs = [p["tokenAddress"] for p in prof if p.get("chainId") == "solana"][:25]
            for a in addrs:
                pairs = http_json("GET", f"https://api.dexscreener.com/latest/dex/tokens/{a}").get("pairs") or []
                if not pairs: continue
                p = pairs[0]; tx = p.get("txns", {}).get("m5", {})
                age = (time.time() * 1000 - p.get("pairCreatedAt", 0)) / 60000
                out.append(Token(a, p["baseToken"]["symbol"], float(p.get("priceUsd") or 0),
                                 (p.get("liquidity") or {}).get("usd", 0), age,
                                 tx.get("buys", 0), tx.get("sells", 0),
                                 (p.get("volume") or {}).get("m5", 0),
                                 (p.get("priceChange") or {}).get("m5", 0)))
        except Exception as e:
            print("feed error:", e)
        return out
    def price(self, tok):
        try:
            pairs = http_json("GET", f"https://api.dexscreener.com/latest/dex/tokens/{tok.addr}").get("pairs") or []
            return float(pairs[0].get("priceUsd") or tok.price)
        except Exception:
            return tok.price


# ---------- safety agent (live only) ----------
class Safety:
    """Rejects tokens you probably can't sell or that the creator can still abuse."""
    def __init__(self, jup_key): self.jup_key = jup_key

    def check(self, t, usd):
        """Return a reason string if the token is unsafe, else None."""
        try:
            info = rpc("getAccountInfo", [t.addr, {"encoding": "jsonParsed"}])
            parsed = (((info or {}).get("value") or {}).get("data") or {}).get("parsed", {}).get("info")
            if not parsed: return "cannot read token mint"
            if parsed.get("mintAuthority"): return "creator can still mint more"
            if parsed.get("freezeAuthority"): return "creator can freeze wallets"
            supply = int(parsed["supply"])
            if supply <= 0: return "zero supply"
            holders = [int(x["amount"]) for x in rpc("getTokenLargestAccounts", [t.addr])["value"]]
            pct = sum(holders[1:10]) / supply * 100
            if pct > CFG["max_top_holders_pct"]: return f"top holders own {pct:.0f}%"
            # can we actually sell? ask for a sell quote (no taker = quote only)
            raw = int(usd / t.price * 10 ** int(parsed["decimals"]))
            q = http_json("GET", f"{JUP}/order?" + urllib.parse.urlencode(
                {"inputMint": t.addr, "outputMint": USDC, "amount": raw}),
                headers={"x-api-key": self.jup_key})
            if q.get("errorMessage") or not int(q.get("outAmount") or 0):
                return "no sell route"
            out_usd = q.get("outUsdValue")
            if out_usd is not None and float(out_usd) < usd * 0.7:
                return f"selling would lose >30% (quote ${float(out_usd):.2f} for ${usd:.2f})"
            return None
        except Exception as e:
            return f"safety check failed ({type(e).__name__})"   # when unsure, don't trade


# ---------- live execution (real money) ----------
class LiveExecutor:
    """Swaps via Jupiter Swap V2: GET /order -> sign -> POST /execute.
    USDC is the base currency so the dollar cap is exact."""
    def __init__(self):
        from solders.keypair import Keypair            # pip install solders
        key, self.api = os.environ.get("SOLANA_PRIVATE_KEY"), os.environ.get("JUPITER_API_KEY")
        if not key or not self.api:
            sys.exit("Set SOLANA_PRIVATE_KEY and JUPITER_API_KEY environment variables.")
        self.kp = Keypair.from_base58_string(key)
        self.wallet = str(self.kp.pubkey()); self.deployed = 0.0

    def _sign(self, b64):
        from solders.transaction import VersionedTransaction
        from solders.message import to_bytes_versioned
        tx = VersionedTransaction.from_bytes(base64.b64decode(b64))
        msg = tx.message
        signers = list(msg.account_keys[:msg.header.num_required_signatures])
        sigs = list(tx.signatures)
        sigs[signers.index(self.kp.pubkey())] = self.kp.sign_message(to_bytes_versioned(msg))
        return base64.b64encode(bytes(VersionedTransaction.populate(msg, sigs))).decode()

    def _swap(self, inp, out, amount, check_value=False):
        try:
            q = urllib.parse.urlencode({"inputMint": inp, "outputMint": out, "amount": int(amount),
                                        "taker": self.wallet, "slippageBps": 300})
            order = http_json("GET", f"{JUP}/order?{q}", headers={"x-api-key": self.api}, timeout=30)
            if not order.get("transaction"):
                return None, order.get("errorMessage") or order.get("error") or "no transaction"
            if check_value:   # refuse buys where the quote is worth much less than we pay
                i, o = order.get("inUsdValue"), order.get("outUsdValue")
                if i and o and float(o) < float(i) * 0.85:
                    return None, f"quote loses >15% on entry (in ${i}, out ${o})"
            res = http_json("POST", f"{JUP}/execute", {
                "signedTransaction": self._sign(order["transaction"]),
                "requestId": order["requestId"]}, headers={"x-api-key": self.api}, timeout=60)
            if res.get("status") != "Success":
                return None, res.get("error") or f"execute failed, code {res.get('code')}"
            return res, None
        except Exception as e:
            return None, f"{type(e).__name__}: {e}"

    def buy(self, tok, usd):
        if self.deployed + usd > HARD_CAP_USD:
            return 0, "hard cap reached"
        res, err = self._swap(USDC, tok.addr, usd * 1e6, check_value=True)
        if err: return 0, err
        self.deployed += usd
        return int(res["outputAmountResult"]), None

    def sell(self, pos):
        res, err = self._swap(pos.token.addr, USDC, pos.tokens_raw)
        if err: return 0.0, err
        self.deployed = max(0.0, self.deployed - pos.size)
        return int(res["outputAmountResult"]) / 1e6, None

    def usdc_balance(self):
        try:
            r = rpc("getTokenAccountsByOwner", [self.wallet, {"mint": USDC}, {"encoding": "jsonParsed"}])
            return sum(a["account"]["data"]["parsed"]["info"]["tokenAmount"]["uiAmount"] or 0
                       for a in r["value"])
        except Exception:
            return None


# ---------- agents ----------
def scout(feed, seen):
    return [t for t in feed.new_pairs() if t.addr not in seen and t.price > 0]

def filter_agent(t):
    if t.liquidity < CFG["min_liquidity"]: return "low liquidity"
    if t.age_min < CFG["min_age_min"]: return "too new"
    if t.sells == 0 or t.buys / t.sells > CFG["max_buy_sell_skew"]: return "honeypot-like buy/sell skew"
    return None

def analyst(t):
    s = 0
    s += min(30, t.liquidity / 5000)
    s += min(30, t.vol_5m / 2000)
    s += 20 if 0 < t.change_5m < 80 else 0       # momentum, but not already parabolic
    s += 20 if 0.8 <= t.buys / max(t.sells, 1) <= 2.0 else 0
    return round(s)


class Desk:
    def __init__(self, feed, executor=None, safety=None):
        self.ex, self.safety, self.feed = executor, safety, feed
        self.cash = CFG["start_equity"]; self.peak = self.cash
        self.pos = {}; self.seen = set(); self.watch = []; self.failed = set()
        self.killed = None; self.paused = None; self.step = 0
        self.day = time.strftime("%Y-%m-%d"); self.trades_today = 0; self.cooldown_until = 0
        self.f = open(CFG["log_file"], "a")
        self.load()
        self.day_start = self.equity()

    # Logger agent
    def log(self, kind, **kw):
        kw.update(kind=kind, step=self.step, t=time.strftime("%H:%M:%S"))
        self.f.write(json.dumps(kw) + "\n"); self.f.flush()

    def note(self, msg):                      # phone/console alert, live mode only
        if self.ex: alert(msg)

    # saved positions so a crash or restart never forgets what the wallet holds
    def save(self):
        if not self.ex: return
        with open(CFG["state_file"], "w") as f:
            json.dump({"cash": self.cash, "peak": self.peak, "deployed": self.ex.deployed,
                       "pos": [asdict(p) for p in self.pos.values()]}, f)

    def load(self):
        if not (self.ex and os.path.exists(CFG["state_file"])): return
        s = json.load(open(CFG["state_file"]))
        self.cash, self.peak, self.ex.deployed = s["cash"], s["peak"], s["deployed"]
        for d in s["pos"]:
            p = Position(Token(**d["token"]), d["entry"], d["size"], d["peak"], d["tokens_raw"])
            self.pos[p.token.addr] = p; self.seen.add(p.token.addr)
        if self.pos: self.note(f"Restored {len(self.pos)} open position(s) from {CFG['state_file']}")

    def equity(self):
        return self.cash + sum(p.size * (p.token.price / p.entry) for p in self.pos.values())

    def close(self, addr, why):
        p = self.pos[addr]
        if self.ex:
            value, err = self.ex.sell(p)
            if err:
                self.log("sell_failed", sym=p.token.symbol, why=err)
                if addr not in self.failed:           # alert once, keep retrying quietly
                    self.failed.add(addr)
                    self.note(f"SELL FAILED {p.token.symbol}: {err} (retrying each step)")
                return
        else:
            value = p.size * (p.token.price / p.entry) * (1 - CFG["fee_slippage"])
        self.failed.discard(addr)
        del self.pos[addr]
        self.cash += value
        pnl = value - p.size
        if pnl < 0: self.cooldown_until = self.step + CFG["loss_cooldown_steps"]
        self.log("exit", sym=p.token.symbol, why=why, pnl=round(pnl, 2))
        self.note(f"SOLD {p.token.symbol} ({why}) pnl ${pnl:+.2f}")
        self.save()

    def manage(self):                         # stop-loss / take-profit / trailing stop
        for addr, p in list(self.pos.items()):
            p.token.price = self.feed.price(p.token)
            ret = p.token.price / p.entry - 1
            p.peak = max(p.peak, p.token.price)
            if ret <= -CFG["stop_loss"]: self.close(addr, "stop loss")
            elif ret >= CFG["take_profit"]: self.close(addr, "take profit")
            elif p.peak / p.entry > 1.1 and p.token.price <= p.peak * (1 - CFG["trail_pct"]):
                self.close(addr, "trailing stop")

    def followups(self):                      # what did rejected tokens do afterwards?
        for w in list(self.watch):
            if self.step - w["step"] >= CFG["followup_steps"]:
                p = self.feed.price(w["tok"])
                self.log("reject_followup", sym=w["tok"].symbol, why=w["why"],
                         change_pct=round((p / w["price"] - 1) * 100, 1))
                self.watch.remove(w)

    def reject(self, t, why):
        self.log("reject", sym=t.symbol, why=why)
        if len(self.watch) < 20:
            self.watch.append({"tok": t, "why": why, "price": t.price, "step": self.step})

    def run_step(self):
        self.step += 1
        today = time.strftime("%Y-%m-%d")
        if today != self.day:                 # new day: reset the daily limits
            self.day, self.trades_today, self.paused = today, 0, None
            self.day_start = self.equity()
        self.manage(); self.followups()
        if self.ex and self.step % 30 == 0:
            self.log("wallet", usdc=self.ex.usdc_balance(), bot_equity=round(self.equity(), 2))

        # Risk agent: the "know when to stop" part
        eq = self.equity(); self.peak = max(self.peak, eq)
        if not self.killed and eq <= self.peak * (1 - CFG["max_drawdown"]):
            self.killed = "KILL SWITCH: max drawdown hit"
            if self.ex: open(KILL_FILE, "w").write(self.killed)     # blocks restarts
            self.note(f"{self.killed}. Selling everything and stopping.")
        elif not self.paused and eq <= self.day_start * (1 - CFG["daily_loss_limit"]):
            self.paused = "daily loss limit hit"
            self.note(f"{self.paused}. Paused until tomorrow.")
        if self.killed or self.paused:
            for a in list(self.pos): self.close(a, self.killed or self.paused)
            self.save()
            return not self.killed

        if self.step < self.cooldown_until or self.trades_today >= CFG["max_trades_per_day"]:
            return True
        for t in scout(self.feed, self.seen):
            self.seen.add(t.addr)
            why = filter_agent(t)                                   # Filter
            if why: self.reject(t, why); continue
            score = analyst(t)                                      # Analyst
            if score < CFG["min_score"]: self.reject(t, f"score {score}"); continue
            if len(self.pos) >= CFG["max_open"]: continue
            size = round(self.equity() * CFG["position_pct"], 2)
            if size > self.cash or (self.ex and size < 1.0): continue
            if self.safety:                                         # Safety
                why = self.safety.check(t, size); time.sleep(1.1)   # stay under rate limits
                if why: self.reject(t, "unsafe: " + why); continue
            raw = 0                                                 # Executor
            if self.ex:
                raw, err = self.ex.buy(t, size)
                if err: self.log("buy_failed", sym=t.symbol, why=err); continue
            self.cash -= size
            self.pos[t.addr] = Position(t, t.price, size, t.price, raw)
            self.trades_today += 1
            self.log("buy", sym=t.symbol, score=score, size=size)
            self.note(f"BOUGHT {t.symbol} ${size:.2f} (score {score})")
            self.save()
        return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--feed", choices=["sim", "dexscreener"], default="sim")
    ap.add_argument("--steps", type=int, default=300)
    ap.add_argument("--delay", type=float, default=None, help="seconds between steps")
    ap.add_argument("--live", action="store_true", help="REAL MONEY via Jupiter")
    a = ap.parse_args()
    ex = safety = None
    if a.live:
        if a.feed != "dexscreener": sys.exit("--live requires --feed dexscreener")
        if os.path.exists(KILL_FILE):
            sys.exit(f"Kill switch tripped earlier ({open(KILL_FILE).read()}). "
                     f"Review trades.jsonl, then delete {KILL_FILE} to re-arm.")
        CFG["start_equity"] = HARD_CAP_USD
        if input(f"LIVE: up to ${HARD_CAP_USD:.0f} of real money. You can lose all of it. "
                 f"Type I ACCEPT: ") != "I ACCEPT":
            sys.exit("Cancelled.")
        ex = LiveExecutor(); safety = Safety(ex.api)
        start_bal = ex.usdc_balance()
        alert(f"Bot started. Wallet {ex.wallet[:6]}... USDC balance: {start_bal}")
    delay = a.delay if a.delay is not None else (20 if a.live else 0)
    d = Desk(SimFeed() if a.feed == "sim" else DexScreenerFeed(), ex, safety)
    try:
        for _ in range(a.steps):
            if not d.run_step(): break
            time.sleep(delay)
    except KeyboardInterrupt:
        print("\nStopping: closing open positions...")
        for addr in list(d.pos): d.close(addr, "manual stop")
    if d.pos:
        alert("WARNING: positions still open (sell failed): " +
              ", ".join(p.token.symbol for p in d.pos.values()) + f". See {CFG['state_file']}.")
    eq = d.equity()
    print(f"steps={d.step} equity=${eq:,.2f} ({(eq/CFG['start_equity']-1)*100:+.1f}%) "
          f"open={len(d.pos)} status={d.killed or d.paused or 'ran to completion'}")
    if ex:
        end_bal = ex.usdc_balance()
        print(f"wallet USDC: start {start_bal} -> end {end_bal}  (this is your real result)")
    print(f"log: {CFG['log_file']}")

if __name__ == "__main__":
    main()
