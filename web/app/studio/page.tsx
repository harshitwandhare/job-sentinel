"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardSub, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { buildResume, tailorResume, type TailorResult } from "@/lib/api";

export default function StudioPage() {
  const [jd, setJd] = useState("");
  const [ai, setAi] = useState(false);
  const [result, setResult] = useState<TailorResult | null>(null);
  const [busy, setBusy] = useState<"tailor" | "build" | null>(null);
  const [message, setMessage] = useState("");

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
    if (res.ok && res.blob) {
      const url = URL.createObjectURL(res.blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "resume.pdf";
      a.click();
      URL.revokeObjectURL(url);
    } else {
      setMessage(res.detail ?? "Build failed.");
    }
    setBusy(null);
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-5 py-12">
      <header>
        <h1 className="text-3xl font-bold text-ink">Résumé studio</h1>
        <p className="mt-1 text-muted">
          Paste a job description, see how your profile matches, and download a tailored PDF.
        </p>
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
