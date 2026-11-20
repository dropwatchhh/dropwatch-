import chains from "./sample/chains.json";
import { hash, rng } from "./rng";
import type { AgentRun, Candles, DarkPoolLevel, FlowPrint, OptionsChain, Quote, Signal, Trader } from "./types";
import { SYMBOLS } from "./types";

const BASE: Record<string, number> = Object.fromEntries(Object.entries(chains).map(([k, v]) => [k, (v as { spot: number }).spot]));
const NOW = () => Date.now();

export function sampleChain(symbol: string): OptionsChain {
  const c = (chains as unknown as Record<string, OptionsChain>)[symbol] ?? (chains as unknown as Record<string, OptionsChain>).SPY;
  return { ...c, source: "sample" };
}

export function simQuote(symbol: string): Quote {
  const r = rng(hash(symbol));
  const base = BASE[symbol] ?? 100;
  const pct = (r() - 0.45) * 2;
  return { symbol, price: +(base * (1 + pct / 100)).toFixed(2), change: +((base * pct) / 100).toFixed(2), changePct: +pct.toFixed(2), asOf: NOW(), source: "simulated" };
}

export function simCandles(symbol: string, n = 90): Candles {
  const r = rng(hash(symbol) + 11);
  let p = (BASE[symbol] ?? 100) * 0.95;
  const day = 86_400;
  const end = Math.floor(Date.parse("2026-11-20T21:00:00Z") / 1000);
  const candles = Array.from({ length: n }, (_, i) => {
    const o = p;
    const c = o * (1 + (r() - 0.46) * 0.02);
    const h = Math.max(o, c) * (1 + r() * 0.006);
    const l = Math.min(o, c) * (1 - r() * 0.006);
    p = c;
    return { t: end - (n - i) * day, o: +o.toFixed(2), h: +h.toFixed(2), l: +l.toFixed(2), c: +c.toFixed(2), v: Math.round(1e6 * (1 + r() * 2)) };
  });
  return { symbol, candles, source: "simulated" };
}

export function simFlow(): FlowPrint[] {
  const r = rng(101);
  return Array.from({ length: 40 }, (_, i) => {
    const symbol = SYMBOLS[Math.floor(r() * SYMBOLS.length)];
    const spot = BASE[symbol];
    const type = r() > 0.5 ? "C" : "P";
    const strike = Math.round((spot * (1 + (r() - 0.5) * 0.1)) / 5) * 5;
    const size = Math.round(50 + r() * 1800);
    return {
      id: `f${i}`, time: NOW() - i * 47_000, symbol, type, strike,
      expiry: new Date(Date.parse("2026-11-20") + Math.floor(r() * 30) * 86_400_000).toISOString().slice(0, 10),
      side: (["Ask", "Bid", "Mid"] as const)[Math.floor(r() * 3)], size,
      premium: Math.round(size * (0.4 + r() * 9) * 100), score: Math.round(30 + r() * 70),
    };
  });
}

export function simDarkPool(): DarkPoolLevel[] {
  const r = rng(202);
  return SYMBOLS.flatMap((symbol) =>
    (["Support", "Resistance", "Magnet"] as const).map((kind, i) => ({
      symbol, kind,
      price: +(BASE[symbol] * (kind === "Support" ? 0.975 - i * 0.002 : kind === "Resistance" ? 1.025 : 1.003)).toFixed(2),
      shares: Math.round(200_000 + r() * 2_800_000),
    })),
  );
}

export function simSignals(): Signal[] {
  const r = rng(303);
  const strategies = ["Gamma squeeze", "Range fade", "Trend break", "Vol crush", "Opening drive"];
  return Array.from({ length: 30 }, (_, i) => ({
    id: `s${i}`, time: NOW() - i * 190_000, symbol: SYMBOLS[Math.floor(r() * SYMBOLS.length)],
    strategy: strategies[Math.floor(r() * strategies.length)], direction: r() > 0.5 ? "Long" : "Short", strength: Math.round(40 + r() * 60),
  }));
}

export function simAgents(): AgentRun[] {
  return [
    { id: "a1", name: "Flip-level fader", rule: "Fade moves away from the flip level when net gamma is positive", pnlPct: 4.2, trades: 31, status: "Running" },
    { id: "a2", name: "Wall breakout", rule: "Long when price closes above the call wall on rising volume", pnlPct: -1.1, trades: 12, status: "Running" },
    { id: "a3", name: "Vol-crush swing", rule: "Short premium the day before low-impact calendar days", pnlPct: 2.7, trades: 18, status: "Paused" },
  ];
}

export function simTraders(): Trader[] {
  return [
    { id: "t1", handle: "sample_trader_1", style: "Index scalper", return30d: 6.4, winRate: 61, followers: 1240 },
    { id: "t2", handle: "sample_trader_2", style: "Swing, mega-cap", return30d: 3.1, winRate: 54, followers: 860 },
    { id: "t3", handle: "sample_trader_3", style: "Earnings volatility", return30d: -1.8, winRate: 47, followers: 410 },
  ];
}
