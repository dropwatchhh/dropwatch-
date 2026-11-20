import Link from "next/link";
import { Card, DataBadge, PageHead } from "@/components/dash/DataBadge";
import { computeGex } from "@/lib/data/gex";
import { provider } from "@/lib/data";
import { SYMBOLS } from "@/lib/data/types";
import { compact, pct, usd } from "@/lib/format";
import { getWatchlist, toggleWatch } from "@/lib/actions";
import { getUser } from "@/lib/session";

export const metadata = { title: "Overview" };

export default async function Page() {
  const [user, watch] = await Promise.all([getUser(), getWatchlist()]);
  const rows = await Promise.all(
    SYMBOLS.map(async (symbol) => {
      const [q, chain] = await Promise.all([provider.getQuote(symbol), provider.getOptionsChain(symbol)]);
      return { q, chain, gex: computeGex(chain) };
    }),
  );
  const quoteSource = rows[0].q.source;
  const sorted = [...rows].sort((a, b) => Number(watch.includes(b.q.symbol)) - Number(watch.includes(a.q.symbol)));

  return (
    <>
      <PageHead title="Overview" source={quoteSource} sub="Quotes and a positioning snapshot for the tracked symbols. Each column carries its own data label." />
      <Card className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="text-xs text-muted">
            <tr className="border-b border-line">
              <th className="w-10 px-4 py-3" aria-label="Watch" />
              <th className="px-2 py-3 font-medium">Symbol</th>
              <th className="px-4 py-3 text-right font-medium">Price <DataBadge source={quoteSource} /></th>
              <th className="px-4 py-3 text-right font-medium">Change</th>
              <th className="px-4 py-3 text-right font-medium">Net gamma <DataBadge source={rows[0].chain.source} /></th>
              <th className="px-4 py-3 text-right font-medium">Flip</th>
              <th className="px-4 py-3 text-right font-medium" />
            </tr>
          </thead>
          <tbody>
            {sorted.map(({ q, gex }) => {
              const on = watch.includes(q.symbol);
              return (
                <tr key={q.symbol} className="border-b border-line last:border-0">
                  <td className="px-4 py-3">
                    {user ? (
                      <form action={toggleWatch.bind(null, q.symbol)}>
                        <button aria-label={on ? `Remove ${q.symbol} from watchlist` : `Add ${q.symbol} to watchlist`} className={on ? "text-amber-300" : "text-muted hover:text-fg"}>{on ? "★" : "☆"}</button>
                      </form>
                    ) : <span className="text-muted/40">☆</span>}
                  </td>
                  <td className="px-2 py-3 font-mono">{q.symbol}</td>
                  <td className="px-4 py-3 text-right font-mono">{usd(q.price)}</td>
                  <td className={`px-4 py-3 text-right font-mono ${q.changePct >= 0 ? "text-pos" : "text-neg"}`}>{pct(q.changePct)}</td>
                  <td className={`px-4 py-3 text-right font-mono ${gex.netGex >= 0 ? "text-pos" : "text-neg"}`}>{compact(gex.netGex)}</td>
                  <td className="px-4 py-3 text-right font-mono">{gex.flip ?? "n/a"}</td>
                  <td className="px-4 py-3 text-right"><Link href={`/dashboard/heatmap?symbol=${q.symbol}`} className="text-accent">Heatmap →</Link></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>
      {!user && (
        <p className="mt-4 text-sm text-muted">
          <Link href="/sign-up" className="text-accent">Create a free account</Link> to star symbols and keep a watchlist. Optional.
        </p>
      )}
      <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[["/dashboard/setups", "Trade setups", "Ranked by gamma regime and momentum"], ["/dashboard/charts", "Charts", "Candles with positioning levels"], ["/dashboard/flow", "Options flow", "Simulated tape"], ["/dashboard/agents", "AI agents", "Paper-only simulations"]].map(([h, t, d]) => (
          <Link key={h} href={h} className="rounded-2xl border border-line bg-surface p-4 transition hover:border-white/20">
            <p className="font-display text-lg">{t}</p>
            <p className="mt-1 text-sm text-muted">{d}</p>
          </Link>
        ))}
      </div>
    </>
  );
}
