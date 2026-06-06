# ADR-002: Use Pydantic-Settings for Configuration

**Status:** Accepted | **Date:** 2025-01-01

## Decision
Use `pydantic-settings` v2 instead of plain `python-dotenv` + `os.getenv()`.

## Rationale
- **Type safety**: `"900"` → `int`, `"true"` → `bool`, `"a,b"` → `list[str]`
  automatically. No manual casting scattered across the codebase.
- **Validation at startup**: Bad config fails loudly at launch with a clear
  error message — not deep in a call stack at runtime.
- **Nested models**: `settings.telegram.bot_token` not `settings["TELEGRAM_BOT_TOKEN"]`.
- **Multiple sources**: env > .env file > defaults — in one declaration.
- **IDE autocompletion**: Full type inference throughout the project.

## Consequences
- `pydantic` and `pydantic-settings` are runtime dependencies.
- In tests, call `get_settings.cache_clear()` before monkeypatching env vars.

---

# ADR-003: Use Loguru for Logging

**Status:** Accepted | **Date:** 2025-01-01

## Decision
Use `loguru` instead of Python's stdlib `logging` module.

## Rationale
- **Zero config**: `from loguru import logger; logger.info("hello")` — done.
  No Handler, Formatter, getLogger boilerplate.
- **Structured JSON**: `serialize=True` gives machine-readable logs for
  Loki / Datadog / Grafana with zero extra code.
- **Rotating files**: `logger.add(path, rotation="5 MB")` — one line.
- **Context binding**: `logger.bind(posting_id=x).info("found")` — adds
  structured context to all subsequent log calls in scope.
- **Async-safe**: `enqueue=True` makes file writes thread-safe without locks.
- **Better tracebacks**: Coloured, with variable values in DEBUG mode.

## Consequences
- `loguru` is a runtime dependency (lightweight, ~50 KB).
- Call `configure_logging(settings.logging)` once at startup.
- Tests may need `caplog` fixture workaround for loguru intercept.

---

# ADR-004: Pluggable Adapter Pattern for Site Scraping

**Status:** Accepted | **Date:** 2025-01-01

## Decision
Implement a plugin-style adapter registry where each portal is a self-contained
Python file that registers itself.

## Rationale
- **Extensibility**: Any contributor can add a new portal without touching
  any core files.
- **Isolation**: Selectors and login logic for each site are fully contained.
  A DOM change on one portal only affects that one adapter file.
- **Testability**: Each adapter can be tested in isolation by mocking a
  Playwright Page.
- **Open-source alignment**: Makes it easy for the community to contribute
  adapters for their own universities/platforms.

## Design
```
SiteAdapter (ABC)
    └── TwelveTwentyAdapter    ADAPTER_ID = "12twenty"
    └── HandshakeAdapter       ADAPTER_ID = "handshake"
    └── [user's adapter]       ADAPTER_ID = "my_portal"

registry._registry: dict[str, type[SiteAdapter]]

get_adapter("12twenty", settings) → TwelveTwentyAdapter instance
```

Each adapter calls `register_adapter(MyAdapter)` at module level.
The registry lazy-loads built-in adapters on first `get_adapter()` call.

## Consequences
- `SITE_ADAPTER` in `.env` is the only change needed to switch portals.
- Built-in adapters must be listed in `_BUILTIN_ADAPTERS` in `registry.py`.
- Custom adapters can be loaded by setting `CUSTOM_ADAPTER_PATH` and calling
  `register_adapter()` before `get_adapter()`.
