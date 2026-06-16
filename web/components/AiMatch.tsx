"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useState } from "react";

import { matchJob, type MatchResult } from "@/lib/api";
import { cn } from "@/lib/utils";

const VERDICT_STYLES: Record<string, string> = {
  strong: "bg-emerald-100 text-emerald-700",
  moderate: "bg-amber-100 text-amber-700",
  weak: "bg-red-100 text-red-700",
};

function Spinner() {
  return (
    <span
      aria-hidden="true"
      className="h-3 w-3 animate-spin rounded-full border-[1.5px] border-current border-t-transparent"
    />
  );
}

function Ring({ pct }: { pct: number }) {
  const reduced = useReducedMotion();
  const r = 26;
  const c = 2 * Math.PI * r;
  const color = pct >= 70 ? "stroke-emerald-500" : pct >= 45 ? "stroke-amber-500" : "stroke-red-500";
  return (
    <div className="relative grid h-16 w-16 shrink-0 place-items-center">
      <svg viewBox="0 0 64 64" className="h-16 w-16 -rotate-90">
        <circle cx="32" cy="32" r={r} fill="none" strokeWidth="6" className="stroke-stone-200" />
        <motion.circle
          cx="32"
          cy="32"
          r={r}
          fill="none"
          strokeWidth="6"
          strokeLinecap="round"
          className={color}
          strokeDasharray={c}
          initial={reduced ? { strokeDashoffset: c * (1 - pct / 100) } : { strokeDashoffset: c }}
          animate={{ strokeDashoffset: c * (1 - pct / 100) }}
          transition={{ duration: 0.8, ease: [0.21, 0.65, 0.36, 1] }}
        />
      </svg>
      <span className="absolute text-sm font-bold tabular-nums text-ink">{pct}%</span>
    </div>
  );
}

/**
 * Full-width collapsible AI match section. Renders a top-bordered toggle
 * header and an animated panel below. Lazy — only calls the API on first
 * open. Once scored the panel can be toggled open/closed freely.
 */
export function AiMatch({ jobText, postingId }: { jobText?: string; postingId?: string }) {
  const reduced = useReducedMotion();
  const [open, setOpen] = useState(false);
  const [result, setResult] = useState<MatchResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const score = result ? Math.round(result.score * 100) : null;

  async function handleToggle() {
    if (result) { setOpen((v) => !v); return; }
    if (busy) return;
    setBusy(true);
    setError("");
    const r = await matchJob({ job_description: jobText, posting_id: postingId, ai: true });
    setBusy(false);
    if (r) { setResult(r); setOpen(true); }
    else setError("Match needs the local engine — run `job-sentinel serve`.");
  }

  return (
    <div className="border-t border-line">
      <button
        onClick={handleToggle}
        disabled={busy}
        aria-expanded={open}
        className="flex w-full items-center gap-2 py-2 text-left text-xs font-medium text-brand transition-colors hover:text-brand/80 disabled:opacity-60"
      >
        {busy ? (
          <span className="flex items-center gap-1.5"><Spinner /> Scoring…</span>
        ) : score !== null ? (
          <span className="flex items-center gap-1.5">✦ {score}% match</span>
        ) : (
          <span className="flex items-center gap-1.5">✦ AI match</span>
        )}
        {error && <span className="ml-2 text-[11px] text-amber-600">{error}</span>}
        {result && (
          <span
            aria-hidden="true"
            className={cn("ml-auto transition-transform duration-200", open && "rotate-180")}
          >
            ▾
          </span>
        )}
      </button>

      <AnimatePresence initial={false}>
        {open && result && (
          <motion.div
            initial={reduced ? false : { height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={reduced ? undefined : { height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="mb-2 rounded-xl border border-line bg-bg p-3">
              <div className="flex items-start gap-3">
                <Ring pct={score!} />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-xs font-medium capitalize",
                        VERDICT_STYLES[result.verdict] ?? "bg-stone-200 text-muted",
                      )}
                    >
                      {result.verdict} match
                    </span>
                    {result.semantic !== null && result.semantic !== undefined && (
                      <span className="text-[11px] text-muted">
                        {Math.round(result.coverage * 100)}% keywords · {Math.round(result.semantic * 100)}% semantic
                      </span>
                    )}
                  </div>
                  <p className="mt-1.5 text-sm leading-relaxed text-ink">{result.rationale}</p>
                </div>
              </div>

              {(result.strengths.length > 0 || result.gaps.length > 0) && (
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  {result.strengths.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-emerald-700">Strengths</p>
                      <ul className="mt-1 space-y-0.5">
                        {result.strengths.slice(0, 5).map((s, i) => (
                          <li key={i} className="text-xs text-muted">+ {s}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {result.gaps.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-amber-700">Gaps to address</p>
                      <ul className="mt-1 space-y-0.5">
                        {result.gaps.slice(0, 5).map((g, i) => (
                          <li key={i} className="text-xs text-muted">− {g}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {result.missing_keywords.length > 0 && (
                <div className="mt-3">
                  <p className="text-xs font-medium text-muted">Missing keywords</p>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {result.missing_keywords.slice(0, 15).map((k) => (
                      <span key={k} className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] text-amber-700">
                        {k}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
