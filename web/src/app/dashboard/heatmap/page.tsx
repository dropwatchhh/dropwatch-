import Link from "next/link";
import { Heatmap } from "@/components/dash/Heatmap";
import { PageHead } from "@/components/dash/DataBadge";
import { computeGex } from "@/lib/data/gex";
import { provider } from "@/lib/data";
import { SYMBOLS, isSym } from "@/lib/data/types";
import { getDefaultSymbol } from "@/lib/actions";

export const metadata = { title: "Positioning heatmap" };

export default async function Page({ searchParams }: PageProps<"/dashboard/heatmap">) {
  const sp = await searchParams;
  const raw = typeof sp.symbol === "string" ? sp.symbol.toUpperCase() : await getDefaultSymbol();
  const symbol = isSym(raw) ? raw : "SPY";
  const chain = await provider.getOptionsChain(symbol);
  const gex = computeGex(chain);

  return (
    <>
      <PageHead
        title="Positioning heatmap"
        source={chain.source}
        sub="Estimated dealer gamma exposure by strike and expiry, computed from open interest with Black-Scholes gamma. Assumes dealers are long calls and short puts, so treat it as context, not a signal."
      />
      <div className="mb-5 flex flex-wrap gap-2" role="tablist" aria-label="Symbol">
        {SYMBOLS.map((s) => (
          <Link
            key={s}
            href={`/dashboard/heatmap?symbol=${s}`}
            role="tab"
            aria-selected={s === symbol}
            className={`rounded-full border px-4 py-1.5 font-mono text-sm ${s === symbol ? "border-accent bg-accent/15 text-accent" : "border-line text-muted hover:text-fg"}`}
          >
            {s}
          </Link>
        ))}
      </div>
      <Heatmap gex={gex} />
      <details className="mt-6 text-sm text-muted">
        <summary className="cursor-pointer text-fg">How this is calculated</summary>
        <p className="mt-2 max-w-2xl">
          For each option: gamma × open interest × 100 × spot² × 1%. Calls count positive, puts negative. Cells are summed by
          strike and expiry within ±8% of spot. The flip level is the strike nearest spot where cumulative gamma changes sign.
          The same function runs on the stored sample chain and on the optional CBOE feed.
        </p>
      </details>
    </>
  );
}
