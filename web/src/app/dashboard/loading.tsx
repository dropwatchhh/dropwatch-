export default function Loading() {
  return (
    <div className="animate-pulse space-y-4" aria-busy="true" aria-label="Loading">
      <div className="h-9 w-64 rounded bg-white/5" />
      <div className="h-4 w-96 max-w-full rounded bg-white/5" />
      <div className="h-72 rounded-2xl bg-white/5" />
    </div>
  );
}
