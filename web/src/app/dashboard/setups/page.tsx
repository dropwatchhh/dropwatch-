import Link from "next/link";
import { Card, PageHead } from "@/components/dash/DataBadge";
import { getSetups } from "@/lib/data/setups";
import { compact, pct, usd } from "@/lib/format";

export const metadata = { title: "Trade setups" };

export default async function Page() {
  const setups = await getSetups();
  return (
    <>
      <PageHead
        title="Trade setups"
        source={setups[0].chainSource}
        sub="Symbols ranked by an illustrative score that blends gamma regime, distance to the flip level and day momentum. It describes conditions; it is not a recommendation."
      />
      <div className="space-y-3">
        {setups.map((s, i) => (
          <Card key={s.symbol} className="p-4 sm:p-5">
            <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
              <span className="font-mono text-sm text-muted">#{i + 1}</span>
              <div className="min-w-[6rem]">
                <p className="font-mono text-xl">{s.symbol}</p>
                <p className="font-mono text-sm text-muted">{usd(s.spot)} <span className={s.changePct >= 0 ? "text-pos" : "text-neg"}>{pct(s.changePct)}</span></p>
              </div>
              <div className="min-w-[8rem]">
                <p className="text-xs text-muted">Score</p>
                <div className="mt-1 flex items-center gap-2">
                  <div className="h-2 w-24 overflow-hidden rounded-full bg-white/10"><div className="h-full bg-accent" style={{ width: `${s.score}%` }} /></div>
                  <span className="font-mono text-sm">{s.score}</span>
                </div>
              </div>
              <div>
                <p className="text-xs text-muted">Regime</p>
                <p className={`text-sm ${s.regime === "Positive gamma" ? "text-pos" : "text-neg"}`}>{s.regime} · {s.bias}</p>
              </div>
              <div>
                <p className="text-xs text-muted">Net gamma</p>
                <p className="font-mono text-sm">{compact(s.netGex)}</p>
              </div>
              <Link href={`/dashboard/heatmap?symbol=${s.symbol}`} className="ml-auto text-sm text-accent">Heatmap →</Link>
            </div>
            <ul className="mt-3 list-disc space-y-0.5 pl-5 text-sm text-muted">
              {s.reasons.map((r) => <li key={r}>{r}</li>)}
            </ul>
          </Card>
        ))}
      </div>
    </>
  );
}
