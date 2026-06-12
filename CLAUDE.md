# CLAUDE.md — Job Sentinel

Site-agnostic job-portal monitor: Playwright scraping + Typer CLI + FastAPI local API +
Next.js web UI + Telegram/email alerts + LaTeX resume engine (Ollama-optional AI tailoring).
Python 3.11+, src layout, SQLite via sqlite-utils. **Read AGENTS.md first** — it is the
authorship/quality contract (owner-authored commits, NO AI co-author trailers or notices).

## Commands (Windows; venv already exists)

```powershell
.venv\Scripts\python.exe -m job_sentinel <cmd>     # CLI entry (= job-sentinel)
.venv\Scripts\python.exe -m pytest tests/unit tests/integration   # coverage gate 70%
.venv\Scripts\python.exe -m ruff check . ; .venv\Scripts\python.exe -m ruff format --check .
.venv\Scripts\python.exe -m mypy src/              # strict mode
cd web; npm run dev | build | typecheck            # no eslint configured
```

CLI commands: `run` (scheduler+bot), `scrape` (one cycle, default --dry-run), `login`
(manual portal login → data/session.json), `session` (headless validity check), `serve`
(FastAPI), `web` (API + Next.js together), `adapters`, `db stats|list`,
`resume init|import <pdf>|show|build|cover|doctor`.

## Layout

```
src/job_sentinel/
  __main__.py      Typer CLI (all commands above; lazy imports inside commands)
  adapters/        base.py (SiteAdapter ABC) + registry.py (plugin registry,
                   CUSTOM_ADAPTER_PATH loads external adapters); sites/twelve_twenty.py,
                   sites/handshake.py
  api/             FastAPI: app.py (routes), ops.py (login/scrape/watcher/session ops),
                   chat.py (grounded local-LLM chat)
  bot/handlers.py  python-telegram-bot v21 commands (/jobs /applied /stats /deadlines)
  config/          settings.py (pydantic-settings, .env), logging.py (loguru)
  core/            browser.py (Playwright), scheduler.py (APScheduler), models.py
                   (JobPosting etc.), deadlines.py, session.py (storage-state checks)
  db/repository.py sqlite-utils wrapper (only module allowed untyped calls)
  documents/       latex.py + renderer.py (LaTeX→PDF), tailor.py, llm.py (Ollama),
                   coverletter.py, embeddings.py/semantic.py, resume_import.py (PDF→profile)
  notifiers/       telegram.py (httpx), email.py (optional SMTP)
  profile/         models.py + store.py (data/profile.yaml universal profile)
web/               Next.js 15 / React 19 / Tailwind 3. app/{jobs,profile,profile/edit,
                   studio,chat}/page.tsx; components/ (Nav, ScraperControls, JobActions…);
                   lib/api.ts (typed client for ALL API routes — keep in sync)
tests/             unit/ mirrors src tree; integration/test_scheduler_cycle.py; e2e/ empty
docs/              design/{HLD,LLD,adapter-authoring,web-ui}.md, adr/, NORTH_STAR.md, RELEASING.md
scripts/           check_licenses.py (CI); diagnose_*.py are untracked one-off debug scripts
```

## 12twenty scraping (verified 2026-06-12 — do not rediscover)

- **Never put `viewId=<n>` in PORTAL_JOBS_URL** — saved-search views return "not
  authorized" → empty list (caused the "done 0" bug). Use
  `https://utdallas.12twenty.com/jobPostings#/jobPostings/index?tab=studentEmployment`.
- Adapter captures the portal's internal JSON API: list via
  `POST /Api/V2/job-postings/post-query` (Playwright response listener); full detail
  (description/salary/contact) via `GET /Api/V2/job-postings/{id}`; session validity via
  `GET /api/v2/account/current-user`.
- Authenticated app-shell selector: `#side-nav a.side-nav-link, a.logout`. Job rows
  `tr.job-posting` can be `ng-hide` — visibility waits hang; rely on API capture.
- Login is Cloudflare Turnstile-gated → headless login impossible. `job-sentinel login`
  opens a headed browser (credentials prefilled from .env) and saves data/session.json.

## Conventions (enforced)

- `mypy --strict`; `from __future__ import annotations` everywhere; type-only imports
  under `TYPE_CHECKING`. Ruff: line-length 100, select includes S (bandit), PTH, SIM, N.
- **UI/CLI parity rule**: every CLI feature needs an API route in `api/app.py` AND a web
  surface; `web/lib/api.ts` is the single typed client. API routes today: profile CRUD +
  import-resume, jobs + status, stats, ops/{status,login,session/check,scrape,watcher/*},
  llm/status, resume/{tailor,build,cover}, chat, health.
- Adapters are plugins: subclass `SiteAdapter` in `adapters/sites/`, register in registry;
  external adapters load via `CUSTOM_ADAPTER_PATH`. ~50 lines per portal (see
  docs/design/adapter-authoring.md).
- Conventional Commits (pre-commit enforces); no direct commits to main; CHANGELOG.md +
  docs/RELEASING.md for releases. Optional backends (Ollama, LaTeX, email) must degrade
  gracefully. New heavy deps need an ADR in docs/adr/.
- North star (owner): one-stop open-source job platform for students, zero-cost hosting
  only, UI/CLI feature parity, highest code quality. See docs/NORTH_STAR.md.

## Gotchas

- pytest addopts always runs coverage (html → htmlcov/) with `--cov-fail-under=70`; for a
  single test use `-p no:cacheprovider --no-cov` or expect the gate to fail.
- Windows: CLI reconfigures stdout/stderr to UTF-8 (cp1252 breaks ✓/emoji output).
- `.env` holds real credentials — never read or print it; use .env.example as reference.
- data/, logs/, htmlcov/ contain runtime artifacts; gitignored — don't read them for context.
