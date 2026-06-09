"""Tests for Telegram message formatting helpers."""

from __future__ import annotations

import pytest

from job_sentinel.core.models import ApplicationStatus, JobPosting
from job_sentinel.notifiers.telegram import _format_list_item, _format_new_job, escape


class TestEscapeMarkdown:
    @pytest.mark.parametrize("char", list(r"\_*[]()~`>#+-=|{}.!"))
    def test_special_chars_escaped(self, char: str) -> None:
        result = escape(char)
        assert result == f"\\{char}"

    def test_normal_text_unchanged(self) -> None:
        assert escape("Hello World 123") == "Hello World 123"

    def test_empty_string(self) -> None:
        assert escape("") == ""


class TestFormatNewJob:
    def _job(self) -> JobPosting:
        return JobPosting(
            posting_id="123",
            title="Software Engineer",
            employer="Google",
            location="Dallas, TX",
            job_type="Internship",
            posted_date="2025-01-15",
            deadline="2025-02-01",
            description_snippet="Build amazing things.",
            portal_url="https://utdallas.12twenty.com/posting/123",
            keywords_matched=["software"],
        )

    def test_contains_title(self) -> None:
        msg = _format_new_job(self._job())
        assert "Software Engineer" in msg

    def test_contains_employer(self) -> None:
        msg = _format_new_job(self._job())
        assert "Google" in msg

    def test_contains_posting_id(self) -> None:
        msg = _format_new_job(self._job())
        assert "123" in msg

    def test_contains_view_link(self) -> None:
        msg = _format_new_job(self._job())
        assert "View Posting" in msg

    def test_contains_keywords(self) -> None:
        msg = _format_new_job(self._job())
        assert "software" in msg

    def test_flags_soon_closing_deadline(self) -> None:
        from datetime import date, timedelta

        soon = (date.today() + timedelta(days=2)).strftime("%m/%d/%Y")
        msg = _format_new_job(JobPosting(posting_id="x", title="Role", deadline=soon))
        assert "Closes" in msg and "in 2 days" in msg

    def test_no_flag_for_far_or_unparseable_deadline(self) -> None:
        assert "Closes" not in _format_new_job(
            JobPosting(posting_id="x", title="Role", deadline="Apply Immediately")
        )
        assert "Closes" not in _format_new_job(
            JobPosting(posting_id="x", title="Role", deadline="12/31/2099")
        )


class TestFormatListItem:
    def test_contains_status_emoji(self) -> None:
        job = JobPosting(posting_id="x", title="Dev", status=ApplicationStatus.APPLIED)
        msg = _format_list_item(1, job)
        assert "✅" in msg

    def test_contains_title(self) -> None:
        job = JobPosting(posting_id="x", title="My Job Title")
        msg = _format_list_item(1, job)
        assert "My Job Title" in msg
