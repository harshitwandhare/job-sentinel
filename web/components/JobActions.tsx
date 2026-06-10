"use client";

import { useState } from "react";

import { setJobStatus } from "@/lib/api";

const STATUS_STYLES: Record<string, string> = {
  new: "bg-emerald-100 text-emerald-700",
  seen: "bg-sky-100 text-sky-700",
  applied: "bg-violet-100 text-violet-700",
  ignored: "bg-stone-200 text-muted",
  closed: "bg-stone-200 text-muted",
};

export function JobActions({ postingId, status }: { postingId: string; status: string }) {
  const [current, setCurrent] = useState(status);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  async function update(next: string) {
    setBusy(true);
    setFailed(false);
    const ok = await setJobStatus(postingId, next);
    if (ok) setCurrent(next);
    else setFailed(true);
    setBusy(false);
  }

  return (
    <div className="flex flex-col items-end gap-2">
      <span
        className={`rounded-full px-2.5 py-1 text-xs font-medium ${
          STATUS_STYLES[current] ?? "bg-stone-200 text-muted"
        }`}
      >
        {current}
      </span>
      <div className="flex gap-1.5">
        <button
          onClick={() => update("applied")}
          disabled={busy || current === "applied"}
          className="rounded border border-line px-2 py-0.5 text-xs text-muted hover:bg-stone-100 disabled:opacity-40"
        >
          Applied
        </button>
        <button
          onClick={() => update("ignored")}
          disabled={busy || current === "ignored"}
          className="rounded border border-line px-2 py-0.5 text-xs text-muted hover:bg-stone-100 disabled:opacity-40"
        >
          Ignore
        </button>
      </div>
      {failed && <span className="text-xs text-amber-600">Update failed</span>}
    </div>
  );
}
