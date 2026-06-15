"use client";

import { useState } from "react";

import { buildCover, buildResume } from "@/lib/api";

interface JobDocsProps {
  title: string;
  employer: string;
  /** Full job text used for tailoring (description + requirements). */
  jobText: string;
  /** Use the local LLM to rephrase/polish when it's running. */
  ai?: boolean;
}

function download(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function slug(text: string): string {
  return (
    text
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 40) || "job"
  );
}

/**
 * Per-posting document generation: a résumé tailored to this job's description
 * and a matching cover letter, downloaded as PDFs. Uses the same build
 * endpoints as the studio, so output is identical either way.
 */
export function JobDocs({ title, employer, jobText, ai = true }: JobDocsProps) {
  const [busy, setBusy] = useState<"" | "resume" | "cover">("");
  const [error, setError] = useState("");

  async function onResume() {
    setBusy("resume");
    setError("");
    try {
      const result = await buildResume(jobText, ai);
      if (result.ok && result.blob) download(result.blob, `resume-${slug(title)}.pdf`);
      else setError(result.detail ?? "Resume build failed.");
    } finally {
      setBusy("");
    }
  }

  async function onCover() {
    setBusy("cover");
    setError("");
    try {
      const result = await buildCover(jobText, title, employer, ai);
      if (result.ok && result.blob) download(result.blob, `cover-${slug(title)}.pdf`);
      else setError(result.detail ?? "Cover letter build failed.");
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        onClick={onResume}
        disabled={busy !== ""}
        className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-brand px-3 text-xs font-medium text-white transition-colors hover:bg-brand-500 disabled:opacity-50"
        title="Tailor your profile to this posting and download the PDF"
      >
        {busy === "resume" ? (
          <>
            <Spinner /> Tailoring résumé…
          </>
        ) : (
          "⤓ Tailored résumé"
        )}
      </button>
      <button
        onClick={onCover}
        disabled={busy !== ""}
        className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-line px-3 text-xs font-medium text-ink transition-colors hover:border-ink/30 hover:bg-surface disabled:opacity-50"
        title="Generate a cover letter for this posting and download the PDF"
      >
        {busy === "cover" ? (
          <>
            <Spinner /> Writing cover letter…
          </>
        ) : (
          "⤓ Cover letter"
        )}
      </button>
      {busy && (
        <span className="text-xs text-muted">
          Building with LaTeX{ai ? " + local AI when available" : ""} — a few seconds…
        </span>
      )}
      {error && <span className="text-xs text-amber-600">{error}</span>}
    </div>
  );
}

function Spinner() {
  return (
    <span
      aria-hidden="true"
      className="h-3 w-3 animate-spin rounded-full border-[1.5px] border-current border-t-transparent"
    />
  );
}
