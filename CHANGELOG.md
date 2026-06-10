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

[Unreleased]: https://github.com/harshitwandhare/job-sentinel/compare/v0.3.2...HEAD
[0.3.2]: https://github.com/harshitwandhare/job-sentinel/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/harshitwandhare/job-sentinel/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/harshitwandhare/job-sentinel/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/harshitwandhare/job-sentinel/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/harshitwandhare/job-sentinel/releases/tag/v0.1.0
