"""
config/settings.py
──────────────────
Centralised configuration via **pydantic-settings** (v2).

Why pydantic-settings over plain python-dotenv + dataclass?
  • Automatic type coercion  — "900" → int, "true" → bool, "a,b" → list[str]
  • Validation with clear error messages at startup, not deep in the call stack
  • IDE autocompletion everywhere — settings.poll_interval_seconds not settings["poll_interval"]
  • Nested models — each subsystem can own its own sub-Settings
  • Multiple sources in priority order: env > .env file > defaults
  • Zero boilerplate — no manual os.getenv() calls scattered around

Usage
-----
    from job_sentinel.config.settings import get_settings

    settings = get_settings()   # cached singleton — safe to call anywhere
    print(settings.telegram.bot_token)
"""

from __future__ import annotations

from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# ─────────────────────────────────────────────────────────────────────────────
# Sub-settings (nested models for each subsystem)
# ─────────────────────────────────────────────────────────────────────────────

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ENV_FILE = str(_REPO_ROOT / ".env")

# Each nested BaseSettings loads its own sources, so every one of them must be
# pointed at the .env file via env_file= — otherwise only the root Settings
# reads it and the nested credentials silently fall back to "missing".


class TelegramSettings(BaseSettings):
    """Telegram Bot API credentials."""

    model_config = SettingsConfigDict(
        env_prefix="TELEGRAM_", extra="ignore", env_file=_ENV_FILE, env_file_encoding="utf-8"
    )

    bot_token: str = Field(..., description="Bot token from @BotFather")
    chat_id: str = Field(..., description="Target chat / user ID for alerts")


class PortalSettings(BaseSettings):
    """Target portal credentials and URL."""

    model_config = SettingsConfigDict(
        env_prefix="PORTAL_", extra="ignore", env_file=_ENV_FILE, env_file_encoding="utf-8"
    )

    username: str = Field(..., description="Portal login username / email")
    password: str = Field(..., description="Portal login password")
    jobs_url: str = Field(
        ...,
        description="Full URL to the job-listings page to scrape",
    )


class ScraperSettings(BaseSettings):
    """Browser automation behaviour."""

    model_config = SettingsConfigDict(extra="ignore", env_file=_ENV_FILE, env_file_encoding="utf-8")

    headless: bool = Field(default=True, description="Run browser headless?")
    browser_slowmo_ms: int = Field(default=0, ge=0, description="Playwright slow-mo (ms)")
    max_pages: int = Field(default=50, ge=1, le=500, description="Max pages to paginate")
    page_timeout_ms: int = Field(default=30_000, ge=5_000, description="Page load timeout (ms)")
    poll_interval_seconds: int = Field(
        default=900, ge=60, description="Scrape interval in seconds (min 60)"
    )


class FilterSettings(BaseSettings):
    """Keyword-based post-scrape filtering."""

    model_config = SettingsConfigDict(extra="ignore", env_file=_ENV_FILE, env_file_encoding="utf-8")

    # NoDecode stops pydantic-settings from JSON-decoding the env value first
    # (it would choke on a plain CSV like "software,engineer"); we parse it
    # ourselves in the validator below.
    keyword_filters: Annotated[list[str], NoDecode] = Field(
        default_factory=list,
        description="Comma-separated keywords; empty = match all",
    )

    @field_validator("keyword_filters", mode="before")
    @classmethod
    def parse_csv(cls, v: object) -> list[str]:
        """Accept 'a,b,c' string OR a real list from env."""
        if v is None or v == "":
            return []
        if isinstance(v, str):
            return [kw.strip() for kw in v.split(",") if kw.strip()]
        if isinstance(v, Iterable):
            return [str(item) for item in v]
        return []


class LLMSettings(BaseSettings):
    """Local LLM (Ollama) config for the optional résumé-tailoring layer."""

    model_config = SettingsConfigDict(
        env_prefix="OLLAMA_", extra="ignore", env_file=_ENV_FILE, env_file_encoding="utf-8"
    )

    base_url: str = Field(
        default="http://localhost:11434", description="Ollama HTTP endpoint (OLLAMA_BASE_URL)"
    )
    model: str = Field(default="llama3.1:8b", description="Local model tag to use (OLLAMA_MODEL)")
    embed_model: str = Field(
        default="nomic-embed-text",
        description="Local embedding model for semantic ranking (OLLAMA_EMBED_MODEL)",
    )


