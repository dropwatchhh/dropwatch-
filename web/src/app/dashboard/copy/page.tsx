import { Card, PageHead } from "@/components/dash/DataBadge";
import { provider } from "@/lib/data";
import { int, pct } from "@/lib/format";

export const metadata = { title: "Copy trading" };

export default async function Page() {
  const traders = await provider.getTraders();
  return (
    <>
      <PageHead title="Copy trading" source="simulated" sub="Follow a sample trader's paper portfolio. No brokerage is connected and no orders are ever placed; all traders and results are invented." />
      <div className="grid gap-4 md:grid-cols-3">
        {traders.map((t) => (
          <Card key={t.id} className="p-4">
            <p className="font-mono">{t.handle}</p>
            <p className="text-sm text-muted">{t.style}</p>
            <dl className="mt-4 grid grid-cols-3 gap-2 text-sm">
              <div><dt className="text-xs text-muted">30d</dt><dd className={`font-mono ${t.return30d >= 0 ? "text-pos" : "text-neg"}`}>{pct(t.return30d)}</dd></div>
              <div><dt className="text-xs text-muted">Win rate</dt><dd className="font-mono">{t.winRate}%</dd></div>
              <div><dt className="text-xs text-muted">Followers</dt><dd className="font-mono">{int(t.followers)}</dd></div>
            </dl>
            <button disabled className="mt-4 h-9 w-full cursor-not-allowed rounded-full border border-line text-sm text-muted">Follow (paper) · coming later</button>
          </Card>
        ))}
      </div>
    </>
  );
}
