"use client";
import { useActionState } from "react";
import { saveSettings } from "@/lib/actions";
import { SYMBOLS } from "@/lib/data/types";

export function SettingsForm({ current }: { current: string }) {
  const [state, action, pending] = useActionState(saveSettings, undefined);
  return (
    <form action={action} className="space-y-4">
      <label className="block text-sm">
        Default symbol for the heatmap
        <select name="default_symbol" defaultValue={current} className="mt-1 h-11 w-full rounded-lg border border-line bg-surface-2 px-3">
          {SYMBOLS.map((s) => <option key={s}>{s}</option>)}
        </select>
      </label>
      {state?.error && <p role="alert" className="text-sm text-neg">{state.error}</p>}
      {state?.ok && <p className="text-sm text-pos">{state.ok}</p>}
      <button disabled={pending} className="h-10 rounded-full bg-accent px-5 text-sm font-semibold text-black disabled:opacity-60">Save</button>
    </form>
  );
}
