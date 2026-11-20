import { Button, Container } from "./ui";
import { HeatmapMock } from "./HeatmapMock";

const badges = ["Free forever", "Delayed quotes, clearly labeled", "No card required", "Informational only"];
const tickers = [["SPX", "+0.42%"], ["NDX", "+0.61%"], ["SPY", "+0.40%"], ["QQQ", "+0.58%"], ["RUT", "-0.12%"], ["VIX", "-2.30%"]];

export function Hero() {
  return (
    <section className="relative overflow-hidden pb-16 pt-14 sm:pt-20">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-96 bg-[radial-gradient(ellipse_at_top,rgba(45,212,191,0.14),transparent_70%)]" />
      <Container className="relative">
        <div className="mx-auto max-w-3xl text-center">
          <h1 className="text-5xl leading-[1.05] sm:text-7xl">
            See where the dealers are <span className="italic text-accent">leaning.</span>
          </h1>
          <p className="mx-auto mt-6 max-w-xl text-lg text-muted">
            A free workspace for dealer positioning, ranked setups, flow and charts. Gamma is computed from delayed
            options chains, and anything we can&apos;t source for free is labeled as simulated.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Button href="/sign-up">Start free</Button>
            <Button href="/dashboard" variant="ghost">Open the demo dashboard</Button>
          </div>
          <ul className="mt-8 flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-sm text-muted">
            {badges.map((b) => (
              <li key={b} className="flex items-center gap-1.5">
                <span className="text-accent" aria-hidden>✓</span>
                {b}
              </li>
            ))}
          </ul>
        </div>
        <div className="mt-10 overflow-x-auto">
          <div className="mx-auto flex min-w-max items-center justify-center gap-6 font-mono text-xs text-muted">
            {tickers.map(([t, c]) => (
              <span key={t}>
                <span className="text-fg">{t}</span>{" "}
                <span className={c.startsWith("-") ? "text-neg" : "text-pos"}>{c}</span>
              </span>
            ))}
            <span className="rounded-full border border-amber-400/30 px-2 py-0.5 text-[10px] text-amber-300">sample ticker</span>
          </div>
        </div>
        <div className="mx-auto mt-8 max-w-4xl">
          <HeatmapMock />
        </div>
      </Container>
    </section>
  );
}
