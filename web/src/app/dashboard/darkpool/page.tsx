import { Card, PageHead } from "@/components/dash/DataBadge";
import { provider } from "@/lib/data";
import { SYMBOLS } from "@/lib/data/types";
import { int, usd } from "@/lib/format";

export const metadata = { title: "Dark pool levels" };

const tone = { Support: "text-pos", Resistance: "text-neg", Magnet: "text-amber-300" } as const;

export default async function Page() {
  const levels = await provider.getDarkPool();
  return (
    <>
      <PageHead title="Dark pool levels" source="simulated" sub="Clusters of off-exchange volume shown as support, resistance and magnet levels. Real prints are a paid feed, so these are generated." />
      <div className="grid gap-4 md:grid-cols-2">
        {SYMBOLS.map((s) => (
          <Card key={s} className="p-4">
            <p className="font-mono text-lg">{s}</p>
            <ul className="mt-3 divide-y divide-line text-sm">
              {levels.filter((l) => l.symbol === s).sort((a, b) => b.price - a.price).map((l) => (
                <li key={l.kind} className="flex items-center justify-between py-2">
                  <span className={tone[l.kind]}>{l.kind}</span>
                  <span className="font-mono">{usd(l.price)}</span>
                  <span className="font-mono text-muted">{int(l.shares)} sh</span>
                </li>
              ))}
            </ul>
          </Card>
        ))}
      </div>
    </>
  );
}
