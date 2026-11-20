import { createClient, type Client } from "@libsql/client";

let client: Client | null = null;
let ready: Promise<void> | null = null;

export async function db(): Promise<Client> {
  if (!client) {
    client = createClient({
      url: process.env.TURSO_DATABASE_URL || "file:local.db",
      authToken: process.env.TURSO_AUTH_TOKEN || undefined,
    });
  }
  if (!ready) {
    const c = client;
    ready = c.batch([
      "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, created_at INTEGER NOT NULL)",
      "CREATE TABLE IF NOT EXISTS watchlist (user_id INTEGER NOT NULL, symbol TEXT NOT NULL, PRIMARY KEY (user_id, symbol))",
      "CREATE TABLE IF NOT EXISTS settings (user_id INTEGER PRIMARY KEY, default_symbol TEXT NOT NULL DEFAULT 'SPY')",
    ]).then(() => undefined);
  }
  await ready;
  return client;
}
