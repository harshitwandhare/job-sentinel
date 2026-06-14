"use client";

import { useCallback, useEffect, useState } from "react";

import { LocalSetupGuide } from "@/components/LocalSetupGuide";
import { SearchResultCard } from "@/components/SearchResultCard";
import { Button } from "@/components/ui/button";
import { Card, CardSub, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import {
  fetchCompanyBoard,
  getSources,
  type JobPosting,
  type JobQuery,
  type JobSourceStatus,
  searchJobs,
  type SearchResponse,
  type SourceConfigKeys,
  updateSourcesConfig,
} from "@/lib/api";
import { cn } from "@/lib/utils";

type Mode = "search" | "company";

const REMOTE_OPTIONS = [
  { label: "Anywhere", value: "any" },
  { label: "Remote only", value: "remote" },
  { label: "On-site", value: "onsite" },
] as const;

const DATE_OPTIONS = [
  { label: "Any time", value: "" },
  { label: "Past 24 hours", value: "1" },
  { label: "Past week", value: "7" },
  { label: "Past month", value: "30" },
];

const JOB_TYPES = ["", "Full-time", "Part-time", "Contract", "Internship", "Temporary"];
const SENIORITY = ["", "Internship", "Entry", "Mid", "Senior", "Director", "Executive"];

export default function SearchPage() {
  const [mode, setMode] = useState<Mode>("search");
  const [apiDown, setApiDown] = useState(false);
  const [loaded, setLoaded] = useState(false);

  // Filters
  const [keywords, setKeywords] = useState("");
  const [location, setLocation] = useState("");
  const [remote, setRemote] = useState<(typeof REMOTE_OPTIONS)[number]["value"]>("any");
  const [jobType, setJobType] = useState("");
  const [seniority, setSeniority] = useState("");
  const [salaryMin, setSalaryMin] = useState("");
  const [datePosted, setDatePosted] = useState("");
  const [radiusKm, setRadiusKm] = useState("");
  const [company, setCompany] = useState("");
  const [limit, setLimit] = useState("50");

  // Sources
  const [sources, setSources] = useState<JobSourceStatus[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  // Results
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState<JobPosting[] | null>(null);
  const [resp, setResp] = useState<SearchResponse | null>(null);
  const [message, setMessage] = useState("");

  // Company mode
  const [ats, setAts] = useState("greenhouse");
  const [slug, setSlug] = useState("");

  useEffect(() => {
    getSources().then((s) => {
      if (s === null) {
        setApiDown(true);
      } else {
        setSources(s.sources);
        setSelected(new Set(s.sources.filter((x) => x.enabled && x.configured).map((x) => x.id)));
      }
      setLoaded(true);
    });
  }, []);

  const runSearch = useCallback(async () => {
    setSearching(true);
    setMessage("");
    const query: JobQuery = {
      keywords: keywords.trim(),
      location: location.trim(),
      remote: remote === "any" ? null : remote === "remote",
      job_type: jobType,
      seniority,
      salary_min: salaryMin ? Number(salaryMin) : null,
      date_posted_days: datePosted ? Number(datePosted) : null,
      radius_km: radiusKm ? Number(radiusKm) : null,
      company: company.trim(),
      limit: Number(limit),
      sources: selected.size > 0 ? [...selected] : undefined,
    };
    const r = await searchJobs(query);
    setSearching(false);
    if (r === null) {
      setMessage("Couldn't reach the local API. Run `job-sentinel serve`.");
      setResults(null);
      setResp(null);
      return;
    }
    setResp(r);
    setResults(r.results);
  }, [
    keywords, location, remote, jobType, seniority, salaryMin, datePosted, radiusKm, company, limit, selected,
  ]);

  async function runCompany() {
    if (!slug.trim()) return;
    setSearching(true);
    setMessage("");
    const r = await fetchCompanyBoard(ats, slug.trim());
    setSearching(false);
    if (r === null) {
      setMessage(`No board found for ${ats}/${slug.trim()} — check the slug.`);
      setResults(null);
      setResp(null);
      return;
    }
    setResults(r.results);
    setResp(null);
  }

  if (!loaded) {
    return (
      <div className="mx-auto max-w-3xl px-5 py-20 text-center text-muted">Loading sources…</div>
    );
  }
  if (apiDown) {
    return (
      <div className="mx-auto max-w-3xl px-5 py-16">
        <LocalSetupGuide context="Job search across the web" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-5 py-12">
      <header className="mb-6">
        <h1 className="text-3xl font-bold tracking-tight text-ink">Find jobs anywhere</h1>
        <p className="mt-1 text-sm text-muted">
          Search free, legal job sources — remote boards, company ATS pages, and more — all from
          your machine. Track any result into your pipeline in one click.
        </p>
      </header>

      {/* Mode switch */}
      <div className="mb-5 inline-flex rounded-lg border border-line bg-surface p-0.5 text-sm">
        {(["search", "company"] as Mode[]).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={cn(
              "rounded-md px-3.5 py-1.5 font-medium transition-colors",
              mode === m ? "bg-ink text-white" : "text-muted hover:text-ink",
            )}
          >
            {m === "search" ? "Search" : "Follow a company"}
          </button>
        ))}
      </div>

      {mode === "search" ? (
        <div className="grid gap-6 lg:grid-cols-[300px_1fr]">
          {/* Filters */}
          <aside className="space-y-4">
            <Card className="space-y-3">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void runSearch();
                }}
                className="space-y-3"
              >
                <Input
                  placeholder="Keywords (e.g. python, ML)"
                  value={keywords}
                  onChange={(e) => setKeywords(e.target.value)}
                />
                <Input
                  placeholder="Location (city, country)"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                />
                <Select value={remote} onChange={(e) => setRemote(e.target.value as typeof remote)}>
                  {REMOTE_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </Select>
                <div className="grid grid-cols-2 gap-2">
                  <Select value={jobType} onChange={(e) => setJobType(e.target.value)}>
                    {JOB_TYPES.map((t) => (
                      <option key={t} value={t}>{t || "Any type"}</option>
                    ))}
                  </Select>
                  <Select value={seniority} onChange={(e) => setSeniority(e.target.value)}>
                    {SENIORITY.map((s) => (
                      <option key={s} value={s}>{s || "Any level"}</option>
                    ))}
                  </Select>
                </div>
                <Select value={datePosted} onChange={(e) => setDatePosted(e.target.value)}>
                  {DATE_OPTIONS.map((d) => (
                    <option key={d.value} value={d.value}>{d.label}</option>
                  ))}
                </Select>
                <div className="grid grid-cols-2 gap-2">
                  <Input
                    type="number"
                    placeholder="Min salary"
                    value={salaryMin}
                    onChange={(e) => setSalaryMin(e.target.value)}
                  />
                  <Input
                    type="number"
                    placeholder="Radius km"
                    value={radiusKm}
                    onChange={(e) => setRadiusKm(e.target.value)}
                    disabled={!location.trim()}
                  />
                </div>
                <Input placeholder="Company" value={company} onChange={(e) => setCompany(e.target.value)} />
                <div className="flex items-center gap-2">
                  <Select className="w-24" value={limit} onChange={(e) => setLimit(e.target.value)}>
                    {["25", "50", "100"].map((n) => (
                      <option key={n} value={n}>{n}</option>
                    ))}
                  </Select>
                  <Button type="submit" disabled={searching || selected.size === 0} className="flex-1">
                    {searching ? "Searching…" : "Search"}
                  </Button>
                </div>
                {selected.size === 0 && (
                  <p className="text-xs text-amber-600">Enable at least one source below.</p>
                )}
              </form>
            </Card>

            <SourcesPanel
              sources={sources}
              selected={selected}
              onToggleSelected={(id) =>
                setSelected((prev) => {
                  const next = new Set(prev);
                  if (next.has(id)) next.delete(id);
                  else next.add(id);
                  return next;
                })
              }
              onSaved={(updated) => {
                setSources(updated);
                setSelected(new Set(updated.filter((x) => x.enabled && x.configured).map((x) => x.id)));
              }}
            />
          </aside>

          {/* Results */}
          <section className="min-w-0">
            <ResultsArea
              searching={searching}
              results={results}
              resp={resp}
              message={message}
              emptyHint="Set your filters and hit Search to pull live listings."
            />
          </section>
        </div>
      ) : (
        <div className="space-y-5">
          <Card className="space-y-3">
            <CardTitle>Follow a company&rsquo;s job board</CardTitle>
            <CardSub>
              Pulls live openings straight from a company&rsquo;s public ATS — no key, no scraping.
              Find the slug in the board URL (e.g. <code>boards.greenhouse.io/&lt;slug&gt;</code>).
            </CardSub>
            <form
              className="flex flex-wrap items-center gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                void runCompany();
              }}
            >
              <Select className="w-40" value={ats} onChange={(e) => setAts(e.target.value)}>
                <option value="greenhouse">Greenhouse</option>
                <option value="lever">Lever</option>
                <option value="ashby">Ashby</option>
              </Select>
              <Input
                className="max-w-xs flex-1"
                placeholder="company slug (e.g. stripe)"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
              />
              <Button type="submit" disabled={searching || !slug.trim()}>
                {searching ? "Fetching…" : "Fetch openings"}
              </Button>
            </form>
          </Card>
          <ResultsArea
            searching={searching}
            results={results}
            resp={resp}
            message={message}
            emptyHint="Enter a company slug to see its current openings."
          />
        </div>
      )}
    </div>
  );
}

