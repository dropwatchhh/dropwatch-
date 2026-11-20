import Link from "next/link";
import { BRAND } from "@/lib/brand";
import { Button, Container, SectionHead, SimBadge } from "./ui";

type Mod = { title: string; blurb: string; live: boolean };
const modules: Mod[] = [
  { title: "Dealer positioning heatmap", blurb: "Net gamma by strike and expiry, with the flip level marked. Computed by us from delayed open interest.", live: true },
  { title: "Ranked trade setups", blurb: "Scans the watchlist and scores each name on positioning, trend and volatility so the strongest ideas float up.", live: true },
  { title: "Options flow", blurb: "A tape of large prints with side, size and a simple unusualness score. Demo feed for now.", live: false },
  { title: "Dark pool levels", blurb: "Clusters of off-exchange volume shown as support and resistance bands. Demo feed for now.", live: false },
  { title: "Algo signal feed", blurb: "A filterable stream of rule-based signals by ticker and strategy. Demo feed for now.", live: false },
  { title: "Charting", blurb: "Delayed candles with positioning levels drawn on the price axis, plus your own lines.", live: true },
  { title: "AI agent builder", blurb: "Describe a rule set in plain language and watch it run on paper. Never touches a real account.", live: false },
  { title: "Copy trading", blurb: "Follow a sample trader's paper portfolio and tune your own size and stop. Simulation only.", live: false },
];

export function Features() {
  return (
    <section className="py-20">
      <Container>
        <SectionHead id="features" lead="One workspace," accent="eight tools." sub="Each module shows whether it runs on delayed real data or on a clearly labeled simulation." />
        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {modules.map((m, i) => (
            <article key={m.title} className="flex flex-col rounded-2xl border border-line bg-surface p-5 transition hover:border-white/20">
              <span className="font-mono text-xs text-muted">0{i + 1}</span>
              <h3 className="mt-3 text-xl">{m.title}</h3>
              <p className="mt-2 flex-1 text-sm text-muted">{m.blurb}</p>
              <div className="mt-4">
                {m.live ? (
                  <span className="inline-flex items-center gap-1 rounded-full border border-teal-400/30 bg-teal-400/10 px-2 py-0.5 text-[11px] font-medium text-teal-300">
                    <span className="h-1.5 w-1.5 rounded-full bg-teal-300" />Delayed data
                  </span>
                ) : (
                  <SimBadge />
                )}
              </div>
            </article>
          ))}
        </div>
      </Container>
    </section>
  );
}

const steps = [
  ["Open the dashboard", "No account needed. Browse every module straight away."],
  ["Pick your tickers", "Search a symbol, add it to a watchlist and see its positioning map."],
  ["Save your setup", "Make a free account if you want your watchlists and settings kept."],
];

export function Steps() {
  return (
    <section className="py-20">
      <Container>
        <SectionHead lead="Up and running" accent="in three steps." sub="No card, no trial clock, no tiers." />
        <ol className="mt-12 grid gap-4 md:grid-cols-3">
          {steps.map(([t, d], i) => (
            <li key={t} className="rounded-2xl border border-line bg-surface p-6">
              <span className="flex h-9 w-9 items-center justify-center rounded-full border border-accent/40 font-mono text-sm text-accent">{i + 1}</span>
              <h3 className="mt-4 text-xl">{t}</h3>
              <p className="mt-2 text-sm text-muted">{d}</p>
            </li>
          ))}
        </ol>
      </Container>
    </section>
  );
}

const rows: [string, string, string, string][] = [
  ["Dealer positioning map", "Delayed", "Often paid add-on", "Rarely"],
  ["Options flow tape", "Simulated", "Paid", "Paid"],
  ["Dark pool levels", "Simulated", "Paid", "Paid"],
  ["Ranked setups", "Delayed", "Sometimes", "No"],
  ["Charting", "Delayed", "Included", "Included"],
  ["Algo signal feed", "Simulated", "Rarely", "Rarely"],
  ["AI agent builder (paper)", "Simulated", "No", "No"],
  ["Copy trading (paper)", "Simulated", "No", "No"],
  ["Mobile-friendly", "Yes", "Varies", "Varies"],
  ["Cost", "Free", "Monthly fee", "Monthly fee"],
];

export function Compare() {
  return (
    <section className="py-20">
      <Container>
        <SectionHead lead="How we" accent="compare." sub="A general comparison with typical paid tools. We label what is delayed or simulated rather than claiming parity." />
        <div className="mt-12 overflow-x-auto rounded-2xl border border-line">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="bg-surface-2 text-muted">
              <tr>
                <th className="px-4 py-3 font-medium">Capability</th>
                <th className="px-4 py-3 font-medium text-accent">{BRAND}</th>
                <th className="px-4 py-3 font-medium">Typical flow service</th>
                <th className="px-4 py-3 font-medium">Typical charting suite</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r[0]} className="border-t border-line">
                  <td className="px-4 py-3">{r[0]}</td>
                  <td className="px-4 py-3 text-fg">{r[1]}</td>
                  <td className="px-4 py-3 text-muted">{r[2]}</td>
                  <td className="px-4 py-3 text-muted">{r[3]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs text-muted">Generalizations about categories of tools, not claims about any named product.</p>
      </Container>
    </section>
  );
}

