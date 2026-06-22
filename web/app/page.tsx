import Link from "next/link";

import { Hero } from "@/components/Hero";
import { Pipeline } from "@/components/Pipeline";
import { Reveal } from "@/components/Reveal";
import { TiltCard } from "@/components/TiltCard";

const qualityBadges = [
  "mypy --strict",
  "450+ tests",
  "eslint + vitest",
  "reproducible builds (uv.lock)",
  "ruff lint + format",
  "gitleaks secret scan",
  "pip-audit CVE scan",
  "license compliance",
  "Docker ready",
  "Conventional Commits",
  "trunk-based PRs",
  "Published on PyPI",
  "MIT licensed",
];

const features: { title: string; body: string; span?: string; mono?: string }[] = [
  {
    title: "Local LLM tailoring",
    body: "An Ollama-served model rewrites your bullets toward each posting under a strict no-fabrication contract — output is JSON-validated, and anything off keeps your original words. Semantic embeddings rank what leads.",
    span: "lg:col-span-2",
    mono: "resume build --ai --semantic",
  },
  {
    title: "ATS-clean PDFs",
    body: "Single-column LaTeX compiled with Tectonic: real selectable text, standard fonts, parser-safe structure — with the .tex saved next to it.",
    mono: "resume build -o resume.pdf",
  },
  {
    title: "Deadline radar",
    body: "Free-form deadline parsing flags anything closing within your window, in alerts and on demand.",
    mono: "/deadlines",
  },
  {
    title: "Two alert channels",
    body: "Rich Telegram messages with inline commands, plus optional SMTP email digests — both fan out from one scheduler.",
    mono: "telegram + email",
  },
  {
    title: "Pluggable portals",
    body: "Each portal is one adapter file behind a typed interface. Gated university portals included — sessions captured once, reused headlessly.",
    span: "lg:col-span-2",
    mono: "SITE_ADAPTER=12twenty",
  },
];

const problem = [
  {
    stat: "242",
    label: "applications per opening",
    body: "Triple the 2021 volume. Spray-and-pray is dead — the edge is applying early, with a résumé that actually matches.",
    source: { href: "https://huntr.co/research/job-search-trends-q1-2026", name: "Huntr Q1 2026" },
  },
  {
    stat: "93%",
    label: "have applied to a ghost job",
    body: "Listings that were never real cost ~9 hours each. Watching real portals you already trust beats scrolling aggregators.",
    source: {
      href: "https://www.cpapracticeadvisor.com/2026/04/30/ghost-jobs-still-haunting-67-of-job-seekers-report-finds/182536/",
      name: "MyPerfectResume 2026",
    },
  },
  {
    stat: "66%",
    label: "rejected by an AI, silently",
    body: "Machines read your résumé before any human does. ATS-clean structure and keyword coverage aren't optional anymore.",
    source: { href: "https://enhancv.com/blog/ai-hiring-statistics/", name: "Enhancv 2026" },
  },
];

const comparison: {
  name: string;
  openSource: boolean;
  local: boolean;
  free: string;
  monitoring: boolean;
  note: string;
}[] = [
  {
    name: "Job Sentinel",
    openSource: true,
    local: true,
    free: "Free forever",
    monitoring: true,
    note: "One pipeline: watch → track → tailor → apply",
  },
  {
    name: "Simplify / Teal / Huntr",
    openSource: false,
    local: false,
    free: "Freemium",
    monitoring: false,
    note: "Cloud SaaS — your career data lives on their servers",
  },
  {
    name: "AIHawk (archived May 2026)",
    openSource: true,
    local: false,
    free: "Cloud API keys",
    monitoring: false,
    note: "Auto-apply bot — project archived; LinkedIn ToS ban risk",
  },
  {
    name: "AI auto-apply bots",
    openSource: true,
    local: false,
    free: "Cloud API keys",
    monitoring: false,
    note: "Mass-submit on LinkedIn — ToS violations, account bans",
  },
  {
    name: "Resume builders (OSS)",
    openSource: true,
    local: false,
    free: "Free + API keys",
    monitoring: false,
    note: "Documents only — no portal watching, no tracking",
  },
];

const engineering = [
  { k: "9", v: "CI gates on every PR", d: "lint · types · tests ×3 · secrets · supply chain · web lint+test+build · scorecard" },
  { k: "0", v: "known CVEs shipped", d: "pip-audit scans the dependency tree; strong-copyleft licenses are blocked" },
  { k: "100%", v: "strict-typed Python", d: "mypy --strict across the whole src tree, pydantic v2 at every boundary" },
  { k: "4", v: "releases on PyPI", d: "tag → build → GitHub Release → PyPI, fully automated and secret-gated" },
];

