"use client";

import { useEffect, useMemo, useState } from "react";

import { type Column, DataTable } from "@/components/DataTable";
import { LocalSetupGuide } from "@/components/LocalSetupGuide";
import { Card, CardSub, CardTitle } from "@/components/ui/card";
import {
  deleteDocument,
  documentFileUrl,
  type DocumentKind,
  type GeneratedDocument,
  getDocuments,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const KIND_LABEL: Record<DocumentKind, string> = {
  resume: "Résumé",
  cover_letter: "Cover letter",
};

export default function ResumesPage() {
  const [docs, setDocs] = useState<GeneratedDocument[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [apiDown, setApiDown] = useState(false);
  const [kind, setKind] = useState<DocumentKind | "all">("all");
  const [query, setQuery] = useState("");

  useEffect(() => {
    getDocuments()
      .then((list) => setDocs(list))
      .catch(() => setApiDown(true))
      .finally(() => setLoaded(true));
  }, []);

  // getDocuments returns [] on API-down; probe once to distinguish empty vs down.
  useEffect(() => {
    if (loaded && docs.length === 0) {
      fetch(`${process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000"}/api/documents`, {
        cache: "no-store",
      })
        .then((r) => {
          if (!r.ok) setApiDown(true);
        })
        .catch(() => setApiDown(true));
    }
  }, [loaded, docs.length]);

  async function onDelete(id: string) {
    setDocs((prev) => prev.filter((d) => d.id !== id));
    await deleteDocument(id);
  }

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return docs.filter((d) => {
      if (kind !== "all" && d.kind !== kind) return false;
      if (!q) return true;
      return [d.title, d.employer, d.label, d.provider].join(" ").toLowerCase().includes(q);
    });
  }, [docs, kind, query]);

  const columns: Column<GeneratedDocument>[] = [
    {
      key: "title",
      header: "Document",
      sortValue: (d) => (d.title || d.label).toLowerCase(),
      render: (d) => (
        <div className="min-w-0">
          <div className="font-medium text-ink">{d.title || d.label || "Untitled"}</div>
          {d.employer && <div className="text-xs text-muted">{d.employer}</div>}
        </div>
      ),
    },
    {
      key: "kind",
      header: "Type",
      sortValue: (d) => d.kind,
      render: (d) => (
        <span className="rounded-full bg-bg px-2.5 py-0.5 text-xs font-medium text-muted">
          {KIND_LABEL[d.kind]}
        </span>
      ),
    },
    {
      key: "ats_score",
      header: "ATS",
      sortValue: (d) => d.ats_score ?? -1,
      render: (d) =>
        d.ats_score === null || d.ats_score === undefined ? (
          <span className="text-muted">—</span>
        ) : (
          <span
            className={cn(
              "font-medium",
              d.ats_score >= 0.7 ? "text-emerald-700" : d.ats_score >= 0.4 ? "text-amber-600" : "text-red-600",
            )}
          >
            {Math.round(d.ats_score * 100)}%
          </span>
        ),
    },
    {
      key: "provider",
      header: "Engine",
      sortValue: (d) => d.provider.toLowerCase(),
      render: (d) => (
        <span className="text-xs text-muted">
          {d.provider || "deterministic"}
          {d.tailored && <span className="ml-1 text-brand">· AI</span>}
        </span>
      ),
    },
    {
      key: "created_at",
      header: "Created",
      sortValue: (d) => d.created_at,
      render: (d) => <span className="text-xs text-muted">{d.created_at.slice(0, 10)}</span>,
    },
    {
      key: "actions",
      header: "",
      headerClassName: "w-28",
      render: (d) => (
        <div className="flex items-center gap-3">
          <a
            href={documentFileUrl(d.id)}
            target="_blank"
            rel="noopener noreferrer"
            className="text-brand hover:underline"
            title="Download PDF"
          >
            ↓ PDF
          </a>
          <button
            onClick={() => onDelete(d.id)}
            className="text-muted transition-colors hover:text-red-600"
            title="Delete"
            aria-label={`Delete ${d.title || d.label}`}
          >
            ✕
          </button>
        </div>
      ),
    },
  ];

  if (!loaded) {
    return <div className="mx-auto max-w-5xl px-5 py-20 text-center text-muted">Loading…</div>;
  }
  if (apiDown) {
    return (
      <div className="mx-auto max-w-3xl px-5 py-16">
        <LocalSetupGuide context="Your résumé & cover-letter library" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-5 py-12">
      <header className="mb-6">
        <h1 className="text-3xl font-bold tracking-tight text-ink">Document library</h1>
        <p className="mt-1 text-sm text-muted">
          Every résumé and cover letter the engine has built — tailored versions, ATS scores, and
          the model that wrote them. Your{" "}
          <a href="/profile" className="text-brand hover:underline">primary résumé</a> lives on the
          profile page.
        </p>
      </header>

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="flex gap-1.5">
          {(["all", "resume", "cover_letter"] as const).map((k) => (
            <button
              key={k}
              onClick={() => setKind(k)}
              className={cn(
                "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                kind === k
                  ? "border-ink bg-ink text-white"
                  : "border-line bg-surface text-muted hover:border-ink/30 hover:text-ink",
              )}
            >
              {k === "all" ? "All" : KIND_LABEL[k]}
            </button>
          ))}
        </div>
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search title, employer, engine…"
          className="h-10 w-full max-w-sm rounded-lg border border-line bg-surface px-3 text-sm text-ink shadow-sm placeholder:text-muted/70 focus-visible:border-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/30"
        />
        <span className="ml-auto text-sm text-muted">{visible.length} shown</span>
      </div>

      <DataTable
        rows={visible}
        columns={columns}
        getRowKey={(d) => d.id}
        initialSortKey="created_at"
        initialSortDir="desc"
        empty={
          <Card className="grid min-h-[12rem] place-items-center text-center">
            <div className="max-w-xs space-y-1">
              <CardTitle>No documents yet</CardTitle>
              <CardSub>
                Build a tailored résumé or cover letter in the{" "}
                <a href="/studio" className="text-brand hover:underline">Studio</a> — every PDF you
                generate is saved here automatically.
              </CardSub>
            </div>
          </Card>
        }
      />
    </div>
  );
}
