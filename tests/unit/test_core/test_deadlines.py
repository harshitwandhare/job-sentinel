"""Tests for free-form deadline parsing."""

from __future__ import annotations

from datetime import date

from job_sentinel.core.deadlines import days_until, is_closing_soon, parse_deadline


class TestParseDeadline:
    def test_mdy_slash(self) -> None:
        assert parse_deadline("06/12/2026, 5:00pm CDT") == date(2026, 6, 12)

    def test_single_digit_mdy(self) -> None:
        assert parse_deadline("Apply by 6/5/2026") == date(2026, 6, 5)

    def test_iso(self) -> None:
        assert parse_deadline("Closes 2026-07-01") == date(2026, 7, 1)

    def test_month_day_year(self) -> None:
        assert parse_deadline("June 12, 2026") == date(2026, 6, 12)
        assert parse_deadline("Jun 12 2026") == date(2026, 6, 12)

    def test_day_month_year(self) -> None:
        assert parse_deadline("12 June 2026") == date(2026, 6, 12)

    def test_unparseable_returns_none(self) -> None:
        assert parse_deadline("Apply Immediately") is None
        assert parse_deadline("") is None
        assert parse_deadline(None) is None

    def test_invalid_date_returns_none(self) -> None:
        assert parse_deadline("13/45/2026") is None


class TestDaysUntilAndSoon:
    _TODAY = date(2026, 6, 10)

    def test_days_until(self) -> None:
        assert days_until("06/12/2026", today=self._TODAY) == 2
        assert days_until("06/09/2026", today=self._TODAY) == -1

    def test_none_when_unparseable(self) -> None:
        assert days_until("Apply Immediately", today=self._TODAY) is None

    def test_is_closing_soon(self) -> None:
        assert is_closing_soon("06/12/2026", within_days=5, today=self._TODAY) is True
        assert is_closing_soon("06/20/2026", within_days=5, today=self._TODAY) is False
        assert is_closing_soon("06/09/2026", within_days=5, today=self._TODAY) is False  # past
        assert is_closing_soon("Apply Immediately", within_days=5, today=self._TODAY) is False
