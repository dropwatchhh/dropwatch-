import { computeGex } from "./gex";
import { provider } from "./index";
import { SYMBOLS, type Source } from "./types";

export type Setup = {
  symbol: string;
  score: number;
  regime: "Positive gamma" | "Negative gamma";
  bias: "Mean-reverting" | "Trending";
  spot: number;
  flip: number | null;
  distToFlipPct: number | null;
  changePct: number;
  netGex: number;
  reasons: string[];
  chainSource: Source;
  quoteSource: Source;
};

/** Illustrative ranking: not a trading signal. Blends gamma regime, flip proximity and momentum. */
export async function getSetups(): Promise<Setup[]> {
  const out = await Promise.all(
    SYMBOLS.map(async (symbol) => {
      const [chain, quote] = await Promise.all([provider.getOptionsChain(symbol), provider.getQuote(symbol)]);
      const gex = computeGex(chain);
      const dist = gex.flip ? ((chain.spot - gex.flip) / chain.spot) * 100 : null;
      const reasons: string[] = [];
      let score = 40;
      const neg = gex.netGex < 0;
      if (neg) { score += 12; reasons.push("Net gamma negative: moves tend to extend"); }
      else reasons.push("Net gamma positive: moves tend to be dampened");
      if (dist !== null) {
        score += Math.max(0, 5 - Math.abs(dist)) * 4;
        if (Math.abs(dist) < 1.5) reasons.push(`Spot within ${Math.abs(dist).toFixed(1)}% of the flip level`);
      }
      score += Math.min(20, Math.abs(quote.changePct) * 8);
      if (Math.abs(quote.changePct) > 1) reasons.push(`Large day move (${quote.changePct.toFixed(1)}%)`);
      if (gex.callWall && Math.abs(gex.callWall - chain.spot) / chain.spot < 0.02) reasons.push(`Call wall ${gex.callWall} is close overhead`);
      if (gex.putWall && Math.abs(gex.putWall - chain.spot) / chain.spot < 0.02) reasons.push(`Put wall ${gex.putWall} is close below`);
      return {
        symbol, score: Math.round(Math.min(99, score)), regime: neg ? "Negative gamma" : "Positive gamma",
        bias: neg ? "Trending" : "Mean-reverting", spot: quote.price, flip: gex.flip, distToFlipPct: dist,
        changePct: quote.changePct, netGex: gex.netGex, reasons, chainSource: chain.source, quoteSource: quote.source,
      } satisfies Setup;
    }),
  );
  return out.sort((a, b) => b.score - a.score);
}
