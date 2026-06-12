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

[Unreleased]: https://github.com/harshitwandhare/job-sentinel/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/harshitwandhare/job-sentinel/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/harshitwandhare/job-sentinel/compare/v0.3.2...v0.4.0
[0.3.2]: https://github.com/harshitwandhare/job-sentinel/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/harshitwandhare/job-sentinel/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/harshitwandhare/job-sentinel/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/harshitwandhare/job-sentinel/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/harshitwandhare/job-sentinel/releases/tag/v0.1.0
