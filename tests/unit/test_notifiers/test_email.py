"""Tests for the SMTP email notifier (smtplib mocked)."""

from __future__ import annotations

from unittest.mock import patch

from job_sentinel.config.settings import EmailSettings
from job_sentinel.core.models import JobPosting
from job_sentinel.notifiers.email import EmailNotifier


def _settings(**kw: object) -> EmailSettings:
    base = {
        "enabled": True,
        "smtp_host": "smtp.example.com",
        "smtp_port": 587,
        "username": "me@example.com",
        "password": "pw",
        "recipient": "me@example.com",
    }
    base.update(kw)
    return EmailSettings(**base)  # type: ignore[arg-type]


_JOBS = [JobPosting(posting_id="1", title="SWE Intern", employer="ACME", deadline="06/12/2026")]


def test_disabled_is_noop() -> None:
    n = EmailNotifier(EmailSettings(enabled=False))
    assert n.enabled is False
    assert n.send_new_jobs(_JOBS) is False


def test_enabled_requires_host_and_recipient() -> None:
    assert EmailNotifier(_settings(smtp_host="")).enabled is False
    assert EmailNotifier(_settings(recipient="")).enabled is False
    assert EmailNotifier(_settings()).enabled is True


def test_empty_jobs_is_noop() -> None:
    with patch("smtplib.SMTP") as smtp:
        assert EmailNotifier(_settings()).send_new_jobs([]) is False
        smtp.assert_not_called()


def test_sends_via_starttls() -> None:
    with patch("smtplib.SMTP") as smtp:
        srv = smtp.return_value.__enter__.return_value
        ok = EmailNotifier(_settings(use_tls=True)).send_new_jobs(_JOBS)
        assert ok is True
        srv.starttls.assert_called_once()
        srv.login.assert_called_once_with("me@example.com", "pw")
        srv.send_message.assert_called_once()
        msg = srv.send_message.call_args.args[0]
        assert "1 new posting" in msg["Subject"]
        assert "SWE Intern" in msg.get_content()


def test_sends_via_ssl_when_no_tls() -> None:
    with patch("smtplib.SMTP_SSL") as smtp:
        srv = smtp.return_value.__enter__.return_value
        assert EmailNotifier(_settings(use_tls=False)).send_new_jobs(_JOBS) is True
        srv.send_message.assert_called_once()


def test_send_failure_is_swallowed() -> None:
    with patch("smtplib.SMTP", side_effect=OSError("connection refused")):
        assert EmailNotifier(_settings()).send_new_jobs(_JOBS) is False