class EmailSettings(BaseSettings):
    """Optional SMTP email notifier (a second alert channel alongside Telegram)."""

    model_config = SettingsConfigDict(
        env_prefix="EMAIL_", extra="ignore", env_file=_ENV_FILE, env_file_encoding="utf-8"
    )

    enabled: bool = Field(default=False, description="Turn the email channel on")
    smtp_host: str = Field(default="", description="SMTP server host")
    smtp_port: int = Field(default=587, description="SMTP port (587 STARTTLS, 465 SSL)")
    username: str = Field(default="", description="SMTP username")
    password: str = Field(default="", description="SMTP password / app password")
    sender: str = Field(default="", description="From address (defaults to username)")
    recipient: str = Field(default="", description="Where alerts are sent")
    use_tls: bool = Field(default=True, description="STARTTLS (True) vs implicit SSL (False)")

    @property
    def configured(self) -> bool:
        return self.enabled and bool(self.smtp_host and self.recipient)


class LogSettings(BaseSettings):
    """Logging configuration."""

    model_config = SettingsConfigDict(
        env_prefix="LOG_", extra="ignore", env_file=_ENV_FILE, env_file_encoding="utf-8"
    )

    level: str = Field(default="INFO", description="Log level: DEBUG|INFO|WARNING|ERROR")
    dir: Path = Field(default=_REPO_ROOT / "logs", description="Rotating log file directory")
    # validation_alias keeps the env var LOG_JSON while avoiding the field name
    # "json", which would shadow pydantic's deprecated BaseModel.json().
    json_logs: bool = Field(
        default=False,
        validation_alias="LOG_JSON",
        description="Emit structured JSON logs?",
    )

    @field_validator("level")
    @classmethod
    def normalise_level(cls, v: str) -> str:
        return v.upper()


# ─────────────────────────────────────────────────────────────────────────────
# Root settings (composes all sub-settings)
# ─────────────────────────────────────────────────────────────────────────────


class Settings(BaseSettings):
    """
    Root application settings.

    Loaded from (in priority order):
      1. Real environment variables
      2. ``.env`` file in the repo root
      3. Defaults defined in the field annotations
    """

    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",  # TELEGRAM__BOT_TOKEN also works
        extra="ignore",
        case_sensitive=False,
    )

    # ── Subsystems ────────────────────────────────────────────────────────
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    portal: PortalSettings = Field(default_factory=PortalSettings)
    scraper: ScraperSettings = Field(default_factory=ScraperSettings)
    filters: FilterSettings = Field(default_factory=FilterSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)
    logging: LogSettings = Field(default_factory=LogSettings)

    # ── Top-level ─────────────────────────────────────────────────────────
    site_adapter: str = Field(
        default="12twenty",
        description="Adapter ID to use (see src/job_sentinel/adapters/sites/)",
    )
    custom_adapter_path: Path | None = Field(
        default=None,
        description="Optional path to an out-of-tree adapter file to import at startup",
    )
    db_path: Path = Field(
        default=_REPO_ROOT / "data" / "jobs.db",
        description="SQLite database file path",
    )
    session_path: Path = Field(
        default=_REPO_ROOT / "data" / "session.json",
        description="Saved Playwright storage state (cookies) from `job-sentinel login`",
    )
    dry_run: bool = Field(
        default=False,
        description="Scrape but do not send Telegram messages",
    )
    deadline_alert_days: int = Field(
        default=5, ge=1, description="Flag postings whose deadline is within this many days"
    )
    env: str = Field(default="development", description="development | staging | production")

    @model_validator(mode="after")
    def ensure_dirs(self) -> Settings:
        """Create data and log directories if they don't exist yet."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logging.dir.mkdir(parents=True, exist_ok=True)
        return self

    @property
    def is_production(self) -> bool:
        return self.env == "production"


# ─────────────────────────────────────────────────────────────────────────────
# Cached singleton accessor
# ─────────────────────────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the global :class:`Settings` instance.

    Cached after first call — always returns the same object.
    For tests, call ``get_settings.cache_clear()`` before monkeypatching env vars.
    """
    return Settings()
