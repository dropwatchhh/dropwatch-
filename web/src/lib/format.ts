export const usd = (n: number, d = 2) =>
  n.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: d, maximumFractionDigits: d });

export function compact(n: number) {
  const a = Math.abs(n);
  const s = n < 0 ? "-" : "";
  if (a >= 1e9) return `${s}$${(a / 1e9).toFixed(2)}B`;
  if (a >= 1e6) return `${s}$${(a / 1e6).toFixed(1)}M`;
  if (a >= 1e3) return `${s}$${(a / 1e3).toFixed(0)}K`;
  return `${s}$${a.toFixed(0)}`;
}

export const pct = (n: number) => `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
export const clock = (ms: number) => new Date(ms).toISOString().slice(11, 19) + " UTC";
export const int = (n: number) => n.toLocaleString("en-US");
