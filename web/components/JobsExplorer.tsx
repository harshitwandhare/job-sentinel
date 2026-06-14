"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useMemo, useState } from "react";

import { AiMatch } from "@/components/AiMatch";
import { JobActions } from "@/components/JobActions";
import { JobDocs } from "@/components/JobDocs";
import { Card, CardSub, CardTitle } from "@/components/ui/card";
import type { JobDetail, JobPosting } from "@/lib/api";
import { cn, externalUrl } from "@/lib/utils";

const STATUSES = ["new", "seen", "applied", "ignored"] as const;

const ACCENT: Record<string, string> = {
  new: "bg-emerald-500",
  seen: "bg-sky-500",
  applied: "bg-violet-500",
  ignored: "bg-stone-300",
  closed: "bg-stone-300",
};

function detailOf(job: JobPosting): JobDetail | undefined {
  return job.raw_data?.detail;
}

/** Days until a (free-form) deadline; null when it can't be parsed. */
function daysLeft(deadline: string): number | null {
  if (!deadline) return null;
  const t = Date.parse(deadline);
  if (Number.isNaN(t)) return null;
  return Math.ceil((t - Date.now()) / 86_400_000);
}

function DeadlineChip({ deadline }: { deadline: string }) {
  const d = daysLeft(deadline);
  if (d === null) {
    return <span className="text-sm text-amber-600">Deadline: {deadline}</span>;
  }
  if (d < 0) return <span className="text-sm text-muted line-through">Closed {deadline}</span>;
  const urgent = d <= 7;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium",
        urgent ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700",
      )}
    >
      {urgent && (
        <span className="relative flex h-1.5 w-1.5">
          <span className="absolute h-full w-full animate-ping rounded-full bg-red-500 opacity-60" />
          <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
        </span>
      )}
      {d === 0 ? "Closes today" : `${d} day${d === 1 ? "" : "s"} left`}
    </span>
  );
}

function FactRow({ label, value }: { label: string; value?: string | number | null }) {
  if (value === undefined || value === null || value === "") return null;
  return (
    <div className="flex flex-col text-sm sm:flex-row sm:gap-2">
      <span className="shrink-0 text-muted sm:w-40">{label}</span>
      <span className="min-w-0 break-words text-ink">{String(value)}</span>
    </div>
  );
}

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
 * Client-side explorer over the tracked jobs: search, status filters with live
 * counts, deadline-aware sorting, and animated cards. The list itself comes
 * from the server component, so first paint is instant.
 */
