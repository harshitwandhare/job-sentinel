"""
core/scheduler.py
──────────────────
APScheduler-based poll loop for Job Sentinel.

Why APScheduler over a raw ``threading.Timer`` loop?
  • Persistent job store — survives crashes (optional, SQLite-backed)
  • Mis-fire handling — if a poll is missed (PC sleeps), APScheduler can
    catch up or skip, rather than silently drifting
  • Rich trigger types: interval, cron, date — easy to add "only on weekdays"
  • Thread-pool executor — safe to run blocking Playwright in a background
    thread while the Telegram bot's asyncio loop runs in main thread

Threading model
───────────────
  Main thread   → asyncio event loop (python-telegram-bot Application)
  Thread pool   → APScheduler job (Playwright scrape, blocking I/O)
  Shared state  → JobRepository (SQLite WAL — safe for concurrent access)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger

from job_sentinel.adapters.registry import get_adapter
from job_sentinel.core.browser import browser_context
from job_sentinel.core.models import ApplicationStatus, JobPosting, ScrapeResult

if TYPE_CHECKING:
    from job_sentinel.config.settings import Settings
    from job_sentinel.db.repository import JobRepository

NotifyCallback = Callable[[list[JobPosting]], None]


class Scheduler:
    """
    Manages the recurring scrape cycle.

    Parameters
    ----------
    settings : Settings
        Full application settings.
    repository : JobRepository
        Shared DB for persistence.
    on_new_jobs : NotifyCallback
        Called with newly discovered postings after each cycle.
        Typically ``TelegramNotifier.send_new_jobs``.
    """

    def __init__(
        self,
        settings: Settings,
        repository: JobRepository,
        on_new_jobs: NotifyCallback,
    ) -> None:
        self._settings = settings
        self._repo = repository
        self._on_new_jobs = on_new_jobs

        self._scheduler = BackgroundScheduler(
            executors={"default": ThreadPoolExecutor(max_workers=1)},
            job_defaults={"coalesce": True, "max_instances": 1},
        )
        self._run_count = 0

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the background scheduler (non-blocking)."""
        interval = self._settings.scraper.poll_interval_seconds
        self._scheduler.add_job(
            func=self._scrape_cycle,
            trigger="interval",
            seconds=interval,
            id="scrape_cycle",
            name="Job Sentinel scrape",
            next_run_time=None,  # run immediately on first call via trigger_now()
        )
        self._scheduler.start()
        logger.info("Scheduler started | interval={}s", interval)
        # Trigger first run immediately
        self.trigger_now()

    def stop(self) -> None:
        """Gracefully shut down the scheduler."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped")

    def trigger_now(self) -> int:
        """
        Run one scrape cycle synchronously from the calling thread.

        Returns the number of new jobs found.
        Used by the ``/jobs`` Telegram command for on-demand refresh.
        """
        return self.run_cycle().new_count

    def run_cycle(self) -> ScrapeResult:
        """
        Run one scrape cycle synchronously and return the full result.

        Like :meth:`trigger_now` but keeps counts and errors, so callers
        (e.g. the local API) can report what actually happened.
        """
        return self._scrape_cycle()

    @property
    def running(self) -> bool:
        """Whether the background scheduler loop is active."""
        return bool(self._scheduler.running)

    # ── Scrape cycle ───────────────────────────────────────────────────────

    def _scrape_cycle(self) -> ScrapeResult:
        """
        Full scrape → filter → diff → persist → notify cycle.

        This runs in the APScheduler thread pool — must be thread-safe.
        """
        import time

        start = time.monotonic()
        self._run_count += 1
        adapter_id = self._settings.site_adapter

        result = ScrapeResult(adapter=adapter_id)
        logger.info("▶ Scrape cycle #{} | adapter={}", self._run_count, adapter_id)

        try:
            adapter = get_adapter(adapter_id, self._settings.scraper)

            with browser_context(
                self._settings.scraper, storage_state=self._settings.session_path
            ) as ctx:
                all_jobs = adapter.scrape(ctx)

            result.total_scraped = len(all_jobs)

            if not all_jobs:
                logger.info("Scrape returned 0 results")
                return result

            # Apply keyword filters
            keyword_filters = self._settings.filters.keyword_filters
            filtered = [j for j in all_jobs if j.matches_keywords(keyword_filters)]
            logger.info("Filter pass | matched={}/{}", len(filtered), len(all_jobs))

            # Diff against DB — find genuinely new postings
            new_jobs: list[JobPosting] = []
            for job in filtered:
                is_new = self._repo.save_job(job)
                if is_new:
                    new_jobs.append(job)
                    result.new_count += 1
                else:
                    result.updated_count += 1

            # Mark postings no longer on the portal as CLOSED
            result.closed_count = self._mark_closed(all_jobs)

            # Notify
            if new_jobs:
                logger.info("🔔 New jobs found: {}", len(new_jobs))
                if not self._settings.dry_run:
                    self._on_new_jobs(new_jobs)
                else:
                    logger.info("[DRY RUN] Would alert: {}", [j.title for j in new_jobs])
            else:
                logger.info("No new postings this cycle")

        except Exception as exc:
            msg = str(exc)
            result.errors.append(msg)
            logger.exception("Error in scrape cycle: {}", exc)

        finally:
            result.duration_seconds = time.monotonic() - start
            logger.info("◀ Cycle complete | {}", result)

        return result

    def _mark_closed(self, current_jobs: list[JobPosting]) -> int:
        """
        Mark any tracked jobs that disappeared from the portal as CLOSED.

        Returns the count of postings marked closed.
        """
        current_ids = {j.posting_id for j in current_jobs}
        open_statuses = [ApplicationStatus.NEW, ApplicationStatus.SEEN]
        closed_count = 0

        for status in open_statuses:
            for job in self._repo.get_by_status(status):
                if job.posting_id not in current_ids:
                    self._repo.update_status(job.posting_id, ApplicationStatus.CLOSED)
                    closed_count += 1
                    logger.debug("Marked CLOSED | id={} title={!r}", job.posting_id, job.title)

        return closed_count
