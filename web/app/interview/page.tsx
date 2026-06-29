"use client";

import { useState } from "react";

import {
  type InterviewQuestion,
  type InterviewQuestionsResponse,
  getInterviewQuestions,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const CATEGORY_STYLES: Record<string, string> = {
  Behavioural: "bg-sky-100 text-sky-700",
  Technical: "bg-violet-100 text-violet-700",
  "Role-specific": "bg-emerald-100 text-emerald-700",
  "Culture fit": "bg-amber-100 text-amber-700",
};

const COUNTS = [5, 10, 15, 20];

export default function InterviewPrepPage() {
  const [jd, setJd] = useState("");
  const [role, setRole] = useState("");
  const [count, setCount] = useState(10);
  const [useAi, setUseAi] = useState(true);
  const [result, setResult] = useState<InterviewQuestionsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function generate() {
    setLoading(true);
    setError("");
    setResult(null);
    const res = await getInterviewQuestions({
      job_description: jd,
      role,
      count,
      ai: useAi,
    });
    setLoading(false);
    if (!res) {
      setError("Could not reach the API. Make sure job-sentinel serve is running.");
      return;
    }
    setResult(res);
  }

  return (
    <div className="mx-auto max-w-3xl px-5 py-12">
      <header className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-ink">Interview Prep</h1>
        <p className="mt-2 text-sm text-muted">
          Paste a job description and get tailored mock interview questions — generated locally
          with your LLM or from a curated universal set when no model is running.
        </p>
      </header>

      <div className="space-y-4 rounded-xl border border-line bg-surface p-5">
        <div>
          <label className="mb-1.5 block text-sm font-medium text-ink">
            Job description{" "}
            <span className="font-normal text-muted">(optional — paste the full JD)</span>
          </label>
          <textarea
            className="w-full rounded-lg border border-line bg-bg px-3 py-2 text-sm text-ink placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-brand/40"
            rows={7}
            placeholder="Paste the job posting here…"
            value={jd}
            onChange={(e) => setJd(e.target.value)}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-ink">
              Role title{" "}
              <span className="font-normal text-muted">(used when no JD is supplied)</span>
            </label>
            <input
              type="text"
              className="w-full rounded-lg border border-line bg-bg px-3 py-2 text-sm text-ink placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-brand/40"
              placeholder="e.g. Software Engineer Intern"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            />
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-ink">
              Number of questions
            </label>
            <div className="flex gap-2">
              {COUNTS.map((n) => (
                <button
                  key={n}
                  onClick={() => setCount(n)}
                  className={cn(
                    "flex-1 rounded-lg border px-3 py-2 text-sm font-medium transition-colors",
                    count === n
                      ? "border-brand bg-brand/10 text-brand"
                      : "border-line bg-bg text-ink hover:border-ink/30",
                  )}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>
        </div>

        <label className="flex cursor-pointer items-center gap-2.5">
          <input
            type="checkbox"
            checked={useAi}
            onChange={(e) => setUseAi(e.target.checked)}
            className="h-4 w-4 rounded accent-brand"
          />
          <span className="text-sm text-ink">
            Use local LLM{" "}
            <span className="text-muted">(falls back to curated set if Ollama isn&apos;t running)</span>
          </span>
        </label>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          onClick={generate}
          disabled={loading}
          className="w-full rounded-lg bg-brand px-4 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {loading ? "Generating…" : "Generate questions"}
        </button>
      </div>

      {result && <QuestionList result={result} />}
    </div>
  );
}

function QuestionList({ result }: { result: InterviewQuestionsResponse }) {
  const byCategory = result.questions.reduce<Record<string, InterviewQuestion[]>>(
    (acc: Record<string, InterviewQuestion[]>, q: InterviewQuestion) => {
      (acc[q.category] ??= []).push(q);
      return acc;
    },
    {},
  );

  const categories = Object.keys(byCategory);

  return (
    <div className="mt-8">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-ink">
          {result.questions.length} questions for{" "}
          <span className="text-brand">{result.role_hint}</span>
        </h2>
        <span
          className={cn(
            "rounded-full px-2.5 py-0.5 text-xs font-medium",
            result.source === "llm"
              ? "bg-emerald-100 text-emerald-700"
              : "bg-stone-100 text-stone-600",
          )}
        >
          {result.source === "llm" ? "AI-generated" : "Curated set"}
        </span>
      </div>

      <div className="space-y-6">
        {categories.map((cat) => (
          <section key={cat}>
            <h3
              className={cn(
                "mb-3 inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold",
                CATEGORY_STYLES[cat] ?? "bg-stone-100 text-stone-700",
              )}
            >
              {cat}
            </h3>
            <ol className="space-y-3">
              {byCategory[cat].map((q: InterviewQuestion, i: number) => (
                <li
                  key={i}
                  className="flex gap-3 rounded-lg border border-line bg-surface px-4 py-3"
                >
                  <span className="mt-0.5 shrink-0 text-sm font-bold text-muted">
                    {i + 1}.
                  </span>
                  <p className="text-sm leading-relaxed text-ink">{q.question}</p>
                </li>
              ))}
            </ol>
          </section>
        ))}
      </div>
    </div>
  );
}

