"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useState } from "react";

import { AiMatch } from "@/components/AiMatch";
import { Card, CardSub, CardTitle } from "@/components/ui/card";
import { createApplication, type JobPosting } from "@/lib/api";
import { cn, externalUrl } from "@/lib/utils";

/** Initial-letter monogram used as a lightweight employer "logo". */
function Monogram({ name }: { name: string }) {
  const letter = (name.trim()[0] ?? "?").toUpperCase();
  return (
    <div
      aria-hidden="true"
      className="grid h-11 w-11 shrink-0 select-none place-items-center rounded-xl border border-line bg-bg font-semibold text-muted"
    >
      {letter}
    </div>
  );
}

/**
 * A single search result (from any source). Results are ephemeral — not in the
 * DB — so the only mutating action is "Track", which creates an Application.
 */
export function SearchResultCard({ job, index }: { job: JobPosting; index: number }) {
  const reduced = useReducedMotion();
  const [tracked, setTracked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [showDetails, setShowDetails] = useState(false);

  const raw = job.raw_data ?? {};
  const salary = typeof raw.salary_text === "string" ? raw.salary_text : "";
  const isRemote = raw.is_remote === true;
  const tags = Array.isArray(raw.tags) ? (raw.tags as unknown[]).filter((t) => typeof t === "string") : [];
  const detail = (raw.detail ?? {}) as { description?: string };
  const description = (detail.description || job.description_snippet || "").trim();

  async function onTrack() {
    setBusy(true);
    setError("");
    const created = await createApplication({
      title: job.title,
      employer: job.employer,
      location: job.location,
      url: job.portal_url,
      source: job.source_adapter,
      stage: "saved",
    });
    setBusy(false);
    if (created) setTracked(true);
    else setError("Couldn't save — is the local API running?");
  }

  return (
    <motion.div
      layout={!reduced}
      initial={reduced ? false : { opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, delay: Math.min(index * 0.025, 0.25) }}
    >
      <Card className="space-y-3">
        <div className="flex items-start gap-3.5">
          <Monogram name={job.employer || job.title} />
          <div className="min-w-0 flex-1">
            <CardTitle className="leading-snug">{job.title}</CardTitle>
            <CardSub className="mt-0.5">
              {[job.employer, job.location, job.job_type].filter(Boolean).join(" · ")}
            </CardSub>
            <div className="mt-2 flex flex-wrap items-center gap-1.5">
              {isRemote && (
                <span className="rounded-full bg-sky-100 px-2 py-0.5 text-[11px] font-medium text-sky-700">
                  Remote
                </span>
              )}
              {salary && (
                <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
                  {salary}
                </span>
              )}
              <span className="rounded-full border border-line px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide text-muted">
                {job.source_adapter || "source"}
              </span>
              {job.posted_date && <span className="text-[11px] text-muted">· {job.posted_date}</span>}
            </div>
            {tags.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {(tags as string[]).slice(0, 5).map((t) => (
                  <span
                    key={t}
                    className="rounded border border-line px-1.5 py-0.5 text-[11px] text-muted"
                  >
                    {t}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer — all actions on one row; panels expand below */}
        <div className="flex flex-wrap items-center gap-2 border-t border-line pt-3">
          <button
            onClick={onTrack}
            disabled={busy || tracked}
            className={cn(
              "inline-flex h-8 items-center rounded-lg px-3 text-xs font-medium transition-colors disabled:opacity-60",
              tracked
                ? "bg-emerald-100 text-emerald-700"
                : "bg-brand text-white hover:bg-brand-500",
            )}
          >
            {tracked ? "✓ Tracked" : busy ? "Saving…" : "Track"}
          </button>
          {job.portal_url && (
            <a
              href={externalUrl(job.portal_url)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex h-8 items-center rounded-lg border border-line px-3 text-xs font-medium text-ink transition-colors hover:border-ink/30 hover:bg-bg"
            >
              View posting ↗
            </a>
          )}
          <AiMatch
            jobText={[job.title, job.employer, job.job_type, description]
              .filter(Boolean)
              .join("\n")}
          />
          {description && (
            <button
              onClick={() => setShowDetails((v) => !v)}
              aria-expanded={showDetails}
              className="inline-flex h-8 items-center gap-1 rounded-lg border border-line px-3 text-xs font-medium text-muted transition-colors hover:border-ink/30 hover:text-ink"
            >
              Job details
              <span aria-hidden="true" className={cn("transition-transform", showDetails && "rotate-180")}>
                ▾
              </span>
            </button>
          )}
          {error && <span className="w-full text-xs text-amber-600">{error}</span>}
        </div>

        {showDetails && description && (
          <p className="whitespace-pre-line border-l-2 border-line pl-3 text-sm leading-relaxed text-muted">
            {description}
          </p>
        )}
      </Card>
    </motion.div>
  );
}