function ResultsArea({
  searching,
  results,
  resp,
  message,
  emptyHint,
}: {
  searching: boolean;
  results: JobPosting[] | null;
  resp: SearchResponse | null;
  message: string;
  emptyHint: string;
}) {
  if (message) return <p className="text-sm text-amber-600">{message}</p>;
  if (searching && !results) {
    return (
      <div className="space-y-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-28 animate-pulse rounded-2xl border border-line bg-surface" />
        ))}
      </div>
    );
  }
  if (results === null) {
    return (
      <Card className="grid min-h-[12rem] place-items-center text-center">
        <CardSub className="max-w-xs">{emptyHint}</CardSub>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {resp && (resp.errors.length > 0 || Object.keys(resp.counts).length > 0) && (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
          {Object.entries(resp.counts).map(([sid, n]) => (
            <span key={sid} className="text-muted">
              <span className="font-medium text-ink">{sid}</span> {n}
            </span>
          ))}
          {resp.errors.map((e) => (
            <span key={e.source} className="text-amber-600" title={e.detail}>
              {e.source}: failed
            </span>
          ))}
        </div>
      )}
      {results.length === 0 ? (
        <Card className="grid min-h-[10rem] place-items-center text-center">
          <CardSub>No matches. Try broader keywords or a different source.</CardSub>
        </Card>
      ) : (
        results.map((j, i) => <SearchResultCard key={`${j.posting_id}-${i}`} job={j} index={i} />)
      )}
    </div>
  );
}

