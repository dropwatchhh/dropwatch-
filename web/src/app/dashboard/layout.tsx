import Link from "next/link";
import { Suspense } from "react";
import { BRAND } from "@/lib/brand";
import { getUser } from "@/lib/session";
import { signOut } from "@/lib/actions";
import { NavLinks } from "@/components/dash/NavLinks";

export default function DashboardLayout({ children }: LayoutProps<"/dashboard">) {
  return (
    <div className="min-h-screen md:flex">
      <aside className="hidden w-60 shrink-0 border-r border-line bg-surface p-4 md:block">
        <Link href="/" className="mb-6 block px-3 font-display text-xl">{BRAND}</Link>
        <NavLinks orientation="side" />
      </aside>
      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-30 border-b border-line bg-bg/85 backdrop-blur">
          <div className="flex h-14 items-center justify-between px-4 sm:px-6">
            <Link href="/" className="font-display text-lg md:hidden">{BRAND}</Link>
            <span className="hidden text-xs text-muted md:inline">Informational only. Not financial advice.</span>
            <Suspense fallback={<div className="h-8 w-24" />}>
              <UserMenu />
            </Suspense>
          </div>
          <div className="border-t border-line md:hidden">
            <NavLinks orientation="top" />
          </div>
        </header>
        <main className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6">{children}</main>
        <footer className="mx-auto max-w-6xl px-4 pb-10 text-xs text-muted sm:px-6">
          For information only. Not financial advice. Data is delayed, sample or simulated as labeled on each page.
        </footer>
      </div>
    </div>
  );
}

async function UserMenu() {
  const user = await getUser();
  return (
    <div className="flex items-center gap-3 text-sm">
      {user ? (
        <>
          <span className="hidden max-w-[12rem] truncate text-muted sm:inline">{user.email}</span>
          <form action={signOut}>
            <button className="rounded-full border border-white/20 px-3 py-1.5 hover:bg-white/5">Sign out</button>
          </form>
        </>
      ) : (
        <>
          <Link href="/sign-in" className="text-muted hover:text-fg">Sign in</Link>
          <Link href="/sign-up" className="rounded-full bg-accent px-3 py-1.5 font-semibold text-black">Start free</Link>
        </>
      )}
    </div>
  );
}
