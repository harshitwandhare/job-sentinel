# High-Level Design (HLD) — Job Sentinel

**Version:** 1.0  
**Author:** Harshit Wandhare  
**Last updated:** 2025

---

## 1. Purpose

Job Sentinel is an autonomous background service that monitors job-listing
portals, diffs new postings against a local database, and delivers instant
Telegram alerts.  It is designed to run indefinitely on a personal Windows
PC / WSL2 without cloud infrastructure.

---

## 2. Goals & Non-Goals

### Goals
- Real-time (≤15 min latency) alerts for new job postings
- Site-agnostic — adding a new portal requires no core code changes
- Zero cloud dependencies — runs fully on-premise (PC / WSL2)
- Interactive Telegram bot for tracking application lifecycle
- Open-source, portfolio-quality codebase

### Non-Goals (v1)
- Auto-submission of applications (legal/ToS risk; planned for v2)
- Multi-user support
- Web dashboard (planned for v2)

---

## 3. System Components

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            Job Sentinel Process                          │
│                                                                          │
│   ┌──────────────────────────────────────────────────────────────────┐   │
│   │  Main Thread — asyncio event loop                                │   │
│   │  ┌────────────────────────────────────────────────────────────┐  │   │
│   │  │  python-telegram-bot Application.run_polling()             │  │   │
│   │  │  Handles: /jobs /recent /applied /ignore /status /stats    │  │   │
│   │  └────────────────────────────────────────────────────────────┘  │   │
│   └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│   ┌──────────────────────────────────────────────────────────────────┐   │
│   │  Background Thread — APScheduler ThreadPoolExecutor              │   │
│   │  ┌───────────┐    ┌───────────────┐    ┌────────────────────┐   │   │
│   │  │ Scheduler │───▶│  SiteAdapter  │───▶│   BrowserContext   │   │   │
│   │  │           │    │  (Playwright) │    │   (Chromium)       │   │   │
│   │  └─────┬─────┘    └───────────────┘    └────────────────────┘   │   │
│   │        │                                                          │   │
│   │        ▼                                                          │   │
│   │  ┌───────────────┐    ┌──────────────────┐                       │   │
│   │  │ JobRepository │    │ TelegramNotifier  │                       │   │
│   │  │ (sqlite-utils)│    │ (httpx, tenacity) │                       │   │
│   │  └───────────────┘    └──────────────────┘                       │   │
│   └──────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
    SQLite DB                    Telegram Bot API
    (jobs.db)                    (api.telegram.org)
```

---

## 4. Data Flow

```
Portal Website
     │
     │  HTTP (Playwright/Chromium)
     ▼
TwelveTwentyAdapter.scrape()
     │  list[JobPosting]
     ▼
Scheduler._scrape_cycle()
     │
     ├─── Apply keyword filters ──────────────────────┐
     │                                                 │
     ├─── JobRepository.save_job(job)                  │
     │         └── is_new?                             │
     │              ├── Yes → new_jobs.append(job)     │
     │              └── No  → update metadata          │
     │                                                 │
     └─── TelegramNotifier.send_new_jobs(new_jobs) ◀──┘
```

---

## 5. Component Responsibilities

| Component | Responsibility |
|---|---|
| `SiteAdapter` | Login + HTML scraping via Playwright |
| `Scheduler` | Interval timing, cycle orchestration, filter application |
| `JobRepository` | Upsert / query SQLite (sqlite-utils) |
| `TelegramNotifier` | Format MarkdownV2 messages, HTTP POST to Bot API |
| `BotHandlers` | Async command handlers, user interaction |
| `Settings` | pydantic-settings config, type-safe env loading |

---

## 6. Concurrency Model

```
Main thread         Background thread (APScheduler)
─────────────       ──────────────────────────────
asyncio loop        Playwright (blocking I/O)
  └── bot polling     └── Chromium browser
  └── command         └── HTTP requests (httpx sync)
      handlers
          │
          │  thread-safe reads (SQLite WAL)
          ▼
       JobRepository (shared)
```

SQLite WAL mode allows concurrent reads from the bot thread while the
scheduler thread is writing.  No additional locking is needed.

---

## 7. Failure Modes & Recovery

| Failure | Behaviour |
|---|---|
| Portal unreachable | Scrape returns empty list; logged; retried next interval |
| CAS login fails | Exception caught; logged; next cycle retries |
| Telegram API down | tenacity retries 3× with exponential backoff; logged |
| PC sleep/hibernate | APScheduler detects missed fire; runs immediately on wake |
| DB corruption | sqlite-utils raises; logged; next insert creates fresh DB |

---

## 8. Security Considerations

- Credentials stored only in local `.env` — never logged, never sent except to portal
- `gitleaks` pre-commit hook blocks accidental credential commits
- Telegram Bot API uses HTTPS only
- `.env` is in `.gitignore` with `detect-private-key` hook as extra guard
- No credentials in logs (loguru's `diagnose=False` in production log files)

---

## 9. Technology Choices

| Decision | Choice | Rationale |
|---|---|---|
| Package manager | `uv` | 10-100× faster than pip/poetry; replaces pyenv |
| Config | `pydantic-settings` | Type-safe, validates at startup, no scattered `os.getenv` |
| Logging | `loguru` | Zero-config, JSON mode, rotating files in one line |
| Browser | Playwright (Chromium) | Handles SPAs, handles CAS SSO, cross-platform |
| DB | `sqlite-utils` + SQLite | Zero infra, WAL-safe, ergonomic API |
| Scheduler | `apscheduler` | Handles sleep/hibernate miss-fires; cron-capable |
| HTTP | `httpx` | Async-capable, HTTP/2, replaces requests |
| Retry | `tenacity` | Declarative retry with exponential backoff |
| CLI | `typer` + `rich` | Beautiful auto-help, zero boilerplate |
| Bot | `python-telegram-bot` v21 | Async, Bot API 7.x, actively maintained |
| Linting | `ruff` | Replaces black+flake8+isort; 100× faster |

See [docs/adr/](../adr/) for individual Architecture Decision Records.

---

## 10. Future Evolution

```
v1 (now)      v2                    v3
──────────    ──────────────────    ────────────────────────
Local PC  →   Docker / VPS      →   Multi-user SaaS
SQLite    →   PostgreSQL        →   Cloud DB
Telegram  →   + Discord/Email   →   Web dashboard
Manual    →   AI relevance      →   LLM application drafter
```
