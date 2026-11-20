import { Card, PageHead } from "@/components/dash/DataBadge";
import { provider } from "@/lib/data";
import { pct } from "@/lib/format";

export const metadata = { title: "AI agents" };

export default async function Page() {
  const agents = await provider.getAgents();
  return (
    <>
      <PageHead title="AI agent builder" source="simulated" sub="Describe a rule set and watch it run on paper. Agents here are static demos: they never touch a real account and nothing is executed." />
      <Card className="mb-6 p-4">
        <label htmlFor="rule" className="text-sm text-muted">Describe a rule (demo, not wired up)</label>
        <textarea id="rule" disabled rows={3} placeholder="e.g. Fade moves away from the flip level when net gamma is positive" className="mt-2 w-full rounded-lg border border-line bg-surface-2 p-3 text-sm opacity-70" />
        <button disabled className="mt-3 h-10 cursor-not-allowed rounded-full border border-line px-5 text-sm text-muted">Build agent · coming later</button>
      </Card>
      <div className="grid gap-4 md:grid-cols-3">
        {agents.map((a) => (
          <Card key={a.id} className="p-4">
            <div className="flex items-center justify-between">
              <p className="font-display text-lg">{a.name}</p>
              <span className="rounded-full border border-line px-2 py-0.5 text-[11px] text-muted">{a.status}</span>
            </div>
            <p className="mt-2 text-sm text-muted">{a.rule}</p>
            <p className="mt-4 font-mono text-sm">
              <span className={a.pnlPct >= 0 ? "text-pos" : "text-neg"}>{pct(a.pnlPct)}</span>
              <span className="text-muted"> · {a.trades} paper trades</span>
            </p>
          </Card>
        ))}
      </div>
    </>
  );
}
