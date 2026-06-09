# Low-Level Design (LLD) — Job Sentinel

**Version:** 1.0
**Last updated:** 2025

This document drops a level below the [HLD](HLD.md): module-by-module
responsibilities, the key data structures, the exact control flow of a scrape
cycle, and the contracts each component promises to its callers.

---

## 1. Module map

```
src/job_sentinel/
├── core/
│   ├── models.py      # JobPosting, ScrapeResult, ApplicationStatus
│   ├── browser.py     # browser_context() — Playwright lifecycle
│   └── scheduler.py   # Scheduler — the poll loop + cycle orchestration
├── adapters/
│   ├── base.py        # SiteAdapter ABC + scrape() orchestrator
│   ├── registry.py    # register_adapter / get_adapter / list_adapters
│   └── sites/*.py     # one file per portal
├── config/
│   ├── settings.py    # Settings tree (pydantic-settings)
│   └── logging.py     # configure_logging()
├── db/
│   └── repository.py  # JobRepository — sqlite-utils wrapper
├── notifiers/
│   └── telegram.py    # TelegramNotifier + MarkdownV2 formatters
├── bot/
│   └── handlers.py    # python-telegram-bot command handlers
└── __main__.py        # Typer CLI
```

Dependency direction is strictly inward: `bot`, `notifiers`, and `adapters`
depend on `core` and `config`, never the reverse. Nothing in `core` imports a
concrete adapter — the registry is the only seam where adapters are resolved,
and it does so by string ID.

---

## 2. Key data structures

### `JobPosting` (`core/models.py`)

The single record type that flows scraper → repository → notifier → bot.

| Field | Type | Notes |
|---|---|---|
| `posting_id` | `str` | Primary key. Portal-assigned, non-empty. |
| `title` … `deadline` | `str` | Whitespace-stripped on construction. |
| `description_snippet` | `str` | Truncated to 350 chars + ellipsis. |
| `status` | `ApplicationStatus` | Enum, stored as its `.value` string. |
| `discovered_at` / `updated_at` | `datetime` | Always tz-aware UTC. |
| `keywords_matched` | `list[str]` | Populated by `matches_keywords()`. |
| `raw_data` | `dict` | Adapter escape hatch; JSON-serialised in SQLite. |

Invariants:

- `posting_id` is unique per `(source_adapter)` and is the upsert key.
- Timestamps are **always** UTC — never naive. `_parse_dt()` in the repository
  falls back to `now(utc)` on a malformed string rather than raising.
- The model is mutable only through `touch()` and the keyword side-effect, both
  of which use `object.__setattr__` so the rest of the object stays effectively
  read-only.

### `ApplicationStatus` state machine

```
        ┌─────┐  alert sent   ┌──────┐  /applied   ┌─────────┐
        │ NEW │ ────────────▶ │ SEEN │ ──────────▶ │ APPLIED │
        └──┬──┘               └──┬───┘             └─────────┘
           │                     │  /ignore
           │                     ▼
           │                 ┌─────────┐
           │                 │ IGNORED │
           │                 └─────────┘
           │  removed from portal (any open state)
           ▼
        ┌────────┐
        │ CLOSED │
        └────────┘
```

`APPLIED` and `IGNORED` are **terminal from the scraper's point of view**: a
re-scrape never overwrites them (see §4, `save_job`). Only a human command can
move a posting into those states.

---

## 3. Component contracts

### `SiteAdapter` (`adapters/base.py`)

```python
class SiteAdapter(ABC):
    ADAPTER_ID: str            # unique slug, e.g. "12twenty"
    def login(page) -> None    # leave `page` authenticated on the listings view
    def scrape_page(page) -> list[JobPosting]
    def next_page(page) -> bool   # default False (single-page portals)
    def scrape(context) -> list[JobPosting]   # provided; orchestrates the above
```

Contract notes:

- `scrape()` is the only public entry point the scheduler calls. Subclasses
  override the three hooks, not `scrape()` itself.
- `scrape()` swallows `PlaywrightTimeoutError` per-page and any exception during
  login — a flaky portal must never crash the scheduler thread. It returns
  whatever it managed to collect.
- `safe_text` / `safe_attr` never raise; they return `""` on any failure so card
  parsing degrades gracefully when one field is missing.
- Pagination is bounded by `ScraperSettings.max_pages` to prevent an infinite
  "Next" loop on a broken selector.

### `JobRepository` (`db/repository.py`)