export function JobsExplorer({ jobs }: { jobs: JobPosting[] }) {
  const reduced = useReducedMotion();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<string>("all");
  const [sort, setSort] = useState<"newest" | "deadline">("newest");
  // Status changes made in this session, layered over the server snapshot so
  // filter counts stay live without refetching.
  const [overrides, setOverrides] = useState<Record<string, string>>({});

  const statusOf = (j: JobPosting) => overrides[j.posting_id] ?? j.status;

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: jobs.length };
    for (const j of jobs) c[statusOf(j)] = (c[statusOf(j)] ?? 0) + 1;
    return c;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobs, overrides]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = jobs.filter((j) => {
      if (filter !== "all" && statusOf(j) !== filter) return false;
      if (!q) return true;
      return [j.title, j.employer, j.location, j.job_type]
        .join(" ")
        .toLowerCase()
        .includes(q);
    });
    if (sort === "deadline") {
      return [...filtered].sort((a, b) => {
        const da = daysLeft(a.deadline);
        const db = daysLeft(b.deadline);
        if (da === null && db === null) return 0;
        if (da === null) return 1;
        if (db === null) return -1;
        return da - db;
      });
    }
    return filtered; // server already returns newest first
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobs, query, filter, sort, overrides]);

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="sticky top-14 z-10 -mx-1 space-y-3 rounded-2xl border border-line bg-bg/90 p-3 backdrop-blur-md">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative min-w-0 flex-1">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted"
              aria-hidden="true"
            >
              <circle cx="11" cy="11" r="7" />
              <path d="m20 20-3.5-3.5" />
            </svg>
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search title, employer, location…"
              aria-label="Search tracked jobs"
              className="h-10 w-full rounded-lg border border-line bg-surface pl-9 pr-3 text-sm text-ink shadow-sm placeholder:text-muted/70 focus-visible:border-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/30"
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-muted">
            Sort
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value as "newest" | "deadline")}
              className="h-10 rounded-lg border border-line bg-surface px-2.5 text-sm text-ink shadow-sm focus-visible:border-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/30"
            >
              <option value="newest">Newest</option>
              <option value="deadline">Deadline</option>
            </select>
          </label>
        </div>
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filter by status">
          {["all", ...STATUSES].map((s) => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              aria-pressed={filter === s}
              className={cn(
                "rounded-full border px-3 py-1 text-xs font-medium capitalize transition-colors",
                filter === s
                  ? "border-ink bg-ink text-white"
                  : "border-line bg-surface text-muted hover:border-ink/30 hover:text-ink",
              )}
            >
              {s}
              <span className={cn("ml-1.5 tabular-nums", filter === s ? "text-white/60" : "text-muted/60")}>
                {counts[s] ?? 0}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Results */}
      {visible.length === 0 ? (
        <Card>
          <CardTitle>Nothing matches</CardTitle>
          <CardSub className="mt-2">
            {jobs.length === 0
              ? "No jobs tracked yet — use Login above to sign in to the portal once, then Run scraper."
              : "Try a different search or status filter."}
          </CardSub>
        </Card>
      ) : (
        <AnimatePresence initial={false} mode="popLayout">
          {visible.map((j, idx) => {
            const d = detailOf(j);
            return (
              <motion.div
                key={j.posting_id}
                layout={!reduced}
                initial={reduced ? false : { opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={reduced ? undefined : { opacity: 0, scale: 0.98 }}
                transition={{ duration: 0.3, delay: Math.min(idx * 0.03, 0.3) }}
              >
                <Card className="group relative mb-4 space-y-2 overflow-hidden pl-6">
                  <span
                    aria-hidden="true"
                    className={cn(
                      "absolute inset-y-0 left-0 w-1",
                      ACCENT[statusOf(j)] ?? "bg-stone-300",
                    )}
                  />
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="flex min-w-0 flex-1 gap-3.5">
                      <Monogram name={j.employer || j.title} />
                      <div className="min-w-0 flex-1">
                        <CardTitle>{j.title}</CardTitle>
                        <CardSub>
                          {[j.employer, j.location, j.job_type].filter(Boolean).join(" · ")}
                        </CardSub>
                        <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1.5">
                          {j.posted_date && <CardSub>Posted {j.posted_date}</CardSub>}
                          {j.deadline && <DeadlineChip deadline={j.deadline} />}
                          {d?.salary && (
                            <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-700">
                              {d.salary}
                            </span>
                          )}
                          {typeof d?.num_applicants === "number" && (
                            <CardSub>{d.num_applicants} applicants</CardSub>
                          )}
                        </div>
                        {j.portal_url && (
                          <a
                            href={externalUrl(j.portal_url)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="mt-1 inline-block text-sm text-brand hover:underline"
                          >
                            View posting →
                          </a>
                        )}
                      </div>
                    </div>
                    <JobActions
                      postingId={j.posting_id}
                      status={statusOf(j)}
                      onChange={(next) =>
                        setOverrides((o) => ({ ...o, [j.posting_id]: next }))
                      }
                    />
                  </div>

                  <JobDocs
                    title={j.title}
                    employer={j.employer}
                    jobText={[
                      j.title,
                      j.employer,
                      j.job_type,
                      d?.job_function ?? "",
                      d?.industry ?? "",
                      d?.description || j.description_snippet,
                    ]
                      .filter(Boolean)
                      .join("\n")}
                  />

                  <AiMatch postingId={j.posting_id} />

                  {(d?.description || j.description_snippet) && (
                    <details className="group/details">
                      <summary className="cursor-pointer select-none text-sm font-medium text-brand">
                        Job details
                      </summary>
                      <div className="mt-2 space-y-2 border-l-2 border-line pl-3">
                        <div className="space-y-0.5">
                          <FactRow label="Job function" value={d?.job_function} />
                          <FactRow label="Industry" value={d?.industry} />
                          <FactRow label="Openings" value={d?.openings} />
                          <FactRow
                            label="Work-study required"
                            value={
                              d?.work_study_required === undefined || d?.work_study_required === null
                                ? undefined
                                : d.work_study_required
                                  ? "Yes"
                                  : "No"
                            }
                          />
                          <FactRow label="Work authorization" value={d?.required_work_auth} />
                          <FactRow
                            label="Documents"
                            value={
                              d?.application_documents?.length
                                ? d.application_documents.join(", ")
                                : undefined
                            }
                          />
                          <FactRow
                            label="Contact"
                            value={
                              d?.contact_name
                                ? `${d.contact_name}${d.contact_email ? ` · ${d.contact_email}` : ""}`
                                : undefined
                            }
                          />
                        </div>
                        <p className="whitespace-pre-line text-sm text-muted">
                          {d?.description || j.description_snippet}
                        </p>
                      </div>
                    </details>
                  )}
                </Card>
              </motion.div>
            );
          })}
        </AnimatePresence>
      )}
    </div>
  );
}
