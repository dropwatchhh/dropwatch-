"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

export const NAV = [
  { href: "/dashboard", label: "Overview" },
  { href: "/dashboard/heatmap", label: "Positioning heatmap" },
  { href: "/dashboard/setups", label: "Trade setups" },
  { href: "/dashboard/flow", label: "Options flow" },
  { href: "/dashboard/darkpool", label: "Dark pool" },
  { href: "/dashboard/signals", label: "Algo signals" },
  { href: "/dashboard/charts", label: "Charts" },
  { href: "/dashboard/agents", label: "AI agents" },
  { href: "/dashboard/copy", label: "Copy trading" },
  { href: "/dashboard/settings", label: "Settings" },
];

export function NavLinks({ orientation }: { orientation: "side" | "top" }) {
  const path = usePathname();
  return (
    <nav aria-label="Dashboard" className={orientation === "side" ? "flex flex-col gap-1" : "flex gap-2 overflow-x-auto px-4 py-2"}>
      {NAV.map((n) => {
        const active = path === n.href;
        return (
          <Link
            key={n.href}
            href={n.href}
            aria-current={active ? "page" : undefined}
            className={`whitespace-nowrap rounded-lg px-3 py-2 text-sm transition ${
              active ? "bg-accent/15 text-accent" : "text-muted hover:bg-white/5 hover:text-fg"
            } ${orientation === "top" ? "border border-line" : ""}`}
          >
            {n.label}
          </Link>
        );
      })}
    </nav>
  );
}
