# [MY BRAND]

A free options-positioning workspace: dealer gamma heatmap, ranked setups, charts, and demo modules for flow, dark pool, signals, AI agents and copy trading. Next.js 16, TypeScript, Tailwind v4, libSQL (Turso).

> Informational only. Not financial advice. No brokerage is connected and no orders are placed.

## Run locally

```bash
cd web
npm install
cp .env.example .env      # then edit .env
npm run dev               # http://localhost:3000
```

Requires Node 20+. With an empty `.env` everything still works: quotes and candles fall back to clearly labeled simulated data, and a local `local.db` file stores accounts.

### Environment variables

| Variable | Purpose |
|---|---|
| `FINNHUB_API_KEY` | Free Finnhub key for delayed quotes and candles. Optional. Never commit it (`.env` is git-ignored). |
| `OPTIONS_SOURCE` | `sample` (default) uses the stored sample chain. `cboe` uses the CBOE delayed feed. See the risk note below. |
| `AUTH_SECRET` | Random string that signs session cookies. **Required in production** (`openssl rand -base64 32`). |
| `TURSO_DATABASE_URL` | `file:local.db` in dev; a `libsql://...` URL on Vercel. |
| `TURSO_AUTH_TOKEN` | Turso token (not needed for a local file). |

## What is real and what is simulated

Every page and card carries a badge saying which of these it is.

| Module | Data |
|---|---|
| Positioning heatmap | Real Black-Scholes gamma math on a **stored sample chain** ("Sample data"), or on CBOE delayed data when enabled. The math is identical for both. |
| Trade setups | Computed from the heatmap data plus quotes. Illustrative score, not a signal. |
| Charts | Finnhub candles if available on your key, otherwise simulated. Positioning levels come from the heatmap. |
| Quotes | Finnhub free tier (delayed) if a key is set, otherwise simulated. |
| Options flow, dark pool, algo signals, AI agents, copy trading | **Simulated.** No free source exists. Nothing is executed. |

Note: Finnhub has moved some endpoints (notably stock candles) to paid plans over time. If your key can't read candles, the chart falls back to simulated data and says so. Check your plan at finnhub.io.

## Data layer

All data goes through the `DataProvider` interface in `src/lib/data/types.ts`. The default implementation is `src/lib/data/index.ts`. To plug in a real feed, implement the methods you want and return a `source` label so the UI stays honest. The GEX math (`src/lib/data/gex.ts`) only needs an `OptionsChain` (strike, expiry, type, open interest, IV).

Rate limits: results are cached in memory (`src/lib/data/cache.ts`): quotes 60 s, candles 15 min, CBOE chains 15 min, with in-flight de-duplication. On serverless the cache is per instance, which is fine for a free-tier app but not a guarantee against limits.

### CBOE delayed feed: terms-of-use risk

`OPTIONS_SOURCE=cboe` reads CBOE's public delayed-quotes JSON. This is an undocumented endpoint, not a licensed API. Its terms may restrict automated access, caching or redistribution of the data, and CBOE's CDN may block cloud IPs (it returned a 403 from our build sandbox). It is **off by default**. Review CBOE's current terms before enabling it on a public site, and fall back to the sample chain on any error (the app does this automatically).

## Accounts

Sign-up is optional (email and password) and only stores a watchlist and default symbol. Passwords are hashed with bcrypt and sessions are signed cookies. This is a minimal demo implementation: no email verification, password reset or rate limiting yet.

## Deploy free: Vercel + Turso

1. **Turso:** install the CLI, then `turso db create my-brand` and `turso db show my-brand --url`, then `turso db tokens create my-brand`.
2. **Vercel:** import the repo, set **Root Directory** to `web`.
3. Add environment variables in Project Settings: `AUTH_SECRET`, `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN`, and optionally `FINNHUB_API_KEY` and `OPTIONS_SOURCE`.
4. Deploy. Tables are created automatically on first use.

Plain SQLite files do not persist on Vercel, which is why production uses Turso.

## Scripts

- `npm run dev` / `npm run build` / `npm start`
- `npm run lint`
- `node scripts/gen-sample-chains.mjs` regenerates the stored sample chains (made-up data).
