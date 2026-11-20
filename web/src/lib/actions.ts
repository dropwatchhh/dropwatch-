"use server";
import bcrypt from "bcryptjs";
import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { db } from "./db";
import { createSession, destroySession, getUser } from "./session";
import { isSym } from "./data/types";

export type FormState = { error?: string; ok?: string } | undefined;
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export async function signUp(_: FormState, fd: FormData): Promise<FormState> {
  const email = String(fd.get("email") ?? "").trim().toLowerCase();
  const password = String(fd.get("password") ?? "");
  if (!EMAIL.test(email)) return { error: "Enter a valid email address." };
  if (password.length < 8) return { error: "Password must be at least 8 characters." };
  const c = await db();
  const exists = await c.execute({ sql: "SELECT id FROM users WHERE email = ?", args: [email] });
  if (exists.rows.length) return { error: "An account with that email already exists." };
  const hash = await bcrypt.hash(password, 10);
  const r = await c.execute({ sql: "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)", args: [email, hash, Date.now()] });
  await createSession({ id: Number(r.lastInsertRowid), email });
  redirect("/dashboard");
}

export async function signIn(_: FormState, fd: FormData): Promise<FormState> {
  const email = String(fd.get("email") ?? "").trim().toLowerCase();
  const password = String(fd.get("password") ?? "");
  const c = await db();
  const r = await c.execute({ sql: "SELECT id, password_hash FROM users WHERE email = ?", args: [email] });
  const row = r.rows[0];
  const ok = row ? await bcrypt.compare(password, String(row.password_hash)) : false;
  if (!row || !ok) return { error: "Incorrect email or password." };
  await createSession({ id: Number(row.id), email });
  redirect("/dashboard");
}

export async function signOut() {
  await destroySession();
  redirect("/");
}

export async function toggleWatch(symbol: string) {
  const u = await getUser();
  if (!u || !isSym(symbol)) return;
  const c = await db();
  const has = await c.execute({ sql: "SELECT 1 FROM watchlist WHERE user_id = ? AND symbol = ?", args: [u.id, symbol] });
  if (has.rows.length) await c.execute({ sql: "DELETE FROM watchlist WHERE user_id = ? AND symbol = ?", args: [u.id, symbol] });
  else await c.execute({ sql: "INSERT INTO watchlist (user_id, symbol) VALUES (?, ?)", args: [u.id, symbol] });
  revalidatePath("/dashboard", "layout");
}

export async function saveSettings(_: FormState, fd: FormData): Promise<FormState> {
  const u = await getUser();
  if (!u) return { error: "Sign in to save settings." };
  const sym = String(fd.get("default_symbol") ?? "");
  if (!isSym(sym)) return { error: "Unknown symbol." };
  const c = await db();
  await c.execute({ sql: "INSERT INTO settings (user_id, default_symbol) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET default_symbol = excluded.default_symbol", args: [u.id, sym] });
  revalidatePath("/dashboard", "layout");
  return { ok: "Saved." };
}

export async function getWatchlist(): Promise<string[]> {
  const u = await getUser();
  if (!u) return [];
  const r = await (await db()).execute({ sql: "SELECT symbol FROM watchlist WHERE user_id = ? ORDER BY symbol", args: [u.id] });
  return r.rows.map((x) => String(x.symbol));
}

export async function getDefaultSymbol(): Promise<string> {
  const u = await getUser();
  if (!u) return "SPY";
  const r = await (await db()).execute({ sql: "SELECT default_symbol FROM settings WHERE user_id = ?", args: [u.id] });
  return r.rows[0] ? String(r.rows[0].default_symbol) : "SPY";
}
