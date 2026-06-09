# 🛡 Job Sentinel

> **Site-agnostic job-portal monitor with pluggable adapters and instant Telegram alerts.**

[![CI](https://github.com/harshitwandhare/job-sentinel/actions/workflows/ci.yml/badge.svg)](https://github.com/harshitwandhare/job-sentinel/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg)](https://conventionalcommits.org)

Job Sentinel monitors job-listing portals on a configurable interval.
The moment a new posting appears, you get a rich Telegram alert — with
title, employer, location, deadline, keyword tags, and a direct link.

It ships with adapters for **UTD 12twenty** and **Handshake**.
Adding a new portal takes one file and ~50 lines of Python.

Out of the box it watches UTD 12twenty's **on-campus Student Employment** tab.
The tab is chosen by the `tab=` parameter in `PORTAL_JOBS_URL`, so the same
setup later points at internships or full-time listings by switching that URL.

---

## ✨ Features

| Feature | Details |
|---|---|
| **Pluggable adapters** | One Python file per portal — no core changes needed |
| **Telegram bot** | Rich alerts + commands (`/jobs`, `/applied`, `/stats`, `/deadlines`, …) |
| **Résumé engine** | Universal profile → ATS-friendly LaTeX/PDF, tailored per posting |
| **Local-LLM tailoring** | Optional Ollama rephrasing — no API key, nothing leaves your machine |
| **Web UI** | Next.js + Tailwind app: profile editor, résumé studio, jobs board |
| **Local API** | FastAPI layer (`job-sentinel serve`) the UI consumes — one source of truth |
| **Email + Telegram alerts** | Two notifier channels; email is optional SMTP |
| **Deadline awareness** | `/deadlines` flags postings closing within a configurable window |
| **Status tracking** | NEW → SEEN → APPLIED / IGNORED / CLOSED, persisted in SQLite |
| **Closed detection** | Marks postings that disappear from the portal |
| **Production-grade** | `mypy --strict`, ~82% tests, CI (lint/types/tests/secret/supply-chain), Docker |

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

### 5. Test run (dry run — no messages sent)

```bash
uv run job-sentinel scrape
```

### 6. Start the full bot

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
# 1. Start the local API (needs the 'web' extra: uv sync --extra web)
job-sentinel serve                 # http://127.0.0.1:8000  (Swagger at /docs)

# 2. Start the web app
cd web && npm install && npm run dev   # http://localhost:3000
```

Pages: an animated landing, a **profile editor**, a **résumé studio** (paste a
JD → live ATS coverage → download a tailored PDF, with a local-LLM toggle), and
a **jobs board** with statuses and deadlines.

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
│   ├── adapters/
│   │   ├── base.py            # Abstract SiteAdapter interface
│   │   ├── registry.py        # Plugin registry (dynamic loading)
│   │   └── sites/
│   │       ├── twelve_twenty.py   # UTD 12twenty adapter
│   │       └── handshake.py       # Handshake adapter
│   ├── bot/
│   │   └── handlers.py        # Telegram command handlers
│   ├── config/
│   │   ├── settings.py        # pydantic-settings config
│   │   └── logging.py         # loguru setup
│   ├── core/
│   │   ├── browser.py         # Playwright lifecycle manager
│   │   ├── models.py          # JobPosting, ScrapeResult (Pydantic v2)
│   │   └── scheduler.py       # APScheduler poll loop
│   ├── db/
│   │   └── repository.py      # sqlite-utils DB layer
│   ├── notifiers/
│   │   └── telegram.py        # MarkdownV2 formatting + delivery
│   └── __main__.py            # Typer CLI entry-point
├── tests/
│   ├── unit/                  # Fast, no I/O
│   ├── integration/           # Real DB, mocked network
│   └── e2e/                   # Full stack (optional, requires .env)
├── docs/
│   ├── adr/                   # Architecture Decision Records
│   └── design/                # HLD, LLD, adapter authoring guide
├── scripts/                   # Dev helper scripts
├── .github/workflows/         # CI/CD (GitHub Actions)
├── pyproject.toml             # Single source of truth (uv + hatchling)
├── .env.example               # Config template
└── .pre-commit-config.yaml    # Ruff, mypy, gitleaks, conventional commits
```

---

## 📋 Roadmap

- [x] Résumé engine (universal profile → ATS LaTeX/PDF) with per-posting tailoring
- [x] Local-LLM rephrasing via Ollama (no API key)
- [x] Web UI (Next.js) + local FastAPI layer
- [x] Email notifier (optional SMTP) alongside Telegram
- [x] Deadline-aware tracking (`/deadlines`)
- [x] Docker / docker-compose with persistent data
- [ ] Cover-letter generation (local LLM)
- [ ] Semantic relevance ranking (local embeddings)
- [ ] More portal adapters (Greenhouse, Workday, public boards via JobSpy)
- [ ] Discord webhook notifier
- [ ] Packaged installers + PyPI publish

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

All commits must follow [Conventional Commits](https://conventionalcommits.org).
Run `uv run pre-commit install` to enforce this automatically.

---

## 📄 License

MIT © [Harshit Wandhare](https://github.com/harshitwandhare) — see [LICENSE](LICENSE).