| Method | Contract |
|---|---|
| `save_job(job)` | Upsert. Returns `True` **iff** the row was new. Preserves a human-set status. |
| `update_status(id, status)` | Returns `False` if the id is unknown (no-op). |
| `get_new_jobs()` / `get_by_status(s)` | Newest-first, never `None` (empty list). |
| `get_stats()` | Always returns every status key (zero-filled) plus `total`. |

Concurrency: SQLite is opened in WAL mode so the bot thread can read while the
scheduler thread writes. There is a single writer (the scheduler's one-worker
thread pool), so no write-write contention is possible by construction.

### `TelegramNotifier` (`notifiers/telegram.py`)

- `_send()` is wrapped in `tenacity` (3 attempts, exponential backoff) and
  **never propagates** — a delivery failure returns `False` and is logged.
- All user-facing text passes through `escape()` before hitting the MarkdownV2
  parser. Forgetting to escape is the single most common Telegram bug, so the
  formatters own escaping rather than the callers.

---

## 4. Scrape-cycle control flow

`Scheduler._scrape_cycle()` is the heart of the system. One cycle:

```
1. resolve adapter      get_adapter(settings.site_adapter, settings.scraper)
2. open browser         with browser_context(scraper) as ctx:
3. scrape                   all_jobs = adapter.scrape(ctx)
4. filter               filtered = [j for j in all_jobs if j.matches_keywords(...)]
5. diff + persist       for j in filtered: is_new = repo.save_job(j)
                            if is_new -> new_jobs.append(j)
6. detect closed        repo: open postings no longer present -> CLOSED
7. notify               if new_jobs and not dry_run: on_new_jobs(new_jobs)
8. record               ScrapeResult(total, new, updated, closed, duration)
```

Failure containment: steps 2–7 run inside one `try/except` that records the
error string on the `ScrapeResult` and logs the traceback. The `finally` block
always stamps `duration_seconds` and logs the result, so every cycle produces
exactly one summary log line whether it succeeded or failed.

`save_job` upsert logic (step 5), in detail:

```
existing = get_job(job.posting_id)
is_new   = existing is None
if existing and existing.status in (APPLIED, IGNORED, CLOSED):
    # human decision wins — keep the stored status
    job = job.model_copy(update={"status": existing.status})
upsert(row)
return is_new
```

This is why a posting you marked `/applied` never re-alerts and never reverts to
`NEW`, even though the scraper keeps seeing it every cycle.

---

## 5. Threading & lifecycle

```
main thread                         scheduler worker thread (1)
───────────                         ───────────────────────────
Application.run_polling()  (asyncio)  BackgroundScheduler interval job
  ├─ command handlers                   └─ _scrape_cycle()
  └─ reads via JobRepository ──┐            ├─ Playwright (blocking)
                               │            └─ writes via JobRepository
                               └──── shared SQLite (WAL) ────┘
```

- The Telegram `Application` owns the main asyncio loop.
- APScheduler runs the blocking Playwright work on a **single** worker thread
  (`max_instances=1`, `coalesce=True`) so two cycles can never overlap and a
  backlog of missed fires collapses into one catch-up run after the PC wakes.
- `/jobs` calls `scheduler.trigger_now()`, which runs a cycle **synchronously on
  the calling coroutine's thread**. This is intentional for an on-demand refresh;
  the handler warns the user it takes 30–60s first.

---

## 6. Error handling matrix

| Layer | Failure | Handling |
|---|---|---|
| Adapter | Selector missing / timeout | `safe_*` returns `""`; page timeout breaks the pagination loop |
| Adapter | Login fails | Exception caught in `scrape()`, logged, empty list returned |
| Scheduler | Any cycle exception | Recorded on `ScrapeResult.errors`, logged, cycle still reports |
| Repository | Unknown id on update | Returns `False`, warns, no raise |
| Notifier | Telegram 4xx/5xx/network | tenacity retries, then logged `False` |
| Browser | Launch/close error | `finally` block guards teardown, warns on close failure |

The design rule: **the poll loop is the last line of defence and must survive
anything.** Everything below it fails soft.

---

## 7. Extension points

- **New portal** → new file in `adapters/sites/`, add to `_BUILTIN_ADAPTERS`.
  See [adapter-authoring.md](adapter-authoring.md).
- **Custom out-of-tree adapter** → set `CUSTOM_ADAPTER_PATH` in `.env`; the
  registry imports it at startup and the file self-registers.
- **New notifier** (Discord, email) → mirror `TelegramNotifier`'s
  `send_new_jobs(list[JobPosting])` shape and wire it into the scheduler
  callback in `__main__.py`.
- **New filter strategy** → extend `FilterSettings` and the `matches_keywords`
  call site in the cycle; the model already carries `keywords_matched`.
