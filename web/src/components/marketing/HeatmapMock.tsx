// Decorative, deterministic mock of a dealer-gamma heatmap. Not real data.
function val(r: number, c: number) {
  const x = Math.sin(r * 12.9898 + c * 78.233) * 43758.5453;
  const noise = x - Math.floor(x);
  const peak = Math.exp(-Math.pow((r - 6) / 2.6, 2)) * Math.exp(-Math.pow((c - 2) / 2.2, 2));
  const sign = r < 6 ? -1 : 1;
  return sign * (peak * 0.9 + noise * 0.25);
}
const ROWS = 13;
const COLS = 7;
const strikes = Array.from({ length: ROWS }, (_, i) => 5900 - i * 10);
const exps = ["0DTE", "1D", "2D", "3D", "1W", "2W", "1M"];

export function HeatmapMock() {
  return (
    <div className="rounded-2xl border border-line bg-surface p-3 shadow-2xl shadow-teal-500/5 sm:p-4" aria-label="Illustrative heatmap mock-up">
      <div className="mb-3 flex items-center justify-between gap-2 text-xs text-muted">
        <div className="flex items-center gap-2">
          <span className="font-mono text-fg">SPX</span>
          <span>Net gamma by strike</span>
        </div>
        <span className="rounded-full border border-amber-400/30 bg-amber-400/10 px-2 py-0.5 text-[11px] text-amber-300">Illustration</span>
      </div>
      <div className="grid gap-[3px]" style={{ gridTemplateColumns: `auto repeat(${COLS}, minmax(0,1fr))` }}>
        <div />
        {exps.map((e) => (
          <div key={e} className="pb-1 text-center font-mono text-[10px] text-muted">{e}</div>
        ))}
        {strikes.map((s, r) => (
          <Row key={s} s={s} r={r} />
        ))}
      </div>
    </div>
  );
}

function Row({ s, r }: { s: number; r: number }) {
  const flip = r === 6;
  return (
    <>
      <div className={`pr-2 text-right font-mono text-[10px] leading-5 sm:text-[11px] ${flip ? "text-accent" : "text-muted"}`}>{s}</div>
      {exps.map((_, c) => {
        const v = val(r, c);
        const a = Math.min(0.9, Math.abs(v));
        const bg = v >= 0 ? `rgba(45,212,191,${a})` : `rgba(251,113,133,${a})`;
        return <div key={c} className={`h-5 rounded-[3px] ${flip ? "ring-1 ring-white/30" : ""}`} style={{ background: bg }} />;
      })}
    </>
  );
}
