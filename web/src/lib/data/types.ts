export type Source = "sample" | "cboe" | "finnhub" | "simulated";

export type Quote = { symbol: string; price: number; change: number; changePct: number; asOf: number; source: Source };
export type Candle = { t: number; o: number; h: number; l: number; c: number; v: number };
export type Candles = { symbol: string; candles: Candle[]; source: Source };

export type OptionRow = { expiry: string; strike: number; type: "C" | "P"; oi: number; iv: number };
export type OptionsChain = { symbol: string; spot: number; asOf: number; rows: OptionRow[]; source: Source };

export type FlowPrint = { id: string; time: number; symbol: string; type: "C" | "P"; strike: number; expiry: string; side: "Ask" | "Bid" | "Mid"; size: number; premium: number; score: number };
export type DarkPoolLevel = { symbol: string; price: number; shares: number; kind: "Support" | "Resistance" | "Magnet" };
export type Signal = { id: string; time: number; symbol: string; strategy: string; direction: "Long" | "Short"; strength: number };
export type AgentRun = { id: string; name: string; rule: string; pnlPct: number; trades: number; status: "Running" | "Paused" };
export type Trader = { id: string; handle: string; style: string; return30d: number; winRate: number; followers: number };

/** The single seam where real feeds can be swapped in. */
export interface DataProvider {
  getQuote(symbol: string): Promise<Quote>;
  getCandles(symbol: string): Promise<Candles>;
  getOptionsChain(symbol: string): Promise<OptionsChain>;
  getFlow(): Promise<FlowPrint[]>;
  getDarkPool(): Promise<DarkPoolLevel[]>;
  getSignals(): Promise<Signal[]>;
  getAgents(): Promise<AgentRun[]>;
  getTraders(): Promise<Trader[]>;
}

export const SYMBOLS = ["SPY", "QQQ", "AAPL", "NVDA", "TSLA"] as const;
export type Sym = (typeof SYMBOLS)[number];
export const isSym = (s: string): s is Sym => (SYMBOLS as readonly string[]).includes(s);
