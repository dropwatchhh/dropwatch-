import Link from "next/link";
import { BRAND } from "@/lib/brand";
import { Button, Container } from "./ui";

export function PromoBanner() {
  return (
    <div className="border-b border-line bg-accent/10 px-4 py-2 text-center text-sm text-fg">
      Everything is free. No card, no paywall.{" "}
      <Link href="/sign-up" className="font-semibold text-accent underline-offset-4 hover:underline">Create an account</Link>{" "}
      only if you want to save watchlists.
    </div>
  );
}

export function Nav() {
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-bg/80 backdrop-blur">
      <Container className="flex h-16 items-center justify-between">
        <Link href="/" className="font-display text-xl tracking-tight">{BRAND}</Link>
        <nav className="hidden items-center gap-7 text-sm text-muted md:flex">
          <a href="#features" className="hover:text-fg">Features</a>
          <a href="#faq" className="hover:text-fg">FAQ</a>
        </nav>
        <div className="flex items-center gap-2 sm:gap-3">
          <Link href="/sign-in" className="px-2 text-sm text-muted hover:text-fg sm:px-3">Sign in</Link>
          <Button href="/sign-up">Start free</Button>
        </div>
      </Container>
      <Container className="flex h-10 items-center gap-6 border-t border-line text-sm text-muted md:hidden">
        <a href="#features" className="hover:text-fg">Features</a>
        <a href="#faq" className="hover:text-fg">FAQ</a>
      </Container>
    </header>
  );
}
