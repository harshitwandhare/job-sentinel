"""Tests for core domain models."""

from __future__ import annotations

import pytest

from job_sentinel.core.models import ApplicationStatus, JobPosting, ScrapeResult


class TestJobPosting:
    def test_defaults_are_safe(self) -> None:
        job = JobPosting(posting_id="abc123")
        assert job.title == "Untitled Position"
        assert job.status == ApplicationStatus.NEW
        assert job.keywords_matched == []

    def test_whitespace_stripped(self) -> None:
        job = JobPosting(posting_id="x", title="  Software Engineer  ", employer="  Google  ")
        assert job.title == "Software Engineer"
        assert job.employer == "Google"

    def test_description_truncated_at_350(self) -> None:
        long_desc = "x" * 400
        job = JobPosting(posting_id="x", description_snippet=long_desc)
        assert len(job.description_snippet) <= 351  # 350 + ellipsis char
        assert job.description_snippet.endswith("…")

    def test_keyword_match_case_insensitive(self) -> None:
        job = JobPosting(posting_id="x", title="Software Engineer Intern")
        assert job.matches_keywords(["software", "DATA"]) is True
        assert "software" in job.keywords_matched

    def test_keyword_no_match(self) -> None:
        job = JobPosting(posting_id="x", title="Janitor")
        assert job.matches_keywords(["software", "engineer"]) is False
        assert job.keywords_matched == []

    def test_empty_keywords_matches_all(self) -> None:
        job = JobPosting(posting_id="x", title="Anything")
        assert job.matches_keywords([]) is True

    def test_touch_updates_updated_at(self) -> None:
        job = JobPosting(posting_id="x")
        before = job.updated_at
        job.touch()
        assert job.updated_at >= before

    def test_str_representation(self) -> None:
        job = JobPosting(posting_id="abc", title="Dev", employer="Corp")
        s = str(job)
        assert "abc" in s
        assert "Dev" in s


class TestApplicationStatus:
    def test_all_values_are_strings(self) -> None:
        for status in ApplicationStatus:
            assert isinstance(status.value, str)

    @pytest.mark.parametrize("val", ["new", "seen", "applied", "ignored", "closed"])
    def test_from_string(self, val: str) -> None:
        assert ApplicationStatus(val).value == val


class TestScrapeResult:
    def test_had_errors_false_by_default(self) -> None:
        result = ScrapeResult(adapter="12twenty")
        assert result.had_errors is False

    def test_had_errors_true_when_errors(self) -> None:
        result = ScrapeResult(adapter="12twenty", errors=["something broke"])
        assert result.had_errors is True

    def test_str(self) -> None:
        result = ScrapeResult(adapter="12twenty", total_scraped=5, new_count=2)
        s = str(result)
        assert "12twenty" in s
