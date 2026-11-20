import { Card, PageHead } from "@/components/dash/DataBadge";
import { provider } from "@/lib/data";
import { clock, compact, int } from "@/lib/format";

export const metadata = { title: "Options flow" };

export default async function Page() {
  const prints = await provider.getFlow();
  return (
    <>
      <PageHead title="Options flow" source="simulated" sub="A tape of large option prints with side, size, premium and an unusualness score. No free real-time source exists, so this is generated." />
      <Card className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="text-xs text-muted">
            <tr className="border-b border-line">
              {["Time", "Symbol", "Contract", "Side", "Size", "Premium", "Score"].map((h, i) => (
                <th key={h} className={`px-4 py-3 font-medium ${i > 3 ? "text-right" : ""}`}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {prints.map((p) => (
              <tr key={p.id} className="border-b border-line last:border-0">
                <td className="px-4 py-2.5 font-mono text-xs text-muted">{clock(p.time)}</td>
                <td className="px-4 py-2.5 font-mono">{p.symbol}</td>
                <td className={`px-4 py-2.5 font-mono ${p.type === "C" ? "text-pos" : "text-neg"}`}>{p.strike}{p.type} · {p.expiry.slice(5)}</td>
                <td className="px-4 py-2.5">{p.side}</td>
                <td className="px-4 py-2.5 text-right font-mono">{int(p.size)}</td>
                <td className="px-4 py-2.5 text-right font-mono">{compact(p.premium)}</td>
                <td className="px-4 py-2.5 text-right font-mono">{p.score}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </>
  );
}
