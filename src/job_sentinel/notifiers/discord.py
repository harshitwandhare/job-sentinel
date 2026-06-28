"""
notifiers/discord.py
─────────────────────
Discord webhook notifier — a third alert channel alongside Telegram and email.

Sends job alerts as rich Discord embeds using the Incoming Webhooks API.
No Discord bot token or OAuth required; just a webhook URL from a channel's
Integration settings (Server Settings → Integrations → Webhooks → New Webhook).

Uses httpx (sync) with tenacity retries — same transport layer as the Telegram
notifier so the two behave consistently in the scheduler thread pool.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
from loguru import logger
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from job_sentinel.core.deadlines import days_until

if TYPE_CHECKING:
    from job_sentinel.config.settings import DiscordSettings
    from job_sentinel.core.models import JobPosting

# Embed colour constants (Discord uses decimal integers for colours)
_COLOUR_NEW = 0x2ECC71  # emerald — new posting
_COLOUR_URGENT = 0xE74C3C  # red — deadline within a week


class DiscordNotifier:
    """Sends job-alert embeds to a Discord channel via an Incoming Webhook."""

    def __init__(self, settings: DiscordSettings) -> None:
        self._url = settings.webhook_url

    @property
    def enabled(self) -> bool:
        return bool(self._url)

    def send_new_jobs(self, jobs: list[JobPosting]) -> bool:
        """Post an alert for each new posting. Returns False if disabled or all posts fail."""
        if not self.enabled or not jobs:
            return False

        if len(jobs) > 1:
            self._post_message(f"🔔 **{len(jobs)} new job postings** found!")

        ok = True
        for job in jobs:
            ok = self._post_embed(job) and ok

        logger.info("Discord alert sent | jobs={}", len(jobs))
        return ok

    # ── internals ────────────────────────────────────────────────────────────

    def _post_message(self, content: str) -> bool:
        try:
            return self._post({"content": content})
        except RetryError as exc:
            logger.error("Discord send failed after retries: {}", exc.last_attempt.exception())
        except Exception as exc:
            logger.exception("Unexpected Discord send error: {}", exc)
        return False

    def _post_embed(self, job: JobPosting) -> bool:
        days = days_until(job.deadline) if job.deadline else None
        urgent = days is not None and 0 <= days <= 7
        colour = _COLOUR_URGENT if urgent else _COLOUR_NEW

        fields: list[dict[str, object]] = []
        if job.employer:
            fields.append({"name": "Company", "value": job.employer, "inline": True})
        if job.location:
            fields.append({"name": "Location", "value": job.location, "inline": True})
        if job.job_type:
            fields.append({"name": "Type", "value": job.job_type, "inline": True})
        if job.deadline:
            deadline_val = job.deadline
            if urgent:
                when = "today" if days == 0 else ("tomorrow" if days == 1 else f"in {days}d")
                deadline_val = f"{job.deadline} ⏰ closes {when}"
            fields.append({"name": "Deadline", "value": deadline_val, "inline": True})
        if job.posted_date:
            fields.append({"name": "Posted", "value": job.posted_date, "inline": True})

        description = job.description_snippet[:300] if job.description_snippet else ""

        embed: dict[str, object] = {
            "title": job.title,
            "url": job.portal_url,
            "color": colour,
            "description": description,
            "fields": fields,
            "footer": {"text": f"ID: {job.posting_id}"},
        }

        payload: dict[str, object] = {"embeds": [embed]}
        try:
            return self._post(payload)
        except RetryError as exc:
            logger.error(
                "Discord embed send failed after retries: {}", exc.last_attempt.exception()
            )
        except Exception as exc:
            logger.exception("Unexpected Discord embed error: {}", exc)
        return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
        reraise=False,
    )
    def _post(self, payload: dict[str, object]) -> bool:
        with httpx.Client(timeout=15, http2=True) as client:
            resp = client.post(self._url, json=payload)
        resp.raise_for_status()
        # 204 No Content is the normal Discord webhook success response
        return True
