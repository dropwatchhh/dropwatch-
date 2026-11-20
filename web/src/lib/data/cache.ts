// Tiny in-memory TTL cache + in-flight de-duplication, to stay inside free-tier rate limits.
const store = new Map<string, { exp: number; val: unknown }>();
const inflight = new Map<string, Promise<unknown>>();

export async function cached<T>(key: string, ttlMs: number, fn: () => Promise<T>): Promise<T> {
  const hit = store.get(key);
  if (hit && hit.exp > Date.now()) return hit.val as T;
  const pending = inflight.get(key);
  if (pending) return pending as Promise<T>;
  const p = fn()
    .then((val) => { store.set(key, { exp: Date.now() + ttlMs, val }); return val; })
    .finally(() => inflight.delete(key));
  inflight.set(key, p);
  return p;
}
