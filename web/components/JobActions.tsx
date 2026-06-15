"use client";

import { useState } from "react";

import { setJobStatus } from "@/lib/api";
import { cn } from "@/lib/utils";

const STATUSES = ["new", "seen", "applied", "ignored"] as const;
type Status = (typeof STATUSES)[number];

const STATUS_STYLES: Record<string, string> = {
  new: "bg-emerald-100 text-emerald-700",
  seen: "bg-sky-100 text-sky-700",
  applied: "bg-violet-100 text-violet-700",
  ignored: "bg-stone-200 text-stone-500",
  closed: "bg-stone-200 text-stone-500",
};

/**
 * Inline action row for a tracked job card — status pill + quick-action chips,
 * designed to sit inside a flex footer row alongside other card actions.
 */
export function JobActions({
  postingId,
  status,
  onChange,
}: {
  postingId: string;
  status: string;
  onChange?: (next: string) => void;
}) {
  const [current, setCurrent] = useState(status);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  async function update(next: string) {
    if (busy || next === current) return;
    setBusy(true);
    setFailed(false);
    const ok = await setJobStatus(postingId, next);
    if (ok) {
      setCurrent(next);
      onChange?.(next);
    } else {
      setFailed(true);
    }
    setBusy(false);
  }

  return (
    <>
      {/* Quick actions */}
      {current !== "applied" && (
        <button
          onClick={() => update("applied")}
          disabled={busy}
          className="inline-flex h-8 items-center rounded-lg border border-line px-3 text-xs font-medium text-ink transition-colors hover:border-ink/30 hover:bg-bg disabled:opacity-50"
        >
          Mark applied
        </button>
      )}
      {current !== "ignored" && (
        <button
          onClick={() => update("ignored")}
          disabled={busy}
          className="inline-flex h-8 items-center rounded-lg border border-line px-3 text-xs font-medium text-muted transition-colors hover:border-ink/30 hover:text-ink disabled:opacity-50"
        >
          Ignore
        </button>
      )}
      {(current === "applied" || current === "ignored") && (
        <button
          onClick={() => update("new")}
          disabled={busy}
          className="inline-flex h-8 items-center rounded-lg border border-line px-3 text-xs font-medium text-muted transition-colors hover:border-ink/30 hover:text-ink disabled:opacity-50"
        >
          Reset
        </button>
      )}
      {/* Status pill — rightmost in parent flex row */}
      <span
        className={cn(
          "ml-auto inline-flex h-8 items-center rounded-full px-3 text-xs font-medium capitalize",
          STATUS_STYLES[current] ?? "bg-stone-200 text-stone-500",
        )}
      >
        {current}
      </span>
      {failed && (
        <span className="text-xs text-amber-600">Update failed</span>
      )}
    </>
  );
}
