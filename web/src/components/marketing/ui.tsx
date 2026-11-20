import Link from "next/link";
import type { ReactNode } from "react";

export function Container({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`mx-auto w-full max-w-6xl px-4 sm:px-6 ${className}`}>{children}</div>;
}

export function Button({ href, children, variant = "primary" }: { href: string; children: ReactNode; variant?: "primary" | "ghost" }) {
  const base = "inline-flex h-11 items-center justify-center rounded-full px-5 text-[15px] font-semibold transition";
  const styles =
    variant === "primary"
      ? "bg-accent text-black hover:brightness-110"
      : "border border-white/20 text-fg hover:bg-white/5";
  return <Link href={href} className={`${base} ${styles}`}>{children}</Link>;
}

export function SimBadge({ label = "Simulated data" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-amber-400/30 bg-amber-400/10 px-2 py-0.5 text-[11px] font-medium text-amber-300">
      <span className="h-1.5 w-1.5 rounded-full bg-amber-300" />
      {label}
    </span>
  );
}

export function SectionHead({ id, lead, accent, sub }: { id?: string; lead: string; accent: string; sub: string }) {
  return (
    <div id={id} className="mx-auto max-w-2xl scroll-mt-24 text-center">
      <h2 className="text-3xl sm:text-5xl">
        {lead} <span className="italic text-accent">{accent}</span>
      </h2>
      <p className="mt-4 text-muted">{sub}</p>
    </div>
  );
}