function Mark({ ok }: { ok: boolean }) {
  return ok ? (
    <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-emerald-100 text-xs font-bold text-emerald-700">
      ✓<span className="sr-only">Yes</span>
    </span>
  ) : (
    <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-stone-100 text-xs text-stone-400">
      —<span className="sr-only">No</span>
    </span>
  );
}

export default function HomePage() {
  return (
    <>
      <Hero />

      {/* Quality marquee — the receipts, scrolling. */}
      <section aria-label="Engineering quality badges" className="border-b border-line bg-surface py-5">
        <div className="relative overflow-hidden">
          <div className="animate-marquee flex w-max gap-3 motion-reduce:animate-none motion-reduce:flex-wrap motion-reduce:justify-center">
            {[...qualityBadges, ...qualityBadges].map((b, i) => (
              <span
                key={`${b}-${i}`}
                aria-hidden={i >= qualityBadges.length}
                className="whitespace-nowrap rounded-full border border-line bg-bg px-4 py-1.5 font-mono text-xs text-muted"
              >
                {b}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* The problem — why this exists */}
      <section className="border-b border-line bg-surface">
        <div className="mx-auto max-w-6xl px-5 py-16 sm:px-6 sm:py-24">
          <Reveal>
            <p className="font-mono text-sm font-medium uppercase tracking-widest text-brand">
              The 2026 job market
            </p>
            <h2 className="mt-3 max-w-2xl text-2xl font-bold tracking-tight text-ink sm:text-4xl">
              The job hunt broke. Tools should catch up.
            </h2>
          </Reveal>
          <div className="mt-12 grid gap-5 sm:grid-cols-3">
            {problem.map((p, i) => (
              <Reveal key={p.label} delay={i * 0.08}>
                <div className="h-full rounded-2xl border border-line bg-bg p-6">
                  <p className="text-5xl font-bold tracking-tight text-ink">{p.stat}</p>
                  <p className="mt-1.5 font-medium text-ink">{p.label}</p>
                  <p className="mt-3 text-sm leading-relaxed text-muted">{p.body}</p>
                  <a
                    href={p.source.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-3 inline-block text-xs text-muted/70 underline-offset-2 hover:text-brand hover:underline"
                  >
                    {p.source.name} ↗
                  </a>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="bg-grid border-b border-line">
        <div className="mx-auto max-w-6xl px-5 py-16 sm:px-6 sm:py-24">
          <Reveal>
            <p className="font-mono text-sm font-medium uppercase tracking-widest text-brand">How it works</p>
            <h2 className="mt-3 max-w-2xl text-2xl font-bold tracking-tight text-ink sm:text-4xl">
              From posting detected to PDF in hand — one pipeline.
            </h2>
          </Reveal>
          <div className="mt-14">
            <Pipeline />
          </div>
        </div>
      </section>

      {/* Feature bento */}
      <section className="border-b border-line bg-bg">
        <div className="mx-auto max-w-6xl px-5 py-16 sm:px-6 sm:py-24">
          <Reveal>
            <p className="font-mono text-sm font-medium uppercase tracking-widest text-brand">Capabilities</p>
            <h2 className="mt-3 max-w-2xl text-2xl font-bold tracking-tight text-ink sm:text-4xl">
              Everything between &ldquo;new posting&rdquo; and &ldquo;submitted&rdquo;.
            </h2>
          </Reveal>
          <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((f, i) => (
              <Reveal key={f.title} delay={i * 0.06} className={f.span}>
                <TiltCard className="group relative h-full rounded-2xl border border-line bg-surface p-6 shadow-card">
                  <h3 className="text-lg font-semibold tracking-tight text-ink">{f.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted">{f.body}</p>
                  {f.mono && (
                    <code className="mt-4 inline-block rounded-md bg-night px-2.5 py-1 font-mono text-xs text-brand-400">
                      {f.mono}
                    </code>
                  )}
                </TiltCard>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Honest comparison — why local-first wins */}
      <section className="border-b border-line bg-surface">
        <div className="mx-auto max-w-6xl px-5 py-16 sm:px-6 sm:py-24">
          <Reveal>
            <p className="font-mono text-sm font-medium uppercase tracking-widest text-brand">
              The landscape
            </p>
            <h2 className="mt-3 max-w-2xl text-2xl font-bold tracking-tight text-ink sm:text-4xl">
              Plenty of tools do one piece. None of them are yours.
            </h2>
            <p className="mt-4 max-w-2xl text-muted">
              Trackers, builders, and auto-apply bots each solve a slice — in someone else&rsquo;s
              cloud, with your career data as the price. Job Sentinel is the integrated loop,
              running entirely on your machine.
            </p>
          </Reveal>
          <Reveal delay={0.1}>
            <div className="mt-10 overflow-x-auto rounded-2xl border border-line shadow-card">
              <table className="w-full min-w-[680px] border-collapse bg-bg text-left text-sm">
                <thead>
                  <tr className="border-b border-line bg-surface text-xs uppercase tracking-wider text-muted">
                    <th scope="col" className="px-5 py-3.5 font-medium">Tool</th>
                    <th scope="col" className="px-4 py-3.5 font-medium">Open source</th>
                    <th scope="col" className="px-4 py-3.5 font-medium">Data stays local</th>
                    <th scope="col" className="px-4 py-3.5 font-medium">Cost</th>
                    <th scope="col" className="px-4 py-3.5 font-medium">Portal monitoring</th>
                    <th scope="col" className="px-5 py-3.5 font-medium">The catch</th>
                  </tr>
                </thead>
                <tbody>
                  {comparison.map((row, i) => (
                    <tr
                      key={row.name}
                      className={
                        i === 0
                          ? "border-b border-line bg-brand/[0.04]"
                          : "border-b border-line last:border-b-0"
                      }
                    >
                      <th scope="row" className="px-5 py-4 font-semibold text-ink">
                        {row.name}
                        {i === 0 && (
                          <span className="ml-2 rounded-full bg-brand px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-white">
                            this
                          </span>
                        )}
                      </th>
                      <td className="px-4 py-4">
                        <Mark ok={row.openSource} />
                      </td>
                      <td className="px-4 py-4">
                        <Mark ok={row.local} />
                      </td>
                      <td className="px-4 py-4 text-muted">{row.free}</td>
                      <td className="px-4 py-4">
                        <Mark ok={row.monitoring} />
                      </td>
                      <td className="px-5 py-4 text-muted">{row.note}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Reveal>
        </div>
      </section>

      {/* AIHawk alternative — capture archived-project users */}
      <section id="aihawk-alternative" className="border-b border-line bg-bg">
        <div className="mx-auto max-w-6xl px-5 py-16 sm:px-6 sm:py-24">
          <Reveal>
            <p className="font-mono text-sm font-medium uppercase tracking-widest text-brand">
              Migrating from AIHawk?
            </p>
            <h2 className="mt-3 max-w-2xl text-2xl font-bold tracking-tight text-ink sm:text-4xl">
              AIHawk was archived. Your job search shouldn&rsquo;t be.
            </h2>
            <p className="mt-4 max-w-2xl leading-relaxed text-muted">
              AIHawk (29.9k stars) shut down in May 2026 after LinkedIn aggressively blocked
              mass auto-apply bots. Job Sentinel takes the opposite bet: quality over volume,
              local-first privacy, and a workflow that doesn&rsquo;t risk your account.
            </p>
          </Reveal>
          <div className="mt-12 grid gap-5 sm:grid-cols-3">
            {[
              {
                heading: "No auto-apply, by design",
                body: "AIHawk tried to submit hundreds of applications for you — and got burned. Job Sentinel helps you apply smarter: AI-tailored résumés, ATS scoring, and deadline radar so every application counts.",
              },
              {
                heading: "Your data, your machine",
                body: "AIHawk required cloud API keys and sent your résumé data through third-party services. Job Sentinel runs entirely on your hardware — SQLite locally, Ollama locally, no cloud.",
              },
              {
                heading: "A tool that won't disappear",
                body: "Open-source (MIT), published on PyPI, typed end-to-end, and built for longevity. No corporate dependency, no sudden shutdown — fork it, audit it, run it forever.",
              },
            ].map((item, i) => (
              <Reveal key={item.heading} delay={i * 0.08}>
                <div className="h-full rounded-2xl border border-line bg-surface p-6 shadow-card">
                  <div className="mb-3 inline-flex items-center gap-2">
                    <span className="inline-flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-brand/10 text-xs font-bold text-brand">
                      {i + 1}
                    </span>
                  </div>
                  <h3 className="text-base font-semibold tracking-tight text-ink">{item.heading}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted">{item.body}</p>
                </div>
              </Reveal>
            ))}
          </div>
          <Reveal delay={0.2}>
            <div className="mt-10 flex flex-wrap items-center gap-4">
              <a
                href="https://github.com/harshitwandhare/job-sentinel"
                className="rounded-lg bg-brand px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-brand-500"
              >
                Switch to Job Sentinel ↗
              </a>
              <span className="text-sm text-muted">
                <code className="mr-1.5 rounded bg-surface px-1.5 py-0.5 font-mono text-xs">pip install job-sentinel</code>
                — no sign-up required
              </span>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Engineering quality — the FAANG section. */}
      <section data-nav-theme="dark" className="relative overflow-hidden bg-night text-white">
        <div className="bg-grid-dark absolute inset-0" aria-hidden="true" />
        <div className="relative mx-auto max-w-6xl px-5 py-16 sm:px-6 sm:py-24">
          <Reveal>
            <p className="font-mono text-sm font-medium uppercase tracking-widest text-brand-400">
              Built like production software
            </p>
            <h2 className="mt-3 max-w-2xl text-2xl font-bold tracking-tight sm:text-4xl">
              Because the codebase is part of the product.
            </h2>
            <p className="mt-4 max-w-2xl text-stone-400">
              Open the repo and judge it the way a staff engineer would: typed end to end, tested,
              gated, documented (HLD, LLD, ADRs), released, and honest about its trade-offs.
            </p>
          </Reveal>
          <div className="mt-12 grid gap-px overflow-hidden rounded-2xl border border-white/10 bg-white/10 sm:grid-cols-2 lg:grid-cols-4">
            {engineering.map((e, i) => (
              <Reveal key={e.v} delay={i * 0.08}>
                <div className="h-full bg-night p-6">
                  <p className="text-4xl font-bold text-brand-400">{e.k}</p>
                  <p className="mt-2 font-medium text-white">{e.v}</p>
                  <p className="mt-1.5 text-xs leading-relaxed text-stone-400">{e.d}</p>
                </div>
              </Reveal>
            ))}
          </div>
          <Reveal delay={0.2}>
            <div className="mt-8 flex flex-wrap gap-4 text-sm">
              <a
                href="https://github.com/harshitwandhare/job-sentinel"
                className="rounded-lg border border-white/20 px-5 py-2.5 font-medium transition-colors hover:bg-white/10"
              >
                Read the source ↗
              </a>
              <a
                href="https://pypi.org/project/job-sentinel/"
                className="rounded-lg border border-white/20 px-5 py-2.5 font-medium transition-colors hover:bg-white/10"
              >
                pip install job-sentinel ↗
              </a>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Privacy + final CTA */}
      <section className="bg-bg">
        <div className="mx-auto max-w-6xl px-5 py-16 sm:px-6 sm:py-24">
          <div className="grid items-center gap-8 sm:gap-10 lg:grid-cols-2">
            <Reveal className="min-w-0">
              <p className="font-mono text-sm font-medium uppercase tracking-widest text-brand">Private by default</p>
              <h2 className="mt-3 text-2xl font-bold tracking-tight text-ink sm:text-4xl">
                Your career data never leaves your machine.
              </h2>
              <p className="mt-4 leading-relaxed text-muted">
                Credentials live in a local .env. Sessions, history, and your profile live in local
                files. The AI runs on your own GPU via Ollama. There is no cloud, no telemetry, and
                no API key — by architecture, not by promise.
              </p>
            </Reveal>
            <Reveal delay={0.1} className="min-w-0">
              <div className="rounded-2xl border border-line bg-surface p-5 shadow-card sm:p-8">
                <h3 className="text-xl font-semibold tracking-tight text-ink">Start in two minutes</h3>
                <pre className="mt-4 overflow-x-auto rounded-xl bg-night p-3 font-mono text-xs leading-6 text-stone-300 sm:p-4 sm:text-sm sm:leading-7">
                  <code>{`pip install job-sentinel
job-sentinel resume init   # your universal profile
job-sentinel web           # this web app`}</code>
                </pre>
                <div className="mt-6 flex flex-wrap gap-3">
                  <Link
                    href="/profile"
                    className="rounded-lg bg-brand px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-brand-500"
                  >
                    Build your profile
                  </Link>
                  <Link
                    href="/studio"
                    className="rounded-lg border border-line px-5 py-2.5 text-sm font-medium text-ink transition-colors hover:border-ink/30"
                  >
                    Try the studio
                  </Link>
                </div>
              </div>
            </Reveal>
          </div>
        </div>
      </section>
    </>
  );
}
