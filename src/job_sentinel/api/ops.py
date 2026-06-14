"""
api/ops.py
───────────
Background operations behind the local API: portal login, one-shot scrape,
and the continuous watcher. These are the HTTP twins of the CLI commands
``job-sentinel login``, ``job-sentinel scrape`` and ``job-sentinel run`` —
they reuse the exact same core code (adapters, browser, scheduler) so the
two surfaces can never drift apart.

Threading model
───────────────
FastAPI handlers return immediately; the actual browser work runs in a
daemon thread tracked by :class:`OpsRunner`. The UI polls ``/api/ops/status``
to follow progress. One browser-driven op at a time (login XOR scrape) —
guarded by a lock so two Chromium instances never fight over the session.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

from loguru import logger
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from job_sentinel.config.settings import Settings
    from job_sentinel.core.scheduler import Scheduler
    from job_sentinel.db.repository import JobRepository

OpState = Literal["idle", "running", "ok", "error"]


class OpStatus(BaseModel):
    """Progress snapshot of one background operation."""

    state: OpState = "idle"
    message: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None
    detail: dict[str, Any] = Field(default_factory=dict)


class OpsConflictError(RuntimeError):
    """Raised when an operation can't start because another one is running."""


class OpsConfigError(RuntimeError):
    """Raised when settings can't load (incomplete .env)."""


def _load_settings() -> Settings:
    """Load settings, translating a pydantic failure into a friendly error."""
    from job_sentinel.config.settings import get_settings

    try:
        settings = get_settings()
    except Exception as exc:  # pydantic ValidationError → readable message
        # Log the underlying validation error server-side; keep the client
        # message generic so internal detail/traces never reach the response.
        logger.warning("Settings failed to load: {}", exc)
        msg = (
            "Settings could not load — check your .env (PORTAL_*/TELEGRAM_* "
            "variables are required)."
        )
        raise OpsConfigError(msg) from exc

    if settings.custom_adapter_path:
        from job_sentinel.adapters.registry import load_custom_adapter

        load_custom_adapter(settings.custom_adapter_path)
    return settings


