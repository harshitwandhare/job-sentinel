# Changelog

All notable changes to Job Sentinel are documented here.

This project follows [Conventional Commits](https://conventionalcommits.org)
and [Keep a Changelog](https://keepachangelog.com) format.

Versions follow [Semantic Versioning](https://semver.org):
- **MAJOR** — breaking changes
- **MINOR** — new features (backwards compatible)
- **PATCH** — bug fixes

---

## [Unreleased]

## [1.1.0] — 2026-06-22

Five new quality-of-life features across the job-search experience, shipped as
independent PRs over the week of June 17–22.

### Added

- **Wellfound job source** (`wellfound`). Public GraphQL endpoint — no API key
  required. Startup and tech jobs from AngelList/Wellfound enabled by default
  alongside RemoteOK, The Muse, Arbeitnow, and Himalayas. Salary text stripped
  of HTML before display. Covered by 5 unit tests (happy path, empty response,
  GraphQL error, HTTP 503, limit).

- **Ghost job signals on search cards.** Client-side heuristics flag postings
  that are likely stale (`⚠ Stale — posted 45+ days ago`) or suspiciously thin
  (`⚠ Thin listing — no salary, tags, or description`). Computed entirely
  in-browser from existing search data; no extra API calls.

- **ATS platform detection.** Apply-URL patterns identify 11 ATS platforms —
  Greenhouse, Lever, Ashby, Workday, SmartRecruiters, BambooHR, Jobvite, iCIMS,
  Taleo, Rippling, Breezy — and surface a colour-coded chip on every job card.
  14 tests cover all platforms, null/empty inputs, and unknown URLs.

- **Visa sponsorship detection.** Job description text is scanned for 6
  sponsorship-positive patterns and 7 negative patterns (negative checked first).
  Results surface as `Sponsors Visa` (green) or `No Sponsorship` (red) chips.
  10 unit tests covering signal priority and case-insensitivity.

- **Search keyboard shortcut + clear filters.** Press `/` from anywhere on the
  search page to focus the keywords field. A `⌘/` hint appears in the input.
  An inline "Clear filters" link appears whenever any filter is active.

### Fixed

- Supply-chain CI gate: patched msgpack 1.2.0→1.2.1, pydantic-settings
  2.14.1→2.14.2, pypdf 6.13.2→6.14.0 to resolve pre-existing CVEs that were
  blocking all Dependabot PRs.

- Landing page quality badge corrected to `450+ tests` (was `240+`).

## [1.0.0] — 2026-06-14

The release where Job Sentinel grows from a single-portal monitor into a full,
local-first **career platform** — search, match, track, and tailor, end to end,
on your own machine. Everything below ships typed (`mypy --strict`), tested
(450+ tests), and CI-gated (lint, types, tests ×3, CodeQL, secret scan,
supply-chain, license, web build).

### Added

- **Bring-your-own LLM providers.** Chat *and* embeddings now run on Ollama
  (zero-config default) **or** any OpenAI-compatible provider — OpenAI,
  OpenRouter, Groq, Gemini — configured independently. New `/settings` screen,
  `GET/PUT /api/llm/config`, and `POST /api/llm/test`. Keys live only in your
  local `.env`, are never logged, and are masked in the UI. No new runtime
  dependency. See [`docs/llm-providers.md`](docs/llm-providers.md).
- **Search jobs anywhere — a pluggable job-source layer.** Enabled by default
  with no keys: RemoteOK, The Muse, Arbeitnow, Himalayas. Opt-in with a free
  key: Adzuna, USAJobs. Opt-in scraper tier (off by default, ToS-disclaimed):
  JobSpy. Plus **follow-companies** via public Greenhouse/Lever/Ashby boards.
  Unified `JobQuery` filters, concurrent search with per-source failure
  isolation + dedupe. New `/search` UI, `sources` CLI, and `/api/sources*`
  routes. See [ADR 005](docs/adr/005-job-source-layer.md).
- **Application tracker + document library.** New `applications` and
  `generated_documents` tables (schema v2); a `/applications` pipeline table
  (saved → applied → interviewing → offer → rejected → archived) with inline
  stage editing, and a `/resumes` library of every generated résumé/cover letter
  with ATS scores and provenance. `apps` and `docs` CLI groups; full CRUD API.
- **RAG-grounded AI profile↔job match.** `POST /api/match` blends ATS keyword
  coverage with semantic-embedding similarity and an optional, no-fabrication
  LLM rationale (strengths/gaps), surfaced as an "AI match" affordance on job
  cards. Personalization is retrieval over your own data — never fine-tuned into
  weights, so it stays deletable. See [ADR 006](docs/adr/006-ai-personalization-and-data-strategy.md).
- **Career dashboard** (`/dashboard`) — pipeline funnel, closing-soon deadlines,
  source health, recent activity, quick actions.
- **Clip-to-track browser extension** (Chrome/Firefox, Manifest V3, no build
  step) — one click turns any posting into a tracked application via the local
  API. Tracking only; never auto-submits. See [`extension/`](extension/).
- **One-command installer** — `scripts/install.sh` and `scripts/install.ps1`
  (venv, deps, Playwright Chromium, `.env` scaffold, next-steps banner).
- **Hosted-demo mode** (`NEXT_PUBLIC_DEMO=1`) — every screen alive with bundled
  sample data, so the public demo needs no backend.
- **⌘K command palette**, the **profile rendered as a live résumé sheet**, and a
  README screenshot gallery + launch-post drafts.
- **Docs:** `compliance.md` (candidate-side tool; GDPR/CCPA posture), ADRs 005/006,
  and refreshed README / CLAUDE / HLD / LLD / web-ui.

### Changed

- Packaging polished for PyPI: clearer description, `Development Status :: Beta`,
  added Trove classifiers and keywords (twine-clean).
- Navigation decluttered to four primary tabs + a "More" menu; all dropdowns
  restyled to the theme; job cards reworked to a single action row.
- Docs now publish via the GitHub Pages **artifact flow** (retired the
  `gh-pages` branch, which was also breaking Vercel previews).
- North Star refreshed — the v1.0 "intelligence & polish" scope is shipped.

### Fixed

- Vercel preview deployments no longer fail on the docs branch.
- Command-palette cursor visibility and assorted UI spacing/polish.

### Security

- API responses and the ops status snapshot no longer surface exception/stack
  text (closes `py/stack-trace-exposure`). HTML/text cleaner is regex-free
  (no ReDoS). URL checks are host-anchored. CORS is tightened to localhost +
  extension origins. Secrets are `repr`-hidden and never echoed. **CodeQL: 0
  open alerts.**

## [0.8.0] — 2026-06-12

### Added
- **Public demo is live** at <https://job-sentinel.vercel.app> (Vercel free
  tier, auto-deployed from `main`), and the **docs site** at
  <https://harshitwandhare.github.io/job-sentinel/> (MkDocs Material on GitHub
  Pages, deployed on every docs change).
- **OpenSSF Scorecard** workflow (weekly + on push) with the badge in the
  README; `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1).
- Web UI now has **ESLint** (eslint-config-next, zero warnings) and a
  **vitest** suite, both gating CI alongside typecheck and the production
  build.

### Changed
- **Test coverage 77% → 87%**, CI gate raised to 80%: new suites cover the
  ops state machine (conflicts, worker outcomes, thread safety), the auth
  middleware across all three modes, 12twenty login/scrape flows against a
  fake browser page, and the Handshake adapter.
- CI runs on Python 3.11/3.12/3.13 with `uv sync --locked` (reproducible) and
  a least-privilege token; pre-commit hooks bumped (ruff 0.4→0.15, mypy
  1.10→2.1); dev dependencies deduplicated into PEP 735 `[dependency-groups]`;
  local `pytest` no longer pays the coverage tax (CI applies the gate).
- Hero terminal animation now derives every frame from a progress counter —
  garbled mid-typing frames are impossible.

### Fixed
- mypy strictness: removed the global `ignore_missing_imports` that masked
  typo'd imports (per-module overrides retained).
- Repaired UTF-8 mojibake a PowerShell round-trip introduced into workflow/
  client/env comments; `.env.example` restored byte-perfect.

## [0.7.0] — 2026-06-12

### Fixed
- **Chat assistant timeouts.** The configured Ollama model was a 22 GB
  36B-parameter tag that can't load on a 16 GB laptop; the default is now
  `llama3.2:3b` (2 GB, fits common 4 GB GPUs, ~4 s warm replies, no
  chain-of-thought rambling). Check yours with `job-sentinel resume doctor`.
- **Auth endpoints 422'd in 0.6.0** — `from __future__ import annotations`
  made FastAPI treat the locally-imported `Request` type as a query parameter.
  All `/api/auth/*` routes now work; the full flow (anonymous demo reads,
  gated writes, admin invite, member limits) is covered by live verification.

### Added
- **Per-job document generation**: every posting on the Jobs page has
  "Tailored résumé" and "Cover letter" buttons that build PDFs against that
  job's scraped description (local-AI polish when Ollama is running).
- **One command for everything**: `job-sentinel web --watch` starts the API,
  the web UI, and the recurring scrape watcher together.
- **Adaptive nav bar**: light text/borders over dark sections (hero,
  engineering), dark-on-light elsewhere — driven by `data-nav-theme="dark"`
  markers, smooth transition. Plus a Sign in / username entry in the nav.
- **Live terminal demo** in the hero: a self-typing replay of a real session
  (`session` → `scrape` → `resume build --ai`), pure CSS/JS, respects
  reduced-motion.

### Infrastructure
- Committed `uv.lock`; CI installs with `uv sync --locked` (reproducible
  builds) under a least-privilege `contents: read` token.
- Dependabot (uv + npm + GitHub Actions, weekly, grouped), PEP 561 `py.typed`
  marker, issue/PR templates, dev deps deduplicated into PEP 735
  `[dependency-groups]`.

## [0.6.0] — 2026-06-12

### Fixed
- **The "scrape returns 0 jobs" bug.** Root cause: a `viewId=<n>` saved-search
  reference in `PORTAL_JOBS_URL` made 12twenty respond *"you are not authorized"*
  and render an empty table while the session was perfectly valid. The adapter now
  strips `viewId` from the URL, and the logged-in check uses the real app-shell
  selectors (`#side-nav a.side-nav-link, a.logout`) instead of job rows — verified
  live: 16 Student Employment postings scraped end-to-end.
- Profile links (LinkedIn, GitHub, …) stored without a scheme no longer resolve as
  relative paths — all external links are normalised to `https://` and open in a
  new tab.

### Added
- **API-first 12twenty scraping**: the adapter captures the portal's internal JSON
  (`POST /Api/V2/job-postings/post-query`) while the page renders, then enriches
  every posting from the detail endpoint (`GET /Api/V2/job-postings/{id}`) — full
  description, salary, openings, industry, job function, work-study flag, contact,
  required documents, and applicant count, stored in `raw_data.detail`. DOM parsing
  remains as a fallback.
- **Session validity check** everywhere: `job-sentinel session` (CLI),
  `POST /api/ops/session/check` (API), and a "Check" button next to the session
  badge in the jobs UI — probes the portal's current-user endpoint headlessly and
  reports who you're signed in as.
- **Credential prefill on login**: `job-sentinel login` (and the UI Login button)
  now fills your portal username/password from `.env` the moment the form appears —
  you only clear the Cloudflare challenge and click Sign In. One shared
  implementation (`core/session.py`) backs both CLI and API.
- **Resume PDF import**: upload a resume on the Profile page (or run
  `job-sentinel resume import <pdf>`) and get a structured profile draft —
  local-LLM extraction when Ollama is up, deterministic heuristic parser otherwise.
  Nothing saves without your review.
- **Optional authentication** for shared/demo deployments (`AUTH_MODE=off|demo|required`):
  PBKDF2-hashed accounts in `data/users.json`, stateless HMAC tokens, admin-managed
  account creation (`job-sentinel users add/list/remove`, `POST /api/auth/*`), and a
  `/login` page in the UI. Stdlib-only — no services, no cost.
- Jobs page shows the enriched details (salary, applicants, documents, contact,
  full description) in an expandable section; richer deadline/posted metadata.
- Free-hosting deployment guide (`docs/deployment.md`): laptop-as-server,
  Vercel demo, GitHub Pages docs, tunnels — the whole stack at $0.

### Changed
- `/profile/edit` (legacy partial editor) now redirects to the integrated `/profile`
  editor; navigation highlights the active tab; branded loaders cover route changes.

## [0.5.0] — 2026-06-10

### Added
- **One-command local web stack**: `job-sentinel web` starts the FastAPI backend and
  Next.js UI together, wires `NEXT_PUBLIC_API_BASE`, and automatically moves to the
  next free API/UI ports when defaults are already in use.
- **Scraper controls in the jobs UI**: login, one-shot scrape, dry-run/alert toggle,
  and watcher start/stop controls backed by local API operations.
- **Sentinel branding assets**: canonical logo placement, generated favicon/app icons,
  web manifest, README/GitHub-facing asset copy, first-viewport brand treatment, and
  a reusable themed route loader.

### Fixed
- 12twenty login/session detection no longer treats "no rows rendered yet" as a failed
  login when the authenticated app shell is visible.

## [0.4.0] — 2026-06-10

### Added
- **Sentinel chat assistant**: a ChatGPT-style `/chat` page + `POST /api/chat`. Data
  questions (deadlines, recent jobs, pipeline stats, profile, pasted-JD ATS scoring) are
  answered deterministically from real local state; everything else goes to the local LLM
  grounded with a context block — with graceful rules-only fallback when Ollama is off.
  Suggested prompts, typing indicator, localStorage history, retry-on-failure, full
  keyboard + screen-reader support.
- **Full web UI redesign**: balanced light/dark system (stone + emerald, AA contrast,
  Inter), richer three.js hero (distorted core, wireframe orbiters, particle halo, pointer
  parallax), custom cursor, scroll progress, animated SVG pipeline, tilt-card bento,
  quality marquee, engineering stats band — all reduced-motion safe with skip links and
  focus rings; every app page restyled.

## [0.3.2] — 2026-06-10

### Added
- Web UI hardening: route-level `error`, `not-found` (404), and `loading` boundaries; a
  WebGL-safe error boundary around the three.js hero (an unsupported GPU can't crash the
  page); and **status actions on the jobs board** (mark applied/ignored, via
  `POST /api/jobs/{id}/status`).
- `resume doctor` now checks **both** the chat model (`--ai`) and the embedding model
  (`--semantic`), and `--pull` fetches whichever is missing; it reports "Ready" whenever the
  server is reachable with both models, even if the `ollama` CLI isn't on PATH.

## [0.3.1] — 2026-06-10

### Changed
- **First PyPI release.** The release workflow now publishes the built wheel + sdist to
  PyPI on tag (guarded by the `PYPI_API_TOKEN` secret). `pip install job-sentinel`.

## [0.3.0] — 2026-06-10

### Added
- **Cover-letter generation**: `resume cover --job-text <jd> [--role --company --ai]` and
  `POST /api/resume/cover` produce a tailored cover-letter PDF — a truthful deterministic
  draft (profile summary + most-relevant experience + top skills), optionally polished by
  the local LLM with the same no-fabrication guards.
- **Semantic relevance ranking** (`resume build --semantic`): orders profile content by
  local-embedding cosine similarity to the job description (Ollama `nomic-embed-text`),
  catching matches that share meaning but not keywords. Pluggable `SemanticTailor` that
  layers over the keyword/LLM tailors and falls back when the model is absent.
- Telegram new-job alerts now show a "⏰ Closes in N days" line when a posting's
  deadline parses and falls within a week.

## [0.2.0] — 2026-06-10

### Added
- **Local web stack**: a FastAPI layer (`job-sentinel serve`) and a Next.js 15 web UI
  (TypeScript, Tailwind, framer-motion, a three.js hero) — pages for the landing, profile
  view, **profile editor**, **résumé studio** (tailor → ATS coverage → download PDF, with a
  local-LLM toggle), and tracked jobs.
- **Web API**: `GET`/`PUT /api/profile`, `/api/profile/summary`, `/api/jobs`,
  `POST /api/jobs/{id}/status`, `POST /api/resume/tailor`, and `POST /api/resume/build`
  (streams a tailored PDF; 503 with an install hint if Tectonic is absent).
- **Email notifier** (optional, stdlib SMTP): a second alert channel alongside Telegram,
  fanned out in `run()`; no-op unless `EMAIL_ENABLED=true`.
- **Deadline-aware tracking**: free-form deadline parsing + a `/deadlines` command listing
  postings closing within `DEADLINE_ALERT_DAYS`.
- **Supply-chain CI**: `pip-audit` vulnerability scan + a license-compliance gate (blocks
  GPL/AGPL), plus a web type-check/build job.
- **Docker**: `Dockerfile` + `docker-compose.yml` for always-on operation with
  host-mounted, restart-safe data.
- Project docs: North-Star vision, competitive analysis, `SECURITY.md`, `CODEOWNERS`,
  `AGENTS.md`.

### Changed
- Next.js pinned to 15.5.19 (clears the 15.1.x advisories); `create_app` takes injectable
  profile/DB paths for test isolation. Test suite at ~82% coverage.

## [0.1.0] — 2026-06-09

### Added
- Initial project scaffold with full open-source structure
- Pluggable adapter system (`SiteAdapter` abstract base + registry)
- UTD 12twenty adapter (`TwelveTwentyAdapter`)
- Handshake adapter skeleton
- `pydantic-settings` v2 configuration with nested sub-settings
- `loguru` structured logging with JSON mode and rotating files
- `sqlite-utils` persistence layer (`JobRepository`)
- APScheduler-based poll loop (`Scheduler`)
- Telegram notifier with MarkdownV2 formatting and `tenacity` retry
- Full Telegram bot command suite: `/jobs`, `/recent`, `/applied`, `/ignore`, `/status`, `/stats`, `/filters`, `/adapters`, `/ping`
- Typer CLI with `run`, `scrape`, `db stats`, `db list`, `adapters` commands
- Pre-commit hooks: `ruff`, `mypy`, `gitleaks`, conventional commits, yamllint
- GitHub Actions CI: lint, type-check, test matrix (Python 3.11 / 3.12)
- Architecture Decision Records (ADRs) 001–004
- High-Level Design (HLD) and Low-Level Design (LLD) documents
- Adapter authoring guide
- **Universal profile + résumé generator**: a hand-editable `data/profile.yaml`
  (education, experience, projects, skills, certifications, awards, publications)
  rendered to an ATS-friendly PDF via a single-column LaTeX template compiled
  with Tectonic. New `resume init | show | build` CLI commands; works standalone
  without the bot configured.
- **Per-posting résumé tailoring**: `resume build --job-text <jd>` / `--job-id <id>`
  reorders profile content by keyword relevance and reports ATS keyword coverage
  (matched vs missing terms), behind a pluggable `Tailor` interface.
- **Optional local-LLM rephrasing** (`resume build --ai`): an `LLMTailor` backed
  by a self-hosted Ollama model rewrites bullets toward a posting — no API key, no
  data leaving the machine, with no-fabrication guards and JSON-validated output.
  Falls back to keyword tailoring when unavailable. `resume doctor` checks/sets up
  the local model.
- Out-of-tree adapter loading via `CUSTOM_ADAPTER_PATH` (no fork needed)
- `job-sentinel login` captures a browser session so the scraper can reuse it
  past portal bot-checks (e.g. Cloudflare) without re-authenticating each run
- Integration test for the full scrape cycle, plus bot-handler, notifier,
  browser, and adapter-base coverage (suite at ~75%)

### Fixed
- `KEYWORD_FILTERS` is now parsed as CSV from the environment without tripping
  pydantic-settings' JSON decoder (previously crashed at startup)
- Telegram delivery now actually retries transient transport failures; the
  retry decorator was previously a no-op because the body swallowed exceptions

### Changed
- `ApplicationStatus` uses `enum.StrEnum` (Python 3.11+)
- Codebase passes `ruff check`, `ruff format --check`, and `mypy --strict`
- 12twenty adapter selectors rewritten against the live UTD Student Employment
  DOM (it's an AngularJS table of `tr.job-posting` rows, not the placeholder
  card markup), with infinite-scroll row loading and content-based parsing of
  location / type / posted-date / deadline

---

[Unreleased]: https://github.com/harshitwandhare/job-sentinel/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/harshitwandhare/job-sentinel/compare/v0.8.0...v1.0.0
[0.8.0]: https://github.com/harshitwandhare/job-sentinel/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/harshitwandhare/job-sentinel/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/harshitwandhare/job-sentinel/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/harshitwandhare/job-sentinel/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/harshitwandhare/job-sentinel/compare/v0.3.2...v0.4.0
[0.3.2]: https://github.com/harshitwandhare/job-sentinel/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/harshitwandhare/job-sentinel/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/harshitwandhare/job-sentinel/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/harshitwandhare/job-sentinel/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/harshitwandhare/job-sentinel/releases/tag/v0.1.0
