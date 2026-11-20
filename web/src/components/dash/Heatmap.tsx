"use client";
import { useState } from "react";
import type { GexResult } from "@/lib/data/gex";
import { compact, usd } from "@/lib/format";

const shortDate = (iso: string) => iso.slice(5).replace("-", "/");

function cellColor(v: number, max: number) {
  if (!max || v === 0) return "rgba(255,255,255,0.03)";
  const a = Math.min(0.95, 0.08 + Math.pow(Math.abs(v) / max, 0.6) * 0.87);
  return v > 0 ? `rgba(45,212,191,${a})` : `rgba(251,113,133,${a})`;
}

export function Heatmap({ gex }: { gex: GexResult }) {
  const [sel, setSel] = useState<{ strike: number; expiry: string; gex: number } | null>(null);
  const cellMap = new Map(gex.cells.map((c) => [`${c.strike}|${c.expiry}`, c.gex]));
  const maxAgg = Math.max(...gex.byStrike.map((b) => Math.abs(b.gex)), 1);
  const aggMap = new Map(gex.byStrike.map((b) => [b.strike, b.gex]));
  // The strike closest to spot gets the spot marker.
  const spotStrike = gex.strikes.reduce((a, b) => (Math.abs(b - gex.spot) < Math.abs(a - gex.spot) ? b : a), gex.strikes[0]);
  const cols = `3.5rem repeat(${gex.expiries.length}, minmax(2.25rem, 1fr)) 4.5rem`;

  return (
    <div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <Stat label="Spot" value={usd(gex.spot)} />
        <Stat label="Net gamma / 1%" value={compact(gex.netGex)} tone={gex.netGex >= 0 ? "pos" : "neg"} />
        <Stat label="Flip level" value={gex.flip ? String(gex.flip) : "n/a"} />
        <Stat label="Call wall" value={gex.callWall ? String(gex.callWall) : "n/a"} tone="pos" />
        <Stat label="Put wall" value={gex.putWall ? String(gex.putWall) : "n/a"} tone="neg" />
      </div>

      <div className="mt-5 overflow-x-auto rounded-2xl border border-line bg-surface p-3 sm:p-4">
        <div role="grid" aria-label={`${gex.symbol} gamma exposure by strike and expiry`} className="grid min-w-[30rem] gap-[3px]" style={{ gridTemplateColumns: cols }}>
          <div />
          {gex.expiries.map((e) => (
            <div key={e} className="pb-1 text-center font-mono text-[10px] text-muted">{shortDate(e)}</div>
          ))}
          <div className="pb-1 text-center font-mono text-[10px] text-muted">Net</div>

          {gex.strikes.map((s) => {
            const isSpot = s === spotStrike;
            const isFlip = s === gex.flip;
            return (
              <Row key={s}>
                <div className={`flex items-center justify-end gap-1 pr-2 font-mono text-[11px] ${isSpot ? "font-semibold text-fg" : isFlip ? "text-accent" : "text-muted"}`}>
                  {isSpot && <span className="text-[9px] text-amber-300" aria-label="spot">●</span>}
                  {s}
                </div>
                {gex.expiries.map((e) => {
                  const v = cellMap.get(`${s}|${e}`) ?? 0;
                  const active = sel?.strike === s && sel.expiry === e;
                  return (
                    <button
                      key={e}
                      type="button"
                      role="gridcell"
                      aria-label={`Strike ${s}, expiry ${e}, gamma ${compact(v)}`}
                      onMouseEnter={() => setSel({ strike: s, expiry: e, gex: v })}
                      onFocus={() => setSel({ strike: s, expiry: e, gex: v })}
                      onClick={() => setSel({ strike: s, expiry: e, gex: v })}
                      className={`h-6 rounded-[3px] outline-none transition ${active ? "ring-2 ring-white" : isSpot ? "ring-1 ring-amber-300/50" : isFlip ? "ring-1 ring-accent/60" : ""}`}
                      style={{ background: cellColor(v, gex.maxAbs) }}
                    />
                  );
                })}
                <div className="flex h-6 items-center">
                  <div
                    className="h-3 rounded-sm"
                    style={{
                      width: `${(Math.abs(aggMap.get(s) ?? 0) / maxAgg) * 100}%`,
                      minWidth: 2,
                      background: (aggMap.get(s) ?? 0) >= 0 ? "var(--pos)" : "var(--neg)",
                    }}
                  />
                </div>
              </Row>
            );
          })}
        </div>
      </div>

      <div className="mt-3 flex min-h-12 flex-wrap items-center justify-between gap-3 rounded-xl border border-line bg-surface-2 px-4 py-3 text-sm" aria-live="polite">
        {sel ? (
          <>
            <span className="font-mono">{gex.symbol} {sel.strike} · exp {sel.expiry}</span>
            <span className={sel.gex >= 0 ? "text-pos" : "text-neg"}>
              {compact(sel.gex)} gamma per 1% move · {sel.gex >= 0 ? "dealers long gamma here (dampens moves)" : "dealers short gamma here (amplifies moves)"}
            </span>
          </>
        ) : (
          <span className="text-muted">Hover, tap or focus a cell for its value.</span>
        )}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-muted">
        <span className="flex items-center gap-1.5"><i className="h-3 w-3 rounded-sm bg-pos" /> Positive gamma</span>
        <span className="flex items-center gap-1.5"><i className="h-3 w-3 rounded-sm bg-neg" /> Negative gamma</span>
        <span className="flex items-center gap-1.5"><span className="text-amber-300">●</span> Nearest strike to spot</span>
        <span className="flex items-center gap-1.5"><i className="h-3 w-3 rounded-sm ring-1 ring-accent/60" /> Flip level</span>
      </div>
    </div>
  );
}

function Row({ children }: { children: React.ReactNode }) {
  return <div role="row" className="contents">{children}</div>;
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: "pos" | "neg" }) {
  return (
    <div className="rounded-xl border border-line bg-surface p-3">
      <p className="text-[11px] uppercase tracking-wide text-muted">{label}</p>
      <p className={`mt-1 font-mono text-lg ${tone === "pos" ? "text-pos" : tone === "neg" ? "text-neg" : ""}`}>{value}</p>
    </div>
  );
}
