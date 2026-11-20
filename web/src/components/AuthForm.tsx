"use client";
import Link from "next/link";
import { useActionState } from "react";
import { BRAND } from "@/lib/brand";
import type { FormState } from "@/lib/actions";

export function AuthForm({ mode, action }: { mode: "in" | "up"; action: (s: FormState, fd: FormData) => Promise<FormState> }) {
  const [state, formAction, pending] = useActionState(action, undefined);
  const up = mode === "up";
  const field = "mt-1 h-11 w-full rounded-lg border border-line bg-surface-2 px-3 text-fg outline-none focus:border-accent";
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-sm flex-col justify-center px-4 py-10">
      <Link href="/" className="font-display text-2xl">{BRAND}</Link>
      <h1 className="mt-6 text-3xl">{up ? "Create a free account" : "Welcome back"}</h1>
      <p className="mt-2 text-sm text-muted">
        {up ? "Optional. It only saves your watchlist and settings." : "Sign in to load your saved watchlist and settings."}
      </p>
      <form action={formAction} className="mt-6 space-y-4">
        <label className="block text-sm">Email
          <input name="email" type="email" required autoComplete="email" className={field} />
        </label>
        <label className="block text-sm">Password
          <input name="password" type="password" required minLength={up ? 8 : undefined} autoComplete={up ? "new-password" : "current-password"} className={field} />
        </label>
        {state?.error && <p role="alert" className="text-sm text-neg">{state.error}</p>}
        <button disabled={pending} className="h-11 w-full rounded-full bg-accent font-semibold text-black disabled:opacity-60">
          {pending ? "Please wait…" : up ? "Create account" : "Sign in"}
        </button>
      </form>
      <p className="mt-6 text-sm text-muted">
        {up ? <>Already have one? <Link href="/sign-in" className="text-accent">Sign in</Link></> : <>New here? <Link href="/sign-up" className="text-accent">Create an account</Link></>}
        {" · "}<Link href="/dashboard" className="text-accent">Skip, use the demo</Link>
      </p>
    </main>
  );
}
