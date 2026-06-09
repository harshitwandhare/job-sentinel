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
| **Telegram bot** | Rich alerts + interactive commands (`/jobs`, `/applied`, `/stats`) |
| **Keyword filtering** | Only alert on postings matching your filters |
| **Status tracking** | Track NEW → SEEN → APPLIED / IGNORED / CLOSED per posting |
| **SQLite persistence** | Zero external services — `sqlite-utils` backed |
| **Auto-pagination** | Follows "Next page" across all results |
| **Closed detection** | Marks postings that disappear from the portal |
| **On-demand scrape** | `/jobs` command triggers an immediate refresh |
| **WSL2 ready** | Chrome flags preconfigured for Windows Subsystem for Linux |
| **Production logging** | `loguru` — coloured console + rotating file + optional JSON |

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
| `/filters` | Show active keyword filters |
| `/adapters` | List available site adapters |
| `/ping` | Health check |

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

- [ ] Email notifier adapter
- [ ] Discord webhook notifier
- [ ] Web dashboard (FastAPI + htmx)
- [ ] Docker / docker-compose setup
- [ ] GitHub Actions cron for always-on (no local PC needed)
- [ ] More portal adapters (Greenhouse, Workday, LinkedIn Easy Apply)
- [ ] AI-based relevance scoring (LLM description matching)

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

All commits must follow [Conventional Commits](https://conventionalcommits.org).
Run `uv run pre-commit install` to enforce this automatically.

---

## 📄 License

MIT © [Harshit Wandhare](https://github.com/harshitwandhare) — see [LICENSE](LICENSE).
