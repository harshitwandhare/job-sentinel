"use client";

import { useCallback, useEffect, useState } from "react";

import {
  type Application,
  type ApplyFindResponse,
  type LearnedLabel,
  applyFind,
  forgetLabel,
  getApplyQueue,
  getFieldMap,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const WINDOWS = [3, 7, 14, 30];

export default function ApplyPage() {
  const [keywords, setKeywords] = useState("");
  const [location, setLocation] = useState("");
  const [days, setDays] = useState(7);
  const [screen, setScreen] = useState(true);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<ApplyFindResponse | null>(null);
  const [queue, setQueue] = useState<Application[]>([]);
  const [learned, setLearned] = useState<LearnedLabel[]>([]);

  const refresh = useCallback(async () => {
    setQueue(await getApplyQueue());
    setLearned(await getFieldMap());
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function run() {
    setRunning(true);
    setResult(null);
    const res = await applyFind({ keywords, location, date_posted_days: days, screen });
    setResult(res);
    setRunning(false);
    await refresh();
  }

  async function forget(entry: LearnedLabel) {
    await forgetLabel(entry.label, entry.ats);
    await refresh();
  }

  return (
    <div className="mx-auto max-w-3xl px-5 py-12">
      <header className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-ink">Apply</h1>
        <p className="mt-2 text-sm text-muted">
          Search every enabled source, re-read each posting through the board that serves it, and
          queue the ones nothing rules you out of. Filling and submitting stay with you.
        </p>
      </header>

      <div className="space-y-4 rounded-xl border border-line bg-surface p-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-ink" htmlFor="apply-keywords">
              What to look for
            </label>
            <input
              id="apply-keywords"
              type="text"
              className="w-full rounded-lg border border-line bg-bg px-3 py-2 text-sm text-ink placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-brand/40"
              placeholder="e.g. software engineer intern"
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium text-ink" htmlFor="apply-location">
              Where <span className="font-normal text-muted">(optional)</span>
            </label>
            <input
              id="apply-location"
              type="text"
              className="w-full rounded-lg border border-line bg-bg px-3 py-2 text-sm text-ink placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-brand/40"
              placeholder="e.g. Austin, TX"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
            />
          </div>
        </div>

        <div>
          <span className="mb-1.5 block text-sm font-medium text-ink">Posted within</span>
          <div className="flex gap-2">
            {WINDOWS.map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setDays(n)}
                className={cn(
                  "flex-1 rounded-lg border px-3 py-2 text-sm font-medium transition-colors",
                  days === n
                    ? "border-brand bg-brand/10 text-brand"
                    : "border-line bg-bg text-ink hover:border-ink/30",
                )}
              >
                {n} days
              </button>
            ))}
          </div>
        </div>

        <label className="flex cursor-pointer items-center gap-2.5">
          <input
            type="checkbox"
            checked={screen}
            onChange={(e) => setScreen(e.target.checked)}
            className="h-4 w-4 rounded accent-brand"
          />
          <span className="text-sm text-ink">
            Screen each posting{" "}
            <span className="text-muted">
              (slower, but keeps roles you cannot apply to out of the queue)
            </span>
          </span>
        </label>

        <button
          type="button"
          onClick={run}
          disabled={running}
          className="rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
        >
          {running ? "Running" : "Find and queue"}
        </button>
      </div>

      {result && (
        <section className="mt-8">
          <h2 className="text-lg font-semibold text-ink">{result.summary}</h2>
          {result.errors.map((err) => (
            <p key={err} className="mt-1 text-sm text-amber-700">
              {err}
            </p>
          ))}
          {result.blocked.length > 0 && (
            <ul className="mt-4 space-y-2">
              {result.blocked.map((b) => (
                <li
                  key={b.url || b.employer + b.title}
                  className="rounded-lg border border-line p-3"
                >
                  <p className="text-sm font-medium text-ink">
                    {b.employer}, {b.title}
                  </p>
                  <p className="text-sm text-muted">{b.why}</p>
                  {b.quotes[0] && (
                    <p className="mt-1 border-l-2 border-line pl-2 text-xs italic text-muted">
                      {b.quotes[0]}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <section className="mt-10">
        <h2 className="text-lg font-semibold text-ink">Waiting to be filled ({queue.length})</h2>
        {queue.length === 0 ? (
          <p className="mt-2 text-sm text-muted">Nothing queued yet.</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {queue.map((app) => (
              <li key={app.id} className="rounded-lg border border-line bg-surface p-3">
                <p className="text-sm font-medium text-ink">
                  {app.employer}, {app.title}
                </p>
                {app.url && (
                  <a
                    href={app.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-brand underline"
                  >
                    {app.url}
                  </a>
                )}
                {app.notes && <p className="mt-1 text-xs text-muted">{app.notes}</p>}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-semibold text-ink">Wordings the filler learned</h2>
        <p className="mt-1 text-sm text-muted">
          A question a form asked in words the answer bank did not recognise, paired with the
          stored answer it means. Drop one it got wrong.
        </p>
        {learned.length === 0 ? (
          <p className="mt-2 text-sm text-muted">Nothing learned yet.</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {learned.map((entry) => (
              <li
                key={entry.ats + ":" + entry.label}
                className="flex items-start gap-3 rounded-lg border border-line bg-surface p-3"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-ink">{entry.label}</p>
                  <p className="text-xs text-muted">
                    {entry.ats} to {entry.field_id}, used {entry.uses} times
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => forget(entry)}
                  className="shrink-0 rounded-lg border border-line px-2.5 py-1 text-xs text-ink hover:border-ink/30"
                >
                  Forget
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
