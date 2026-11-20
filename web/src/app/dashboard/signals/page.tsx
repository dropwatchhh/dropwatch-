import { Card, PageHead } from "@/components/dash/DataBadge";
import { provider } from "@/lib/data";
import { clock } from "@/lib/format";

export const metadata = { title: "Algo signals" };

export default async function Page() {
  const signals = await provider.getSignals();
  return (
    <>
      <PageHead title="Algo signal feed" source="simulated" sub="A stream of rule-based signals by ticker and strategy. Generated for demonstration; these are not real algorithm outputs." />
      <Card className="divide-y divide-line">
        {signals.map((s) => (
          <div key={s.id} className="flex flex-wrap items-center gap-x-5 gap-y-1 px-4 py-3 text-sm">
            <span className="w-24 font-mono text-xs text-muted">{clock(s.time)}</span>
            <span className="w-14 font-mono">{s.symbol}</span>
            <span className="min-w-[8rem] flex-1">{s.strategy}</span>
            <span className={s.direction === "Long" ? "text-pos" : "text-neg"}>{s.direction}</span>
            <span className="w-16 text-right font-mono">{s.strength}</span>
          </div>
        ))}
      </Card>
    </>
  );
}
