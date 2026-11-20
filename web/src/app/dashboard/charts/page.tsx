import Link from "next/link";
import { Card, DataBadge, PageHead } from "@/components/dash/DataBadge";
import { computeGex } from "@/lib/data/gex";
import { provider } from "@/lib/data";
import { SYMBOLS, isSym } from "@/lib/data/types";
import { usd } from "@/lib/format";

export const metadata = { title: "Charts" };

export default async function Page({ searchParams }: PageProps<"/dashboard/charts">) {
  const sp = await searchParams;
  const raw = typeof sp.symbol === "string" ? sp.symbol.toUpperCase() : "SPY";
  const symbol = isSym(raw) ? raw : "SPY";
  const [data, chain] = await Promise.all([provider.getCandles(symbol), provider.getOptionsChain(symbol)]);
  const gex = computeGex(chain);
  const cs = data.candles.slice(-80);

  const W = 900, H = 380, PAD = { l: 8, r: 64, t: 12, b: 24 };
  const lo = Math.min(...cs.map((c) => c.l)), hi = Math.max(...cs.map((c) => c.h));
  const span = hi - lo || 1;
  const y = (p: number) => PAD.t + (1 - (p - lo + span * 0.05) / (span * 1.1)) * (H - PAD.t - PAD.b);
  const step = (W - PAD.l - PAD.r) / cs.length;
  // Overlay levels only when they sit on the same price scale as the candles.
  const levels = ([["Flip", gex.flip], ["Call wall", gex.callWall], ["Put wall", gex.putWall]] as const)
    .filter(([, v]) => v !== null && v >= lo * 0.97 && v <= hi * 1.03) as [string, number][];
  const ticks = Array.from({ length: 5 }, (_, i) => lo + (span * i) / 4);

  return (
    <>
      <PageHead title="Charts" source={data.source} sub="Daily candles with positioning levels from the heatmap drawn on the price axis." />
      <div className="mb-5 flex flex-wrap gap-2">
        {SYMBOLS.map((s) => (
          <Link key={s} href={`/dashboard/charts?symbol=${s}`} className={`rounded-full border px-4 py-1.5 font-mono text-sm ${s === symbol ? "border-accent bg-accent/15 text-accent" : "border-line text-muted hover:text-fg"}`}>{s}</Link>
        ))}
      </div>
      <Card className="p-3 sm:p-4">
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${symbol} daily candlestick chart`} className="h-auto w-full">
          {ticks.map((t) => (
            <g key={t}>
              <line x1={PAD.l} x2={W - PAD.r} y1={y(t)} y2={y(t)} stroke="rgba(255,255,255,0.06)" />
              <text x={W - PAD.r + 6} y={y(t) + 4} fontSize="11" fill="#a8a8b0" fontFamily="monospace">{t.toFixed(0)}</text>
            </g>
          ))}
          {cs.map((c, i) => {
            const x = PAD.l + i * step + step / 2;
            const up = c.c >= c.o;
            const col = up ? "#2dd4bf" : "#fb7185";
            return (
              <g key={c.t}>
                <line x1={x} x2={x} y1={y(c.h)} y2={y(c.l)} stroke={col} strokeWidth="1" />
                <rect x={x - step * 0.3} width={step * 0.6} y={y(Math.max(c.o, c.c))} height={Math.max(1, Math.abs(y(c.o) - y(c.c)))} fill={col} />
              </g>
            );
          })}
          {levels.map(([name, v]) => (
            <g key={name}>
              <line x1={PAD.l} x2={W - PAD.r} y1={y(v)} y2={y(v)} stroke="#fbbf24" strokeDasharray="4 4" strokeOpacity="0.7" />
              <text x={W - PAD.r - 4} y={y(v) - 4} textAnchor="end" fontSize="11" fill="#fbbf24">{name} {v}</text>
            </g>
          ))}
        </svg>
        <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-muted">
          <span>Last close {usd(cs[cs.length - 1].c)}</span>
          <span>Levels from</span><DataBadge source={chain.source} />
          {levels.length === 0 && <span>(levels hidden: off this price range)</span>}
        </div>
      </Card>
    </>
  );
}
