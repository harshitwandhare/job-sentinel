"""
notifiers/email.py
───────────────────
Optional SMTP email notifier — a second alert channel alongside Telegram.

Stdlib only (``smtplib`` + ``email.message``): no third-party SMTP client needed.
Mirrors :class:`~job_sentinel.notifiers.telegram.TelegramNotifier`'s
``send_new_jobs`` shape so the scheduler can fan out to both. Like the Telegram
notifier, it never raises into the scheduler: a delivery failure is logged and
swallowed.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from job_sentinel.config.settings import EmailSettings
    from job_sentinel.core.models import JobPosting


class EmailNotifier:
    """Sends a digest email when new postings are found."""

    def __init__(self, settings: EmailSettings) -> None:
        self._s = settings

    @property
    def enabled(self) -> bool:
        return self._s.configured

    def send_new_jobs(self, jobs: list[JobPosting]) -> bool:
        """Email a digest of new postings. No-op (returns False) if disabled/empty."""
        if not self.enabled or not jobs:
            return False
        try:
            self._send(self._compose(jobs))
        except Exception as exc:
            logger.error("Email send failed: {}", exc)
            return False
        logger.info("Email alert sent | jobs={}", len(jobs))
        return True

    # ── internals ───────────────────────────────────────────────────────────

    def _compose(self, jobs: list[JobPosting]) -> EmailMessage:
        msg = EmailMessage()
        msg["Subject"] = f"Job Sentinel: {len(jobs)} new posting{'s' if len(jobs) != 1 else ''}"
        msg["From"] = self._s.sender or self._s.username
        msg["To"] = self._s.recipient

        lines = [f"{len(jobs)} new job posting(s) found:\n"]
        for j in jobs:
            meta = " | ".join(p for p in (j.employer, j.location, j.job_type) if p)
            lines.append(f"• {j.title}")
            if meta:
                lines.append(f"    {meta}")
            if j.deadline:
                lines.append(f"    Deadline: {j.deadline}")
            if j.portal_url:
                lines.append(f"    {j.portal_url}")
            lines.append("")
        msg.set_content("\n".join(lines))
        return msg

    def _send(self, msg: EmailMessage) -> None:
        s = self._s
        if s.use_tls:
            with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=20) as srv:
                srv.starttls()
                if s.username:
                    srv.login(s.username, s.password)
                srv.send_message(msg)
        else:
            with smtplib.SMTP_SSL(s.smtp_host, s.smtp_port, timeout=20) as srv:
                if s.username:
                    srv.login(s.username, s.password)
                srv.send_message(msg)