class OpsRunner:
    """
    Owns the state of all background operations.

    A single instance lives for the lifetime of the API process. All state
    transitions happen under ``self._lock``; worker threads only touch their
    own OpStatus object through the ``_finish``/``_fail`` helpers.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._login = OpStatus()
        self._scrape = OpStatus()
        self._watcher: Scheduler | None = None
        self._watcher_repo: JobRepository | None = None
        self._watcher_interval: int | None = None

    # ── Status ─────────────────────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        """One JSON-friendly snapshot of everything the UI needs."""
        session: dict[str, Any] = {"exists": False, "saved_at": None}
        adapter: str | None = None
        adapters: list[str] = []
        poll_interval: int | None = None
        config_ok = True
        config_error = ""

        try:
            settings = _load_settings()
            adapter = settings.site_adapter
            poll_interval = settings.scraper.poll_interval_seconds
            path = settings.session_path
            if path.is_file():
                session["exists"] = True
                session["saved_at"] = datetime.fromtimestamp(
                    path.stat().st_mtime, tz=UTC
                ).isoformat()
        except OpsConfigError:
            # Surface a fixed, safe hint (the exception text is logged at the
            # raise site) so /api/ops/status never returns exception-derived text.
            config_ok = False
            config_error = "Settings could not load — check your .env (PORTAL_* / TELEGRAM_*)."

        from job_sentinel.adapters.registry import list_adapters

        adapters = list_adapters()

        with self._lock:
            return {
                "config_ok": config_ok,
                "config_error": config_error,
                "session": session,
                "login": self._login.model_dump(mode="json"),
                "scrape": self._scrape.model_dump(mode="json"),
                "watcher": {
                    "running": self._watcher is not None and self._watcher.running,
                    "interval_seconds": self._watcher_interval or poll_interval,
                },
                "adapter": adapter,
                "adapters": adapters,
            }

    # ── Login ──────────────────────────────────────────────────────────────

    def start_login(self, timeout: int = 300) -> None:
        """Open a visible browser for a one-time sign-in (saves the session)."""
        settings = _load_settings()
        with self._lock:
            if self._login.state == "running":
                raise OpsConflictError("A login is already in progress.")
            if self._scrape.state == "running":
                raise OpsConflictError("A scrape is running — wait for it to finish.")
            self._login = OpStatus(
                state="running",
                message="A browser window opened on the machine running the API. "
                "Sign in to the portal; the session saves automatically.",
                started_at=datetime.now(UTC),
            )
        thread = threading.Thread(target=self._login_worker, args=(settings, timeout), daemon=True)
        thread.start()

    def _login_worker(self, settings: Settings, timeout: int) -> None:
        from job_sentinel.core.session import interactive_login

        def on_event(message: str) -> None:
            with self._lock:
                if self._login.state == "running":
                    self._login.message = message

        try:
            interactive_login(settings, timeout_seconds=timeout, on_event=on_event)
            self._finish(
                "login",
                f"Session saved to {settings.session_path.name} — you're logged in.",
            )
        except Exception as exc:
            logger.warning("Login op failed: {}", exc)
            self._fail(
                "login",
                "Didn't detect a signed-in page in time. Start the login again "
                "and finish signing in (clear the challenge, enter credentials).",
            )

    # ── Session check (headless probe — is the saved session still valid?) ──

    def check_session(self) -> dict[str, Any]:
        """Probe the saved session against the portal and report validity."""
        from job_sentinel.core.session import check_session

        settings = _load_settings()
        with self._lock:
            if self._login.state == "running":
                raise OpsConflictError("Finish the login first — a browser is open.")
        status = check_session(settings)
        return status.model_dump(mode="json")

    # ── Scrape (one-shot) ──────────────────────────────────────────────────

    def start_scrape(self, *, send: bool = False) -> None:
        """Run one scrape cycle in the background (dry-run unless ``send``)."""
        settings = _load_settings()
        with self._lock:
            if self._scrape.state == "running":
                raise OpsConflictError("A scrape is already in progress.")
            if self._login.state == "running":
                raise OpsConflictError("Finish the login first — a browser is open.")
            self._scrape = OpStatus(
                state="running",
                message="Scraping the portal…",
                started_at=datetime.now(UTC),
            )
        thread = threading.Thread(target=self._scrape_worker, args=(settings, send), daemon=True)
        thread.start()

    def _scrape_worker(self, settings: Settings, send: bool) -> None:
        from job_sentinel.core.scheduler import Scheduler
        from job_sentinel.db.repository import JobRepository
        from job_sentinel.notifiers.telegram import TelegramNotifier

        repo: JobRepository | None = None
        try:
            run_settings = settings.model_copy(update={"dry_run": not send})
            repo = JobRepository(run_settings.db_path)
            notifier = TelegramNotifier(
                run_settings.telegram.bot_token, run_settings.telegram.chat_id
            )
            scheduler = Scheduler(run_settings, repo, notifier.send_new_jobs)
            result = scheduler.run_cycle()

            detail = result.model_dump(mode="json")
            if result.had_errors:
                self._fail(
                    "scrape",
                    "Scrape finished with errors — you may need to log in again.",
                    detail=detail,
                )
            else:
                self._finish(
                    "scrape",
                    f"Done: {result.new_count} new, {result.updated_count} updated, "
                    f"{result.closed_count} closed ({result.total_scraped} scraped).",
                    detail=detail,
                )
        except Exception as exc:
            # Full detail goes to the server log; the status surfaced via
            # /api/ops/status stays generic so no exception text leaks to a client.
            logger.exception("Scrape op failed: {}", exc)
            self._fail("scrape", "Scrape failed — check the portal session and the server logs.")
        finally:
            if repo is not None:
                repo.close()

    # ── Watcher (continuous monitoring, mirrors `job-sentinel run`) ────────

    def start_watcher(self) -> None:
        """Start the recurring scrape loop with Telegram/email alerts."""
        from job_sentinel.core.scheduler import Scheduler
        from job_sentinel.db.repository import JobRepository
        from job_sentinel.notifiers.email import EmailNotifier
        from job_sentinel.notifiers.telegram import TelegramNotifier

        settings = _load_settings()
        with self._lock:
            if self._watcher is not None and self._watcher.running:
                raise OpsConflictError("The watcher is already running.")

            repo = JobRepository(settings.db_path)
            notifier = TelegramNotifier(settings.telegram.bot_token, settings.telegram.chat_id)
            email = EmailNotifier(settings.email)

            def on_new_jobs(jobs: list[Any]) -> None:
                notifier.send_new_jobs(jobs)
                email.send_new_jobs(jobs)

            self._watcher_repo = repo
            self._watcher = Scheduler(settings, repo, on_new_jobs)
            self._watcher_interval = settings.scraper.poll_interval_seconds
        # start() triggers an immediate first cycle; keep it off the request thread.
        threading.Thread(target=self._watcher.start, daemon=True).start()
        logger.info("Watcher started from the API | interval={}s", self._watcher_interval)

    def stop_watcher(self) -> None:
        """Stop the recurring scrape loop."""
        with self._lock:
            watcher, repo = self._watcher, self._watcher_repo
            self._watcher = None
            self._watcher_repo = None
        if watcher is None:
            raise OpsConflictError("The watcher isn't running.")
        watcher.stop()
        if repo is not None:
            repo.close()
        logger.info("Watcher stopped from the API")

    # ── Helpers ────────────────────────────────────────────────────────────

    def _finish(self, op: str, message: str, detail: dict[str, Any] | None = None) -> None:
        self._set(op, "ok", message, detail)

    def _fail(self, op: str, message: str, detail: dict[str, Any] | None = None) -> None:
        self._set(op, "error", message, detail)

    def _set(self, op: str, state: OpState, message: str, detail: dict[str, Any] | None) -> None:
        with self._lock:
            current: OpStatus = getattr(self, f"_{op}")
            current.state = state
            current.message = message
            current.finished_at = datetime.now(UTC)
            if detail:
                current.detail = detail


_runner: OpsRunner | None = None
_runner_lock = threading.Lock()


def get_runner() -> OpsRunner:
    """Process-wide singleton — the API and tests share one runner."""
    global _runner
    with _runner_lock:
        if _runner is None:
            _runner = OpsRunner()
        return _runner
