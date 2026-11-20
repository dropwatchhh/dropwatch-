import { connection } from "next/server";
import { cboeChain } from "./cboe";
import { finnhubCandles, finnhubQuote, hasFinnhub } from "./finnhub";
import * as sim from "./simulated";
import type { DataProvider } from "./types";

/**
 * Default provider: Finnhub quotes/candles when FINNHUB_API_KEY is set (else labeled sample data),
 * stored sample options chain (or CBOE delayed when OPTIONS_SOURCE=cboe), simulated everything else.
 * Every result carries a `source` so the UI can label it. Swap this object to plug in real feeds.
 */
export const provider: DataProvider = {
  async getQuote(symbol) {
    await connection();
    if (hasFinnhub()) { try { return await finnhubQuote(symbol); } catch {} }
    return sim.simQuote(symbol);
  },
  async getCandles(symbol) {
    if (hasFinnhub()) { try { return await finnhubCandles(symbol); } catch {} }
    return sim.simCandles(symbol);
  },
  async getOptionsChain(symbol) {
    if (process.env.OPTIONS_SOURCE === "cboe") { try { return await cboeChain(symbol); } catch {} }
    return sim.sampleChain(symbol);
  },
  async getFlow() { await connection(); return sim.simFlow(); },
  async getDarkPool() { return sim.simDarkPool(); },
  async getSignals() { await connection(); return sim.simSignals(); },
  async getAgents() { return sim.simAgents(); },
  async getTraders() { return sim.simTraders(); },
};