export function Mobile() {
  return (
    <section className="py-20">
      <Container>
        <div className="grid items-center gap-10 rounded-3xl border border-line bg-surface p-6 sm:p-12 md:grid-cols-2">
          <div>
            <h2 className="text-3xl sm:text-5xl">Built for the <span className="italic text-accent">small screen</span> too.</h2>
            <p className="mt-4 text-muted">
              The whole dashboard is responsive and installable as a home-screen app. Native store apps are on the
              roadmap and not available yet.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <span className="rounded-xl border border-line px-4 py-2 text-sm text-muted">App Store · coming later</span>
              <span className="rounded-xl border border-line px-4 py-2 text-sm text-muted">Google Play · coming later</span>
            </div>
          </div>
          <div className="mx-auto w-56 rounded-[2rem] border border-white/15 bg-bg p-3">
            <div className="rounded-[1.4rem] bg-surface-2 p-3">
              <div className="mb-3 flex items-center justify-between font-mono text-[10px] text-muted"><span>SPX</span><span className="text-pos">+0.42%</span></div>
              <div className="flex h-24 items-end gap-1">
                {[30, 45, 38, 55, 62, 50, 70, 66, 80].map((h, i) => (
                  <div key={i} className="flex-1 rounded-sm bg-accent/60" style={{ height: `${h}%` }} />
                ))}
              </div>
              <div className="mt-3 space-y-1.5">
                {[0, 1, 2].map((i) => <div key={i} className="h-3 rounded bg-white/5" />)}
              </div>
            </div>
          </div>
        </div>
      </Container>
    </section>
  );
}

export function Testimonial() {
  return (
    <section className="py-20">
      <Container className="max-w-3xl text-center">
        <blockquote className="font-display text-2xl leading-snug sm:text-4xl">
          &ldquo;I replaced three tabs with one page, and I like that it tells me which numbers are delayed and which are demo.&rdquo;
        </blockquote>
        <p className="mt-5 text-sm text-muted">Sample testimonial · placeholder text, not a real user</p>
      </Container>
    </section>
  );
}

const faqs: [string, string][] = [
  ["Is it really free?", "Yes. There are no paid tiers, no trial and no card. An account is optional and only saves your watchlists and settings."],
  ["Where does the data come from?", "Quotes and options chains come from free, delayed public sources. Dealer positioning is computed by us from open interest using Black-Scholes gamma. Delayed data is never real-time."],
  ["Which modules use simulated data?", "Options flow, dark pool levels, the algo signal feed, the AI agent builder and copy trading. There is no free source for these, so they run on generated demo data and say so on screen."],
  ["Can I trade from it?", "No. Nothing here connects to a brokerage or places orders. Copy trading and agents are paper simulations."],
  ["How accurate is the positioning map?", "It is an estimate. It assumes a fixed dealer-side convention and uses delayed open interest, so treat it as context, not a signal."],
  ["Do you give financial advice?", "No. Everything is informational only and not financial advice."],
];

export function Faq() {
  return (
    <section className="py-20">
      <Container className="max-w-3xl">
        <SectionHead id="faq" lead="Common" accent="questions." sub="Short answers, including the limits." />
        <div className="mt-10 divide-y divide-line rounded-2xl border border-line bg-surface">
          {faqs.map(([q, a]) => (
            <details key={q} className="group px-5 py-4">
              <summary className="flex cursor-pointer items-center justify-between gap-4 font-medium">
                {q}
                <span className="text-accent transition group-open:rotate-45" aria-hidden>+</span>
              </summary>
              <p className="mt-3 text-sm text-muted">{a}</p>
            </details>
          ))}
        </div>
      </Container>
    </section>
  );
}

export function ClosingCta() {
  return (
    <section className="py-20">
      <Container>
        <div className="rounded-3xl border border-line bg-[radial-gradient(ellipse_at_center,rgba(45,212,191,0.12),transparent_70%)] px-6 py-16 text-center">
          <h2 className="text-4xl sm:text-6xl">Start free. <span className="italic text-accent">Stay free.</span></h2>
          <p className="mx-auto mt-4 max-w-md text-muted">Open the dashboard now, or make an account to keep your watchlists.</p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Button href="/sign-up">Start free</Button>
            <Button href="/dashboard" variant="ghost">Explore the demo</Button>
          </div>
        </div>
      </Container>
    </section>
  );
}

export function Footer() {
  return (
    <footer className="mt-10 border-t border-line py-12 text-sm text-muted">
      <Container>
        <div className="flex flex-col justify-between gap-8 md:flex-row">
          <div>
            <p className="font-display text-xl text-fg">{BRAND}</p>
            <p className="mt-2 flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-pos" />Demo build</p>
          </div>
          <div className="grid grid-cols-2 gap-8 sm:grid-cols-3">
            <div className="space-y-2"><p className="text-fg">Product</p><a href="#features" className="block hover:text-fg">Features</a><Link href="/dashboard" className="block hover:text-fg">Dashboard</Link></div>
            <div className="space-y-2"><p className="text-fg">Account</p><Link href="/sign-in" className="block hover:text-fg">Sign in</Link><Link href="/sign-up" className="block hover:text-fg">Start free</Link></div>
            <div className="space-y-2"><p className="text-fg">Help</p><a href="#faq" className="block hover:text-fg">FAQ</a></div>
          </div>
        </div>
        <p className="mt-10 max-w-3xl text-xs leading-relaxed">
          For informational purposes only. Not financial advice, and not an offer or solicitation to buy or sell any
          security. {BRAND} is not a registered investment adviser or broker-dealer. Options involve significant risk
          and are not suitable for everyone. Past performance does not indicate future results. Market data is delayed
          and some modules use simulated data; neither should be relied on for trading decisions.
        </p>
        <p className="mt-4 text-xs">© 2026 {BRAND}</p>
      </Container>
    </footer>
  );
}
