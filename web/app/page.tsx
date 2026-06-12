import Link from "next/link";

import { Hero } from "@/components/Hero";
import { Pipeline } from "@/components/Pipeline";
import { Reveal } from "@/components/Reveal";
import { TiltCard } from "@/components/TiltCard";

const qualityBadges = [
  "mypy --strict",
  "83% test coverage",
  "185+ tests",
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

const engineering = [
  { k: "7", v: "CI gates on every PR", d: "lint · format · types · tests ×2 · secrets · supply chain · web build" },
  { k: "0", v: "known CVEs shipped", d: "pip-audit scans the dependency tree; strong-copyleft licenses are blocked" },
  { k: "100%", v: "strict-typed Python", d: "mypy --strict across the whole src tree, pydantic v2 at every boundary" },
  { k: "4", v: "releases on PyPI", d: "tag → build → GitHub Release → PyPI, fully automated and secret-gated" },
];

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

      {/* How it works */}
      <section className="bg-grid border-b border-line">
        <div className="mx-auto max-w-6xl px-6 py-24">
          <Reveal>
            <p className="font-mono text-sm font-medium uppercase tracking-widest text-brand">How it works</p>
            <h2 className="mt-3 max-w-2xl text-3xl font-bold tracking-tight text-ink sm:text-4xl">
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
        <div className="mx-auto max-w-6xl px-6 py-24">
          <Reveal>
            <p className="font-mono text-sm font-medium uppercase tracking-widest text-brand">Capabilities</p>
            <h2 className="mt-3 max-w-2xl text-3xl font-bold tracking-tight text-ink sm:text-4xl">
              Everything between "new posting" and "submitted".
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

      {/* Engineering quality — the FAANG section. */}
      <section data-nav-theme="dark" className="relative overflow-hidden bg-night text-white">
        <div className="bg-grid-dark absolute inset-0" aria-hidden="true" />
        <div className="relative mx-auto max-w-6xl px-6 py-24">
          <Reveal>
            <p className="font-mono text-sm font-medium uppercase tracking-widest text-brand-400">
              Built like production software
            </p>
            <h2 className="mt-3 max-w-2xl text-3xl font-bold tracking-tight sm:text-4xl">
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
        <div className="mx-auto max-w-6xl px-6 py-24">
          <div className="grid items-center gap-10 lg:grid-cols-2">
            <Reveal>
              <p className="font-mono text-sm font-medium uppercase tracking-widest text-brand">Private by default</p>
              <h2 className="mt-3 text-3xl font-bold tracking-tight text-ink sm:text-4xl">
                Your career data never leaves your machine.
              </h2>
              <p className="mt-4 leading-relaxed text-muted">
                Credentials live in a local .env. Sessions, history, and your profile live in local
                files. The AI runs on your own GPU via Ollama. There is no cloud, no telemetry, and
                no API key — by architecture, not by promise.
              </p>
            </Reveal>
            <Reveal delay={0.1}>
              <div className="rounded-2xl border border-line bg-surface p-8 shadow-card">
                <h3 className="text-xl font-semibold tracking-tight text-ink">Start in two minutes</h3>
                <pre className="mt-4 overflow-x-auto rounded-xl bg-night p-4 font-mono text-sm leading-7 text-stone-300">
                  <code>{`pip install job-sentinel
job-sentinel resume init   # your universal profile
job-sentinel serve         # this web app`}</code>
                </pre>
                <div className="mt-6 flex flex-wrap gap-3">
                  <Link
                    href="/profile/edit"
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
