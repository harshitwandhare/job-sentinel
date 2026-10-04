"""Tests for the Discord webhook notifier (httpx mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from job_sentinel.config.settings import DiscordSettings
from job_sentinel.core.models import JobPosting
from job_sentinel.notifiers.discord import DiscordNotifier

_WEBHOOK = "https://discord.com/api/webhooks/123/abc"

_JOB = JobPosting(
    posting_id="42",
    title="Software Engineer Intern",
    employer="ACME Corp",
    location="Dallas, TX",
    portal_url="https://example.com/job/42",
)
_JOB_URGENT = JobPosting(
    posting_id="99",
    title="Urgent Role",
    employer="Startup",
    portal_url="https://example.com/job/99",
    deadline="2020-01-01",  # well in the past → days_until returns negative → not urgent
)


def _settings(url: str = _WEBHOOK) -> DiscordSettings:
    return DiscordSettings(webhook_url=url)  # type: ignore[call-arg]


def _mock_response(status: int = 204) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.raise_for_status = MagicMock()
    return resp


# ── basic behaviour ───────────────────────────────────────────────────────────


def test_disabled_when_no_url() -> None:
    n = DiscordNotifier(DiscordSettings())
    assert n.enabled is False


def test_enabled_when_url_set() -> None:
    n = DiscordNotifier(_settings())
    assert n.enabled is True


def test_disabled_send_is_noop() -> None:
    n = DiscordNotifier(DiscordSettings())
    assert n.send_new_jobs([_JOB]) is False


def test_empty_jobs_is_noop() -> None:
    n = DiscordNotifier(_settings())
    with patch("httpx.Client") as mock_client:
        result = n.send_new_jobs([])
        assert result is False
        mock_client.assert_not_called()


# ── successful delivery ───────────────────────────────────────────────────────


def test_single_job_posts_one_embed() -> None:
    with patch("httpx.Client") as mock_client:
        ctx = mock_client.return_value.__enter__.return_value
        ctx.post.return_value = _mock_response(204)

        result = DiscordNotifier(_settings()).send_new_jobs([_JOB])

        assert result is True
        assert ctx.post.call_count == 1
        payload = ctx.post.call_args.kwargs["json"]
        assert "embeds" in payload
        assert payload["embeds"][0]["title"] == "Software Engineer Intern"


def test_multiple_jobs_posts_summary_then_embeds() -> None:
    jobs = [_JOB, _JOB]
    with patch("httpx.Client") as mock_client:
        ctx = mock_client.return_value.__enter__.return_value
        ctx.post.return_value = _mock_response(204)

        DiscordNotifier(_settings()).send_new_jobs(jobs)

        # 1 summary message + 2 individual embeds
        assert ctx.post.call_count == 3
        first_payload = ctx.post.call_args_list[0].kwargs["json"]
        assert "content" in first_payload
        assert "2 new job postings" in first_payload["content"]


def test_embed_includes_employer_and_location() -> None:
    with patch("httpx.Client") as mock_client:
        ctx = mock_client.return_value.__enter__.return_value
        ctx.post.return_value = _mock_response(204)

        DiscordNotifier(_settings()).send_new_jobs([_JOB])

        payload = ctx.post.call_args.kwargs["json"]
        fields = payload["embeds"][0]["fields"]
        field_names = [f["name"] for f in fields]
        assert "Company" in field_names
        assert "Location" in field_names


def test_embed_url_points_to_portal() -> None:
    with patch("httpx.Client") as mock_client:
        ctx = mock_client.return_value.__enter__.return_value
        ctx.post.return_value = _mock_response(204)

        DiscordNotifier(_settings()).send_new_jobs([_JOB])

        payload = ctx.post.call_args.kwargs["json"]
        assert payload["embeds"][0]["url"] == "https://example.com/job/42"


# ── error handling ────────────────────────────────────────────────────────────


def test_http_error_is_swallowed_returns_false() -> None:
    import httpx

    with patch("httpx.Client") as mock_client:
        ctx = mock_client.return_value.__enter__.return_value
        ctx.post.side_effect = httpx.RequestError("timeout")

        result = DiscordNotifier(_settings()).send_new_jobs([_JOB])

        assert result is False


def test_unexpected_error_is_swallowed() -> None:
    with patch("httpx.Client") as mock_client:
        ctx = mock_client.return_value.__enter__.return_value
        ctx.post.side_effect = RuntimeError("unexpected")

        result = DiscordNotifier(_settings()).send_new_jobs([_JOB])

        assert result is False


def test_retry_error_in_post_message_swallowed() -> None:
    """RetryError raised by _post_message's tenacity wrapper returns False."""
    from unittest.mock import MagicMock

    from tenacity import RetryError

    future_mock = MagicMock()
    future_mock.exception.return_value = ConnectionError("network down")

    with patch.object(DiscordNotifier, "_post", side_effect=RetryError(future_mock)):
        # multi-job path calls _post_message for the summary first
        jobs = [_JOB, _JOB]
        result = DiscordNotifier(_settings()).send_new_jobs(jobs)
        assert result is False


