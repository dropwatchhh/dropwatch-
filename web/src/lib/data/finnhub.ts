import { cached } from "./cache";
import type { Candles, Quote } from "./types";

const BASE = "https://finnhub.io/api/v1";
const key = () => process.env.FINNHUB_API_KEY?.trim();
export const hasFinnhub = () => !!key();

/** Free tier: ~60 calls/min. Quotes cached 60s, candles 15 min. Throws on any failure so the caller can fall back. */
export function finnhubQuote(symbol: string): Promise<Quote> {
  return cached(`fh:q:${symbol}`, 60_000, async () => {
    const res = await fetch(`${BASE}/quote?symbol=${encodeURIComponent(symbol)}&token=${key()}`, { cache: "no-store" });
    if (!res.ok) throw new Error(`finnhub quote ${res.status}`);
    const j = (await res.json()) as { c: number; d: number; dp: number; t: number };
    if (!j.c) throw new Error("finnhub quote empty");
    return { symbol, price: j.c, change: j.d ?? 0, changePct: j.dp ?? 0, asOf: (j.t || Date.now() / 1000) * 1000, source: "finnhub" as const };
  });
}

export function finnhubCandles(symbol: string): Promise<Candles> {
  return cached(`fh:c:${symbol}`, 15 * 60_000, async () => {
    const to = Math.floor(Date.now() / 1000);
    const from = to - 120 * 86_400;
    const res = await fetch(`${BASE}/stock/candle?symbol=${encodeURIComponent(symbol)}&resolution=D&from=${from}&to=${to}&token=${key()}`, { cache: "no-store" });
    if (!res.ok) throw new Error(`finnhub candles ${res.status}`);
    const j = (await res.json()) as { s: string; t?: number[]; o: number[]; h: number[]; l: number[]; c: number[]; v: number[] };
    if (j.s !== "ok" || !j.t) throw new Error("finnhub candles empty");
    return { symbol, source: "finnhub" as const, candles: j.t.map((t, i) => ({ t, o: j.o[i], h: j.h[i], l: j.l[i], c: j.c[i], v: j.v[i] })) };
  });
}
