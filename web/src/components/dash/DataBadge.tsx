import type { ReactNode } from "react";
import type { Source } from "@/lib/data/types";

const MAP: Record<Source, { label: string; cls: string }> = {
  simulated: { label: "Simulated data", cls: "border-amber-400/30 bg-amber-400/10 text-amber-300" },
  sample: { label: "Sample data", cls: "border-amber-400/30 bg-amber-400/10 text-amber-300" },
  finnhub: { label: "Delayed · Finnhub", cls: "border-teal-400/30 bg-teal-400/10 text-teal-300" },
  cboe: { label: "Delayed · CBOE", cls: "border-teal-400/30 bg-teal-400/10 text-teal-300" },
};

export function DataBadge({ source }: { source: Source }) {
  const m = MAP[source];
  return (
    <span className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-[11px] font-medium ${m.cls}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {m.label}
    </span>
  );
}

export function PageHead({ title, sub, source }: { title: string; sub: string; source: Source }) {
  return (
    <div className="mb-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-3xl sm:text-4xl">{title}</h1>
        <DataBadge source={source} />
      </div>
      <p className="mt-2 max-w-2xl text-sm text-muted">{sub}</p>
      {(source === "simulated" || source === "sample") && (
        <p className="mt-3 max-w-2xl rounded-lg border border-amber-400/20 bg-amber-400/5 px-3 py-2 text-xs text-amber-200/90">
          {source === "sample"
            ? "This view uses a stored sample options chain, not live market data. The math is real; the inputs are frozen."
            : "Everything on this page is generated demo data. It does not reflect any real market, trader or account."}
        </p>
      )}
    </div>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-2xl border border-line bg-surface ${className}`}>{children}</div>;
}