# ── embed field coverage ──────────────────────────────────────────────────────


def test_embed_includes_job_type_field() -> None:
    job = JobPosting(
        posting_id="t1",
        title="Engineer",
        employer="Acme",
        portal_url="https://x.com",
        job_type="Full-time",
    )
    with patch("httpx.Client") as mock_client:
        ctx = mock_client.return_value.__enter__.return_value
        ctx.post.return_value = _mock_response(204)

        DiscordNotifier(_settings()).send_new_jobs([job])

        fields = ctx.post.call_args.kwargs["json"]["embeds"][0]["fields"]
        assert any(f["name"] == "Type" and f["value"] == "Full-time" for f in fields)


def test_embed_includes_posted_date_field() -> None:
    job = JobPosting(
        posting_id="t2",
        title="Engineer",
        employer="Acme",
        portal_url="https://x.com",
        posted_date="2026-09-01",
    )
    with patch("httpx.Client") as mock_client:
        ctx = mock_client.return_value.__enter__.return_value
        ctx.post.return_value = _mock_response(204)

        DiscordNotifier(_settings()).send_new_jobs([job])

        fields = ctx.post.call_args.kwargs["json"]["embeds"][0]["fields"]
        assert any(f["name"] == "Posted" and f["value"] == "2026-09-01" for f in fields)


@pytest.mark.parametrize(
    ("days_offset", "expected_fragment"),
    [
        (0, "today"),
        (1, "tomorrow"),
        (5, "in 5d"),
    ],
)
def test_urgent_deadline_label_in_embed(days_offset: int, expected_fragment: str) -> None:
    """Deadlines within 7 days should include a human-readable urgency label."""
    import datetime

    deadline = (datetime.date.today() + datetime.timedelta(days=days_offset)).isoformat()
    job = JobPosting(
        posting_id="t3",
        title="Urgent Role",
        employer="Startup",
        portal_url="https://x.com",
        deadline=deadline,
    )
    with patch("httpx.Client") as mock_client:
        ctx = mock_client.return_value.__enter__.return_value
        ctx.post.return_value = _mock_response(204)

        DiscordNotifier(_settings()).send_new_jobs([job])

        fields = ctx.post.call_args.kwargs["json"]["embeds"][0]["fields"]
        deadline_field = next(f for f in fields if f["name"] == "Deadline")
        assert expected_fragment in deadline_field["value"]


# ── colour selection ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("deadline", "expected_colour"),
    [
        ("2099-12-31", 0x2ECC71),  # far future → green
        ("", 0x2ECC71),  # no deadline → green
    ],
)
def test_embed_colour(deadline: str, expected_colour: int) -> None:
    job = JobPosting(
        posting_id="1",
        title="Role",
        employer="Co",
        portal_url="https://x.com",
        deadline=deadline,
    )
    with patch("httpx.Client") as mock_client:
        ctx = mock_client.return_value.__enter__.return_value
        ctx.post.return_value = _mock_response(204)

        DiscordNotifier(_settings()).send_new_jobs([job])

        payload = ctx.post.call_args.kwargs["json"]
        assert payload["embeds"][0]["color"] == expected_colour
