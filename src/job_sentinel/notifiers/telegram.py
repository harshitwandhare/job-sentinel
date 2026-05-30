"""
notifiers/telegram.py
──────────────────────
Telegram notification delivery for Job Sentinel.

Uses **httpx** (sync) for direct Bot API calls — no asyncio required since
the notifier runs from the APScheduler thread pool, not the main event loop.

Message format
──────────────
All messages use Telegram's MarkdownV2 — rich formatting with:
  • Bold job titles
  • Inline code for posting IDs (makes them easy to copy for /applied)
  • Clickable "View Posting →" links
  • Emoji for visual hierarchy

Rate limiting
─────────────
Telegram allows 30 messages/second to a single chat.
We add a 0.5s delay between messages to stay well under this limit.
"""

from __future__ import annotations

import time

import httpx
from loguru import logger
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from job_sentinel.core.models import ApplicationStatus, JobPosting

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
_DELAY_BETWEEN_MSGS = 0.5  # seconds


class TelegramNotifier:
    """
    Sends formatted job-alert messages to a Telegram chat.

    Parameters
    ----------
    bot_token : str
        Token from @BotFather.
    chat_id : str
        Target chat or user ID.
    """

    def __init__(self, bot_token: str, chat_id: str) -> None:
        self._url = _TELEGRAM_API.format(token=bot_token)
        self._chat_id = chat_id

    # ── Public API ────────────────────────────────────────────────────────

    def send_new_jobs(self, jobs: list[JobPosting]) -> None:
        """Send individual alert for each new job. Called by Scheduler."""
        if not jobs:
            return

        if len(jobs) > 1:
            self._send(f"🔔 *{escape(str(len(jobs)))} new job postings* found\\!")
            time.sleep(_DELAY_BETWEEN_MSGS)

        for job in jobs:
            self._send(_format_new_job(job))
            time.sleep(_DELAY_BETWEEN_MSGS)

    def send_text(self, text: str) -> bool:
        """Send a plain MarkdownV2 message. Used by bot command handlers."""
        return self._send(text)

    def send_jobs_list(self, jobs: list[JobPosting], header: str = "") -> None:
        """Send a compact list — used by /jobs and /recent commands."""
        if not jobs:
            self._send("📭 No job postings found\\.")
            return
        if header:
            self._send(escape(header))
            time.sleep(_DELAY_BETWEEN_MSGS)
        for i, job in enumerate(jobs, 1):
            self._send(_format_list_item(i, job))
            time.sleep(_DELAY_BETWEEN_MSGS)

    # ── Internal ──────────────────────────────────────────────────────────

    def _send(self, text: str) -> bool:
        """
        Send one message to the Telegram Bot API.

        Transient transport failures (network errors, HTTP 4xx/5xx) are
        retried with exponential backoff by :meth:`_post`. After retries are
        exhausted — or on any other unexpected error — this logs and returns
        ``False``. A notification failure must never crash the scheduler.
        """
        payload = {
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": "MarkdownV2",
            "disable_web_page_preview": False,
        }
        try:
            return self._post(payload)
        except RetryError as exc:
            # All retry attempts exhausted — unwrap the underlying cause to log it.
            logger.error("Telegram send failed after retries: {}", exc.last_attempt.exception())
        except Exception as exc:
            logger.exception("Unexpected Telegram send error: {}", exc)
        return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
        reraise=False,
    )
    def _post(self, payload: dict[str, object]) -> bool:
        """
        POST the payload once. Raises on transport failure so tenacity retries.

        A well-formed response whose ``ok`` field is ``False`` is a permanent
        error (bad chat_id, bad markup) — we log and return ``False`` rather
        than retrying a request that will never succeed.
        """
        with httpx.Client(timeout=15, http2=True) as client:
            resp = client.post(self._url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            logger.error("Telegram API not ok: {}", data)
            return False
        return True


# ─────────────────────────────────────────────────────────────────────────────
# MarkdownV2 formatting helpers
# ─────────────────────────────────────────────────────────────────────────────

_MD_SPECIAL = r"\_*[]()~`>#+-=|{}.!"


def escape(text: str) -> str:
    """Escape all MarkdownV2 special characters in a plain string."""
    return "".join(f"\\{c}" if c in _MD_SPECIAL else c for c in str(text))


_STATUS_EMOJI: dict[str, str] = {
    ApplicationStatus.NEW.value: "🆕",
    ApplicationStatus.SEEN.value: "👁",
    ApplicationStatus.APPLIED.value: "✅",
    ApplicationStatus.IGNORED.value: "🚫",
    ApplicationStatus.CLOSED.value: "🔒",
}


def _format_new_job(job: JobPosting) -> str:
    """
    Full-detail alert message for a newly discovered job.

    Example:

        🆕 *Software Engineer Intern*

        🏢 Google
        📍 Dallas, TX  •  🕐 Internship
        📅 Posted: 2025-01-15  •  ⏳ Deadline: 2025-02-01

        _First 200 chars of description..._

        🏷 Keywords: `software`, `engineer`

        [View Posting →](https://...)
        `ID: 123456`
    """
    lines = [
        f"🆕 *{escape(job.title)}*",
        "",
        f"🏢 {escape(job.employer or 'N/A')}",
        f"📍 {escape(job.location or 'N/A')}  •  🕐 {escape(job.job_type or 'N/A')}",
    ]

    if job.posted_date or job.deadline:
        date_line = f"📅 {escape(job.posted_date)}" if job.posted_date else ""
        if job.deadline:
            date_line += f"  •  ⏳ Deadline: {escape(job.deadline)}"
        lines.append(date_line.strip(" •"))

    if job.description_snippet:
        snippet = job.description_snippet[:200]
        lines += ["", f"_{escape(snippet)}_"]

    if job.keywords_matched:
        kws = "  ".join(f"`{escape(k)}`" for k in job.keywords_matched)
        lines += ["", f"🏷 {kws}"]

    lines += [
        "",
        f"[View Posting →]({escape(job.portal_url)})",
        f"`ID: {escape(job.posting_id)}`",
    ]
    return "\n".join(lines)


def _format_list_item(index: int, job: JobPosting) -> str:
    """Compact one-liner used by /jobs and /recent."""
    emoji = _STATUS_EMOJI.get(job.status.value, "❓")
    return (
        f"{emoji} *{escape(job.title)}*\n"
        f"🏢 {escape(job.employer or 'N/A')}  •  📍 {escape(job.location or 'N/A')}\n"
        f"[View →]({escape(job.portal_url)})  `{escape(job.posting_id)}`"
    )
