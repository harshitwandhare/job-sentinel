"use client";

import { useState } from "react";

import { setJobStatus } from "@/lib/api";

const STATUS_STYLES: Record<string, string> = {
  new: "bg-emerald-900/60 text-emerald-300",
  seen: "bg-sky-900/60 text-sky-300",
  applied: "bg-violet-900/60 text-violet-300",
  ignored: "bg-neutral-800 text-neutral-400",
  closed: "bg-neutral-800 text-neutral-500",
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
          STATUS_STYLES[current] ?? "bg-neutral-800 text-neutral-400"
        }`}
      >
        {current}
      </span>
      <div className="flex gap-1.5">
        <button
          onClick={() => update("applied")}
          disabled={busy || current === "applied"}
          className="rounded border border-neutral-700 px-2 py-0.5 text-xs text-neutral-300 hover:bg-neutral-800 disabled:opacity-40"
        >
          Applied
        </button>
        <button
          onClick={() => update("ignored")}
          disabled={busy || current === "ignored"}
          className="rounded border border-neutral-700 px-2 py-0.5 text-xs text-neutral-300 hover:bg-neutral-800 disabled:opacity-40"
        >
          Ignore
        </button>
      </div>
      {failed && <span className="text-xs text-amber-400">Update failed</span>}
    </div>
  );
}
