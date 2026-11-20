import type { OptionsChain } from "./types";

// Standard normal pdf
const phi = (x: number) => Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI);

/** Black-Scholes gamma (same for calls and puts). */
export function bsGamma(spot: number, strike: number, tYears: number, iv: number, r = 0.04): number {
  if (spot <= 0 || strike <= 0 || iv <= 0 || tYears <= 0) return 0;
  const sd = iv * Math.sqrt(tYears);
  const d1 = (Math.log(spot / strike) + (r + 0.5 * iv * iv) * tYears) / sd;
  return phi(d1) / (spot * sd);
}

export type GexCell = { strike: number; expiry: string; gex: number };
export type GexResult = {
  symbol: string;
  spot: number;
  strikes: number[]; // descending
  expiries: string[];
  cells: GexCell[];
  byStrike: { strike: number; gex: number }[];
  netGex: number;
  flip: number | null;
  callWall: number | null;
  putWall: number | null;
  maxAbs: number;
};

const DAY = 86_400_000;

/**
 * Dealer gamma exposure in $ per 1% move. Convention (assumed, not observed):
 * dealers are long calls (+) and short puts (-). Identical for every chain source.
 */
export function computeGex(chain: OptionsChain, band = 0.08): GexResult {
  const { spot, rows } = chain;
  const lo = spot * (1 - band), hi = spot * (1 + band);
  const map = new Map<string, number>();
  const expSet = new Set<string>();
  const strikeSet = new Set<number>();
  for (const r of rows) {
    if (r.strike < lo || r.strike > hi) continue;
    const t = Math.max((Date.parse(r.expiry + "T20:00:00Z") - chain.asOf) / DAY, 0.25) / 365;
    const g = bsGamma(spot, r.strike, t, r.iv);
    const sign = r.type === "C" ? 1 : -1;
    const gex = sign * g * r.oi * 100 * spot * spot * 0.01;
    const k = `${r.strike}|${r.expiry}`;
    map.set(k, (map.get(k) ?? 0) + gex);
    expSet.add(r.expiry);
    strikeSet.add(r.strike);
  }
  const expiries = [...expSet].sort();
  const strikes = [...strikeSet].sort((a, b) => b - a);
  const cells: GexCell[] = [];
  const agg = new Map<number, number>();
  let maxAbs = 0;
  for (const s of strikes) {
    for (const e of expiries) {
      const gex = map.get(`${s}|${e}`) ?? 0;
      cells.push({ strike: s, expiry: e, gex });
      agg.set(s, (agg.get(s) ?? 0) + gex);
      maxAbs = Math.max(maxAbs, Math.abs(gex));
    }
  }
  const byStrike = strikes.map((s) => ({ strike: s, gex: agg.get(s) ?? 0 }));
  const netGex = byStrike.reduce((a, b) => a + b.gex, 0);
  // Flip: strike where cumulative gex (ascending strikes) crosses zero, nearest to spot.
  const asc = [...byStrike].sort((a, b) => a.strike - b.strike);
  let cum = 0, flip: number | null = null, best = Infinity;
  for (let i = 0; i < asc.length; i++) {
    const prev = cum;
    cum += asc[i].gex;
    if (i > 0 && Math.sign(prev) !== Math.sign(cum) && prev !== 0) {
      const d = Math.abs(asc[i].strike - spot);
      if (d < best) { best = d; flip = asc[i].strike; }
    }
  }
  const callWall = byStrike.reduce<{ strike: number; gex: number } | null>((m, c) => (c.gex > (m?.gex ?? 0) ? c : m), null)?.strike ?? null;
  const putWall = byStrike.reduce<{ strike: number; gex: number } | null>((m, c) => (c.gex < (m?.gex ?? 0) ? c : m), null)?.strike ?? null;
  return { symbol: chain.symbol, spot, strikes, expiries, cells, byStrike, netGex, flip, callWall, putWall, maxAbs };
}
