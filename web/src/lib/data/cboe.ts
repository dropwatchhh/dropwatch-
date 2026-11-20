import { cached } from "./cache";
import type { OptionRow, OptionsChain } from "./types";

/**
 * CBOE delayed options JSON. OFF by default (OPTIONS_SOURCE=cboe to enable).
 * Terms-of-use risk: this is an undocumented public endpoint whose terms may restrict
 * automated access or redistribution. See README before enabling in production.
 */
export function cboeChain(symbol: string): Promise<OptionsChain> {
  return cached(`cboe:${symbol}`, 15 * 60_000, async () => {
    const res = await fetch(`https://cdn.cboe.com/api/global/delayed_quotes/options/${encodeURIComponent(symbol)}.json`, {
      headers: { "User-Agent": "Mozilla/5.0" }, cache: "no-store",
    });
    if (!res.ok) throw new Error(`cboe ${res.status}`);
    const j = (await res.json()) as { data: { current_price: number; options: { option: string; open_interest: number; iv: number }[] } };
    const spot = j.data.current_price;
    const rows: OptionRow[] = [];
    for (const o of j.data.options) {
      // OCC-style symbol: ROOT + YYMMDD + C/P + strike*1000 (8 digits)
      const m = /^([A-Z.]+)(\d{6})([CP])(\d{8})$/.exec(o.option);
      if (!m) continue;
      const d = m[2];
      rows.push({
        expiry: `20${d.slice(0, 2)}-${d.slice(2, 4)}-${d.slice(4, 6)}`,
        strike: parseInt(m[4], 10) / 1000, type: m[3] as "C" | "P", oi: o.open_interest ?? 0, iv: o.iv ?? 0,
      });
    }
    if (!rows.length) throw new Error("cboe empty");
    // Keep nearest expiries only to bound payload size.
    const exps = [...new Set(rows.map((r) => r.expiry))].sort().slice(0, 7);
    return { symbol, spot, asOf: Date.now(), rows: rows.filter((r) => exps.includes(r.expiry) && r.iv > 0), source: "cboe" as const };
  });
}
