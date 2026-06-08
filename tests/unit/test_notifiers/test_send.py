"""Tests for Telegram delivery (the HTTP send path), mocked with respx."""

from __future__ import annotations

import httpx
import respx

from job_sentinel.core.models import JobPosting
from job_sentinel.notifiers.telegram import TelegramNotifier

_TOKEN = "123456:TEST_TOKEN"
_API = f"https://api.telegram.org/bot{_TOKEN}/sendMessage"


def _notifier() -> TelegramNotifier:
    return TelegramNotifier(bot_token=_TOKEN, chat_id="999")


@respx.mock
def test_send_text_returns_true_on_ok() -> None:
    route = respx.post(_API).mock(return_value=httpx.Response(200, json={"ok": True}))
    assert _notifier().send_text("hello") is True
    assert route.called
    sent = route.calls.last.request
    assert b"MarkdownV2" in sent.content


@respx.mock
def test_send_text_returns_false_when_api_not_ok() -> None:
    respx.post(_API).mock(
        return_value=httpx.Response(200, json={"ok": False, "description": "bad"})
    )
    assert _notifier().send_text("hello") is False


@respx.mock
def test_send_retries_then_fails_on_persistent_5xx() -> None:
    route = respx.post(_API).mock(return_value=httpx.Response(500, text="server error"))
    assert _notifier().send_text("hello") is False
    # tenacity retries up to 3 attempts
    assert route.call_count == 3


@respx.mock
def test_send_new_jobs_sends_a_message_per_job() -> None:
    route = respx.post(_API).mock(return_value=httpx.Response(200, json={"ok": True}))
    jobs = [
        JobPosting(posting_id="1", title="SWE Intern", employer="Google"),
        JobPosting(posting_id="2", title="Data Analyst", employer="Meta"),
    ]
    _notifier().send_new_jobs(jobs)
    # 1 summary header (because >1 job) + 1 per job = 3
    assert route.call_count == 3


@respx.mock
def test_send_new_jobs_no_header_for_single_job() -> None:
    route = respx.post(_API).mock(return_value=httpx.Response(200, json={"ok": True}))
    _notifier().send_new_jobs([JobPosting(posting_id="1", title="Solo")])
    assert route.call_count == 1


def test_send_new_jobs_empty_is_noop() -> None:
    # No respx mock registered — if it tried to send, it would raise.
    _notifier().send_new_jobs([])


@respx.mock
def test_send_jobs_list_empty_sends_placeholder() -> None:
    route = respx.post(_API).mock(return_value=httpx.Response(200, json={"ok": True}))
    _notifier().send_jobs_list([])
    assert route.call_count == 1
