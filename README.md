<p align="center">
  <img src=".github/assets/sentinel.png" alt="Job Sentinel logo" width="140" />
</p>

# Job Sentinel

> **Site-agnostic job-portal monitor with pluggable adapters and instant Telegram alerts.**

[![CI](https://github.com/harshitwandhare/job-sentinel/actions/workflows/ci.yml/badge.svg)](https://github.com/harshitwandhare/job-sentinel/actions/workflows/ci.yml)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/13183/badge)](https://www.bestpractices.dev/projects/13183)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/harshitwandhare/job-sentinel/badge)](https://securityscorecards.dev/viewer/?uri=github.com/harshitwandhare/job-sentinel)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg)](https://conventionalcommits.org)

<p align="center">
  <a href="https://job-sentinel.vercel.app"><b>🌐 Live demo</b></a> ·
  <a href="https://harshitwandhare.github.io/job-sentinel/"><b>📚 Docs</b></a> ·
  <a href="https://github.com/harshitwandhare/job-sentinel/releases"><b>📦 Releases</b></a>
</p>

<p align="center">
  <img src=".github/assets/demo-hero.gif" alt="Job Sentinel landing page with a live terminal replay of a real session: session check, scrape, AI resume build" width="800" />
</p>

Job Sentinel watches your university job portals, alerts you on Telegram the
moment a posting appears, and generates **ATS-ready résumés and cover letters
tailored to each role by a local LLM** — no API keys, no data leaving your
machine.

It ships with adapters for **UTD 12twenty** and **Handshake**; adding a new
portal takes one file and ~50 lines of Python.

> **🌐 Hosted demo vs. running locally** — the
> [live demo](https://job-sentinel.vercel.app) shows the interface, but the
> engine (scraping, local AI, PDF builds) runs **on your machine by design**:
> your portal credentials, your data, and the model never leave it. Follow the
> [Quick Start](#-quick-start) below to run the real thing — about 5 minutes.

<details>
<summary><b>Table of contents</b></summary>

- [Features](#-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Configuration](#%EF%B8%8F-configuration)
- [Bot Commands](#-bot-commands)
- [Résumé Generator](#-résumé-generator)
- [Web UI](#-web-ui)
- [Adding a New Portal](#-adding-a-new-portal)
- [Development](#-development)
- [Deployment & data persistence](#-deployment-always-on--data-persistence)
- [Project Structure](#-project-structure)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)

</details>

---

## ✨ Features

| Feature | Details |
|---|---|
| **Pluggable adapters** | One Python file per portal — no core changes needed |
| **Telegram bot** | Rich alerts + commands (`/jobs`, `/applied`, `/stats`, `/deadlines`, …) |
| **Résumé engine** | Universal profile → ATS-friendly LaTeX/PDF, tailored per posting |
| **Local-LLM tailoring** | Optional Ollama rephrasing — no API key, nothing leaves your machine |
| **Web UI** | Next.js + Tailwind app: profile editor, résumé studio, jobs board |
| **One-command web app** | `job-sentinel web` starts FastAPI + Next.js together |
| **Local API** | FastAPI layer (`job-sentinel serve`) the UI consumes — one source of truth |
| **Email + Telegram alerts** | Two notifier channels; email is optional SMTP |
| **Deadline awareness** | `/deadlines` flags postings closing within a configurable window |
| **Status tracking** | NEW → SEEN → APPLIED / IGNORED / CLOSED, persisted in SQLite |
| **Closed detection** | Marks postings that disappear from the portal |
| **Resume PDF import** | Upload an existing resume → structured profile draft (local-LLM or heuristic) |
| **Session management** | `job-sentinel session` validity check; login prefills credentials from `.env` |
| **Per-job documents** | One-click tailored résumé + cover letter PDFs from any tracked posting |
| **Optional auth** | `AUTH_MODE=demo\|required`: PBKDF2 accounts, HMAC tokens, admin-managed invites |
| **Production-grade** | `mypy --strict`, 280+ tests (80% gate), ESLint+vitest, OpenSSF Scorecard, reproducible `uv.lock` builds, Docker |

---

## 🏗 Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                        Job Sentinel                            │
│                                                                │
│  ┌──────────────┐    ┌─────────────┐    ┌──────────────────┐  │
│  │   Scheduler  │───▶│   Adapter   │───▶│  JobRepository   │  │
│  │  (APScheduler│    │  (Playwright│    │  (sqlite-utils)  │  │
│  │   background)│    │   + site    │    │                  │  │
│  └──────┬───────┘    │   plugin)   │    └──────────────────┘  │
│         │            └─────────────┘             │            │
│         │                                        │            │
│         ▼                                        ▼            │
│  ┌──────────────┐                    ┌──────────────────────┐ │
│  │   Telegram   │◀───────────────────│   Bot Handlers       │ │
│  │   Notifier   │   alerts + cmds    │  (python-telegram-   │ │
│  │   (httpx)    │                    │   bot v21, async)    │ │
│  └──────────────┘                    └──────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

See [docs/design/HLD.md](docs/design/HLD.md) for the full High-Level Design
and [docs/design/LLD.md](docs/design/LLD.md) for Low-Level Design.

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (install: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- A Telegram account

### 2. Clone & Install

```bash
git clone https://github.com/harshitwandhare/job-sentinel.git
cd job-sentinel

# Install all dependencies (creates .venv automatically)
uv sync

# Install Playwright's Chromium browser
uv run playwright install chromium
```

### 3. Create your Telegram bot

1. Open Telegram and message **[@BotFather](https://t.me/BotFather)**
2. Send `/newbot` and follow the prompts → copy the **token**
3. Message your new bot once, then visit:
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Copy your **chat ID** from the JSON response (`message.chat.id`)

### 4. Configure

```bash
cp .env.example .env
# Edit .env and fill in:
#   TELEGRAM_BOT_TOKEN=...
#   TELEGRAM_CHAT_ID=...
#   PORTAL_USERNAME=your_utd_netid
#   PORTAL_PASSWORD=your_password
```

### 5. Sign in once (Cloudflare-gated portals)

```bash
uv run job-sentinel login     # a browser opens; credentials prefill from .env —
                              # clear the challenge, click Sign In, done
uv run job-sentinel session   # verify: "✓ Session valid as <your name>"
```

> ⚠️ Don't add a `viewId=<n>` parameter to `PORTAL_JOBS_URL` — saved-search
> views can be "not authorized" for your account, which silently renders an
> empty list (the classic "scrape found 0 jobs" trap).

### 6. Test run (dry run — no messages sent)

```bash
uv run job-sentinel scrape
```

### 7. Start the full bot

```bash
uv run job-sentinel run
```

That's it. Open Telegram and send `/start` to your bot.

---

## ⚙️ Configuration

All configuration is via environment variables in `.env`.
See [`.env.example`](.env.example) for the full reference.

| Variable | Default | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | — | **Required.** From @BotFather |
| `TELEGRAM_CHAT_ID` | — | **Required.** Your Telegram user/chat ID |
| `PORTAL_USERNAME` | — | **Required.** Portal login |
| `PORTAL_PASSWORD` | — | **Required.** Portal password |
| `PORTAL_JOBS_URL` | UTD 12twenty URL | Full URL to the listings page |
| `SITE_ADAPTER` | `12twenty` | Adapter to use |
| `POLL_INTERVAL_SECONDS` | `900` | Scrape interval (min: 60) |
| `KEYWORD_FILTERS` | _(empty = all)_ | CSV: `software,engineer,research` |
| `HEADLESS` | `true` | Run browser headless |
| `DRY_RUN` | `false` | Scrape but don't send alerts |
| `OLLAMA_MODEL` | `llama3.2:3b` | Local model for AI features (3B fits 4 GB GPUs) |
| `AUTH_MODE` | `off` | `off` / `demo` (gate writes) / `required` (gate all) |
| `LOG_LEVEL` | `INFO` | `DEBUG`/`INFO`/`WARNING`/`ERROR` |

---

## 🤖 Bot Commands

| Command | Description |
|---|---|
| `/jobs` | Trigger a fresh scrape + show recent postings |
| `/recent` | Show last 10 jobs from the database |
| `/applied <id>` | Mark posting as applied |
| `/ignore <id>` | Dismiss a posting |
| `/status <id>` | Full details of a specific posting |
| `/stats` | Counts by status (new / seen / applied / ignored / closed) |
| `/deadlines` | Postings closing within `DEADLINE_ALERT_DAYS` |
| `/filters` | Show active keyword filters |
| `/adapters` | List available site adapters |
| `/ping` | Health check |

---

## 📄 Résumé Generator

Job Sentinel keeps a **universal profile** — your master CV data in one
hand-editable YAML file — and renders ATS-friendly PDFs from it. It's
standalone: you don't need the Telegram bot configured to use it.

```bash
# 1. Scaffold a profile you can edit like an Overleaf source
uv run job-sentinel resume init        # writes data/profile.yaml

# 2. Edit data/profile.yaml — add education, experience, projects, skills…

# 3. Build an ATS-friendly PDF (also writes the .tex next to it)
uv run job-sentinel resume build -o data/resume.pdf
uv run job-sentinel resume show        # summarise your profile

# 4. Tailor to a specific posting — reorders content by relevance and
#    reports ATS keyword coverage (matched vs missing terms)
uv run job-sentinel resume build --job-text "paste a job description here"
uv run job-sentinel resume build --job-id <posting_id>   # a posting already scraped

# 5. Generate a tailored cover letter (deterministic, or --ai to polish locally)
uv run job-sentinel resume cover --job-text "…" --role "Student Assistant" --company "UTD"
```

PDF rendering uses **[Tectonic](https://tectonic-typesetting.github.io)** (a
self-contained LaTeX engine — no full TeX install needed). Install it once:

```bash
winget install TectonicProject.Tectonic   # Windows
brew install tectonic                      # macOS
cargo install tectonic                     # Linux (or your package manager)
```

If Tectonic isn't installed, `resume build` still writes the `.tex` so you can
compile it on Overleaf. The template is single-column with standard fonts and
real selectable text, so it parses cleanly through ATS.

### Optional: local-LLM rephrasing (no API key)

Add `--ai` to rephrase your bullets toward a posting using a **local** model via
[Ollama](https://ollama.com) — fully offline, no API key, your data never leaves
your machine. It only *rephrases* content already in your profile (it can't
invent facts), and falls back to keyword tailoring if the model isn't available.

```bash
job-sentinel resume doctor --pull      # checks Ollama + pulls the model
job-sentinel resume build --ai --job-text "paste a job description"
```

---

## 🖥 Web UI

Prefer a UI? Job Sentinel ships a local web app (Next.js + Tailwind) over a
FastAPI layer — same engine, nicer surface. It's fully local: the API binds to
localhost and the optional LLM stays on your machine.

```bash
# One command for everything: API + UI + recurring scrape watcher
uv run job-sentinel web --watch        # http://localhost:3000

# Or piecemeal:
job-sentinel serve                     # API only — Swagger at /docs
cd web && npm install && npm run dev   # UI only
```

Pages: an animated landing (with a self-typing terminal replay of a real
session), a **profile editor** with resume-PDF import, a **résumé studio**
(paste a JD → live ATS coverage → tailored PDF, local-LLM toggle), a **jobs
board** with per-posting résumé/cover-letter generation, scraper controls and
session checks, and the **Sentinel chat assistant**.

| Jobs board — real scraped postings, one-click tailored documents | Résumé studio — paste a JD, get ATS coverage + a one-page PDF |
|---|---|
| ![Jobs board with scraper controls, session status, and per-posting resume/cover-letter buttons](.github/assets/screen-jobs.png) | ![Resume studio with job-description input, ATS scoring, and local-AI toggle](.github/assets/screen-studio.png) |

### Sharing your instance (optional auth)

Want a public demo of *your* instance, or to invite a friend? Turn on
authentication — stdlib-only, no services:

```bash
job-sentinel users add yourname --admin   # first account must be an admin
AUTH_MODE=demo job-sentinel serve          # reads public, actions need login
```

`AUTH_MODE=demo` keeps browsing open but gates actions; `required` gates
everything. Admins create further accounts (`users add`, or `POST
/api/auth/users`). Details in [docs/deployment.md](docs/deployment.md).

---

## 🔌 Adding a New Portal

1. Create `src/job_sentinel/adapters/sites/my_portal.py`
2. Subclass `SiteAdapter`, implement `login()` and `scrape_page()`
3. Set `SITE_ADAPTER=my_portal` in your `.env`

Full guide: [docs/design/adapter-authoring.md](docs/design/adapter-authoring.md)

---

## 🛠 Development

```bash
# Install dev dependencies
uv sync --all-extras

# Install pre-commit hooks (runs ruff, mypy, secret scan on every commit)
uv run pre-commit install

# Run tests
uv run pytest

# Lint & format
uv run ruff check --fix .
uv run ruff format .

# Type check
uv run mypy src/

# All at once (same as CI)
uv run pre-commit run --all-files
```

---

## 🐳 Deployment (always-on) & data persistence

Run it continuously with Docker — the image is based on the official Playwright
image (Chromium + system libs included):

```bash
docker compose up -d --build     # start detached
docker compose logs -f           # follow
```

**Your data never vanishes on restart.** `./data` and `./logs` are bind-mounted
from the host, so the SQLite database, captured login session, and your profile
live on disk — surviving container restarts, rebuilds, and reboots.

> 12twenty's login is Cloudflare-gated, so capture a session on the host first
> with `job-sentinel login` (it writes `data/session.json`, which the container
> mounts and reuses). Re-run `login` if the session expires.

**Backups.** Everything important is in `data/`. Back it up while the bot is
idle — e.g. a WAL-safe SQLite copy:

```bash
sqlite3 data/jobs.db ".backup data/jobs.backup.db"
cp data/profile.yaml data/profile.backup.yaml
```

---

## 📁 Project Structure

```
job-sentinel/
├── src/job_sentinel/
│   ├── adapters/              # Plugin system: base interface, registry,
│   │   └── sites/             #   12twenty + Handshake adapters
│   ├── api/                   # FastAPI layer: routes, ops runner, auth
│   ├── bot/                   # Telegram command handlers
│   ├── config/                # pydantic-settings config + loguru setup
│   ├── core/                  # Browser, models, scheduler, session workflows
│   ├── db/                    # sqlite-utils repository
│   ├── documents/             # Resume engine: LaTeX, tailoring, LLM,
│   │                          #   embeddings, cover letters, PDF import
│   ├── notifiers/             # Telegram (MarkdownV2) + SMTP email
│   ├── profile/               # Universal profile models + YAML store
│   └── __main__.py            # Typer CLI entry-point
├── web/                       # Next.js UI (App Router, Tailwind, vitest)
├── tests/                     # unit/ · integration/ · e2e/ (280+ tests)
├── docs/                      # MkDocs site: HLD, LLD, ADRs, deployment
├── .github/workflows/         # CI · Release · Docs · Scorecard
├── pyproject.toml             # Single source of truth (uv + hatchling)
└── uv.lock                    # Reproducible builds (CI uses --locked)
```

---

## 📋 Roadmap

- [x] Résumé engine (universal profile → ATS LaTeX/PDF) with per-posting tailoring
- [x] Local-LLM rephrasing via Ollama (no API key)
- [x] Web UI (Next.js) + local FastAPI layer — full CLI feature parity
- [x] Email notifier (optional SMTP) alongside Telegram
- [x] Deadline-aware tracking (`/deadlines`)
- [x] Docker / docker-compose with persistent data
- [x] Cover-letter generation (deterministic + local-LLM polish)
- [x] Semantic relevance ranking (local embeddings via Ollama)
- [x] Resume PDF import → structured profile draft
- [x] Session validity checks + credential-prefilled login
- [x] Optional multi-user auth (demo/required modes, admin invites)
- [x] Hosted demo (Vercel) + docs site (GitHub Pages) — both $0
- [ ] More portal adapters (Greenhouse, Workday, public boards via JobSpy)
- [ ] Discord webhook notifier
- [ ] Playwright e2e suite against `job-sentinel web`
- [ ] Packaged installers + PyPI publish

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

All commits must follow [Conventional Commits](https://conventionalcommits.org).
Run `uv run pre-commit install` to enforce this automatically.

---

## 📄 License

MIT © [Harshit Wandhare](https://github.com/harshitwandhare) — see [LICENSE](LICENSE).
