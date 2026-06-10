"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardSub, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  buildCover,
  buildResume,
  getLlmStatus,
  tailorResume,
  type LlmStatus,
  type TailorResult,
} from "@/lib/api";

function download(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function StudioPage() {
  const [jd, setJd] = useState("");
  const [ai, setAi] = useState(false);
  const [result, setResult] = useState<TailorResult | null>(null);
  const [busy, setBusy] = useState<"tailor" | "build" | "cover" | null>(null);
  const [message, setMessage] = useState("");
  const [role, setRole] = useState("");
  const [company, setCompany] = useState("");
  const [llm, setLlm] = useState<LlmStatus | null>(null);

  useEffect(() => {
    void getLlmStatus().then(setLlm);
  }, []);

  async function onTailor() {
    if (!jd.trim()) return;
    setBusy("tailor");
    setMessage("");
    const r = await tailorResume(jd);
    setResult(r);
    if (!r) setMessage("Could not reach the API. Is `job-sentinel serve` running?");
    setBusy(null);
  }

  async function onDownload() {
    setBusy("build");
    setMessage("");
    const res = await buildResume(jd, ai);
    if (res.ok && res.blob) download(res.blob, "resume.pdf");
    else setMessage(res.detail ?? "Build failed.");
    setBusy(null);
  }

  async function onCover() {
    setBusy("cover");
    setMessage("");
    const res = await buildCover(jd, role, company, ai);
    if (res.ok && res.blob) download(res.blob, "cover_letter.pdf");
    else setMessage(res.detail ?? "Cover letter build failed.");
    setBusy(null);
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-5 py-12">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold text-ink">Résumé studio</h1>
          <p className="mt-1 text-muted">
            Paste a job description, see how your profile matches, and download a tailored PDF.
          </p>
        </div>
        {llm && (
          <span
            className={`rounded-full px-2.5 py-1 text-xs font-medium ${
              llm.chat_ready ? "bg-emerald-100 text-emerald-700" : "bg-stone-200 text-muted"
            }`}
            title={
              llm.chat_ready
                ? `${llm.chat_model} via ${llm.base_url}`
                : `Ollama ${llm.reachable ? "is missing the model" : "is unreachable"} — AI rephrasing falls back to keyword tailoring`
            }
          >
            {llm.chat_ready ? `Local AI ready · ${llm.chat_model}` : "Local AI unavailable"}
          </span>
        )}
      </header>

      <Textarea
        rows={8}
        placeholder="Paste the job description here…"
        value={jd}
        onChange={(e) => setJd(e.target.value)}
      />

      <div className="flex flex-wrap items-center gap-4">
        <Button onClick={onTailor} disabled={busy !== null || !jd.trim()}>
          {busy === "tailor" ? "Analyzing…" : "Analyze match"}
        </Button>
        <Button variant="outline" onClick={onDownload} disabled={busy !== null}>
          {busy === "build" ? "Building…" : "Download PDF"}
        </Button>
        <label className="flex items-center gap-2 text-sm text-muted">
          <input type="checkbox" checked={ai} onChange={(e) => setAi(e.target.checked)} />
          Rephrase with local LLM
        </label>
      </div>

      <Card>
        <CardTitle>Cover letter</CardTitle>
        <CardSub className="mt-1">
          Uses the job description above (optional) plus the role and company below.
        </CardSub>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <Input
            className="max-w-xs"
            placeholder="Role title (e.g. Software Engineer Intern)"
            value={role}
            onChange={(e) => setRole(e.target.value)}
          />
          <Input
            className="max-w-xs"
            placeholder="Company / department"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
          />
          <Button variant="outline" onClick={onCover} disabled={busy !== null}>
            {busy === "cover" ? "Building…" : "Download cover letter"}
          </Button>
        </div>
      </Card>

      {message && <p className="text-sm text-amber-600">{message}</p>}

      {result && (
        <Card>
          <CardTitle>ATS keyword coverage: {Math.round(result.score * 100)}%</CardTitle>
          <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-stone-200">
            <div
              className="h-full bg-brand transition-all"
              style={{ width: `${Math.round(result.score * 100)}%` }}
            />
          </div>
          {result.matched_keywords.length > 0 && (
            <div className="mt-4">
              <CardSub>Matched</CardSub>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {result.matched_keywords.slice(0, 30).map((k) => (
                  <span key={k} className="rounded bg-emerald-900/60 px-2 py-0.5 text-xs text-emerald-300">
                    {k}
                  </span>
                ))}
              </div>
            </div>
          )}
          {result.missing_keywords.length > 0 && (
            <div className="mt-4">
              <CardSub>Missing — consider adding these</CardSub>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {result.missing_keywords.slice(0, 30).map((k) => (
                  <span key={k} className="rounded bg-amber-900/50 px-2 py-0.5 text-xs text-amber-300">
                    {k}
                  </span>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
