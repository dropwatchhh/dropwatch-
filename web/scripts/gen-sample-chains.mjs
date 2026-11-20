// One-off generator for the stored sample option chains. Output is static, made-up data.
import { writeFileSync } from "node:fs";
const specs = { SPY: [590, 1], QQQ: [510, 1], AAPL: [230, 2.5], NVDA: [140, 2.5], TSLA: [320, 5] };
let seed = 7;
const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
const asOf = Date.parse("2026-11-20T20:00:00Z");
const exps = [0, 1, 2, 4, 7, 14, 30].map((d) => new Date(asOf + d * 86400000).toISOString().slice(0, 10));
const out = {};
for (const [sym, [spot, step]] of Object.entries(specs)) {
  const rows = [];
  const stepEff = sym === "SPY" || sym === "QQQ" ? 5 : Math.max(1, Math.round(spot * 0.01));
  const base = Math.round(spot / stepEff) * stepEff;
  for (let k = -20; k <= 20; k++) {
    const strike = base + k * stepEff;
    const m = Math.abs(strike - spot) / spot;
    for (const [ei, e] of exps.entries()) {
      for (const type of ["C", "P"]) {
        const otm = type === "C" ? strike >= spot : strike <= spot;
        const wall = Math.exp(-Math.pow((strike - (type === "C" ? spot * 1.02 : spot * 0.97)) / (spot * 0.012), 2));
        const oi = Math.round((2000 + 90000 * Math.exp(-m * 40) * (otm ? 1 : 0.35) + 160000 * wall * (otm ? 1 : 0.4)) * (1 + rnd() * 0.5) / (1 + ei * 0.35));
        const iv = 0.16 + m * 0.9 + (type === "P" ? 0.03 : 0) + ei * -0.004 + (sym === "SPY" || sym === "QQQ" ? 0 : 0.14);
        rows.push({ expiry: e, strike, type, oi, iv: +iv.toFixed(4) });
      }
    }
  }
  out[sym] = { symbol: sym, spot, asOf, rows, source: "sample" };
}
writeFileSync(new URL("../src/lib/data/sample/chains.json", import.meta.url), JSON.stringify(out));
console.log("ok", Object.values(out).map((c) => c.rows.length));