function SourcesPanel({
  sources,
  selected,
  onToggleSelected,
  onSaved,
}: {
  sources: JobSourceStatus[];
  selected: Set<string>;
  onToggleSelected: (id: string) => void;
  onSaved: (updated: JobSourceStatus[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const [enabled, setEnabled] = useState<Set<string>>(
    () => new Set(sources.filter((s) => s.enabled).map((s) => s.id)),
  );
  const [keys, setKeys] = useState<SourceConfigKeys>({});
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");

  async function save() {
    setSaving(true);
    setStatus("Saving…");
    const nonEmptyKeys = Object.fromEntries(
      Object.entries(keys).filter(([, v]) => v !== undefined && v !== ""),
    ) as SourceConfigKeys;
    const r = await updateSourcesConfig({
      enabled_sources: [...enabled],
      keys: Object.keys(nonEmptyKeys).length ? nonEmptyKeys : undefined,
    });
    setSaving(false);
    if (r) {
      setStatus("Saved ✓");
      setKeys({});
      onSaved(r.sources);
      setTimeout(() => setStatus(""), 2000);
    } else {
      setStatus("Save failed — is the API running?");
    }
  }

  const keyed = sources.filter((s) => s.requires_key);

  return (
    <Card className="space-y-2">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between text-left"
        aria-expanded={open}
      >
        <CardTitle className="text-base">Sources ({selected.size} active)</CardTitle>
        <span aria-hidden="true" className="text-muted">{open ? "−" : "+"}</span>
      </button>

      {/* Quick include/exclude for this search */}
      <div className="flex flex-wrap gap-1.5">
        {sources
          .filter((s) => s.enabled && s.configured)
          .map((s) => (
            <button
              key={s.id}
              onClick={() => onToggleSelected(s.id)}
              className={cn(
                "rounded-full border px-2.5 py-0.5 text-xs transition-colors",
                selected.has(s.id)
                  ? "border-brand bg-brand/10 text-brand"
                  : "border-line text-muted hover:text-ink",
              )}
            >
              {s.label}
            </button>
          ))}
      </div>

      {open && (
        <div className="space-y-3 border-t border-line pt-3">
          <div className="space-y-1.5">
            {sources.map((s) => (
              <label key={s.id} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={enabled.has(s.id)}
                  onChange={() =>
                    setEnabled((prev) => {
                      const next = new Set(prev);
                      if (next.has(s.id)) next.delete(s.id);
                      else next.add(s.id);
                      return next;
                    })
                  }
                />
                <span className="text-ink">{s.label}</span>
                {s.is_scraper && (
                  <span className="rounded bg-amber-100 px-1.5 text-[10px] font-medium text-amber-700">
                    scraper
                  </span>
                )}
                {s.requires_key && !s.configured && (
                  <span className="text-[11px] text-muted">needs key</span>
                )}
              </label>
            ))}
          </div>

          {enabled.has("jobspy") && (
            <p className="rounded-md bg-amber-50 px-2.5 py-1.5 text-[11px] text-amber-700">
              JobSpy scrapes job boards directly — this may violate their terms of service. You
              assume responsibility for how you use it.
            </p>
          )}

          {keyed.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted">API keys (stored locally, never shown again)</p>
              <Input
                placeholder="Adzuna app id"
                value={keys.ADZUNA_APP_ID ?? ""}
                onChange={(e) => setKeys((k) => ({ ...k, ADZUNA_APP_ID: e.target.value }))}
              />
              <Input
                type="password"
                placeholder="Adzuna app key"
                value={keys.ADZUNA_APP_KEY ?? ""}
                onChange={(e) => setKeys((k) => ({ ...k, ADZUNA_APP_KEY: e.target.value }))}
              />
              <Input
                type="password"
                placeholder="USAJobs API key"
                value={keys.USAJOBS_API_KEY ?? ""}
                onChange={(e) => setKeys((k) => ({ ...k, USAJOBS_API_KEY: e.target.value }))}
              />
              <Input
                placeholder="USAJobs email"
                value={keys.USAJOBS_EMAIL ?? ""}
                onChange={(e) => setKeys((k) => ({ ...k, USAJOBS_EMAIL: e.target.value }))}
              />
            </div>
          )}

          <div className="flex items-center gap-3">
            <Button size="sm" onClick={save} disabled={saving}>
              {saving ? "Saving…" : "Save sources"}
            </Button>
            {status && <span className="text-xs text-muted">{status}</span>}
          </div>
        </div>
      )}
    </Card>
  );
}
