"""Tests for the source registry and settings CSV parsing."""

from __future__ import annotations

import pytest

from job_sentinel.sources.base import JobPosting, JobQuery, JobSource
from job_sentinel.sources.registry import (
    _registry,
    get_source,
    list_sources,
    register_source,
)


class _FakeSource(JobSource):
    SOURCE_ID = "fake_test_source"
    LABEL = "Fake"

    def search(self, query: JobQuery) -> list[JobPosting]:
        return []


def test_register_and_get() -> None:
    register_source(_FakeSource)
    cls = get_source("fake_test_source")
    assert cls is _FakeSource


def test_get_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown source"):
        get_source("__nonexistent__")


def test_register_without_source_id_raises() -> None:
    class _Bad(JobSource):
        SOURCE_ID = ""

        def search(self, query: JobQuery) -> list[JobPosting]:
            return []

    with pytest.raises(ValueError, match="SOURCE_ID"):
        register_source(_Bad)


def test_list_sources_includes_builtins() -> None:
    ids = list_sources()
    assert "remoteok" in ids
    assert "adzuna" in ids
    assert "usajobs" in ids
    assert "himalayas" in ids


def test_builtin_remoteok_lazy_loads() -> None:
    """get_source should lazy-load a built-in without it being pre-registered."""
    # Remove from registry if already there
    _registry.pop("remoteok", None)
    cls = get_source("remoteok")
    assert cls.SOURCE_ID == "remoteok"
    assert cls.default_enabled is True


def test_settings_csv_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    """JobSourceSettings should parse comma-separated enabled_sources."""
    monkeypatch.setenv("JOB_SOURCES_ENABLED", "remoteok,adzuna")
    # Need to re-instantiate to pick up env change
    from job_sentinel.config.settings import JobSourceSettings

    s = JobSourceSettings()
    assert "remoteok" in s.enabled_sources
    assert "adzuna" in s.enabled_sources


def test_settings_secret_fields_not_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    """Secret keys must not appear in repr()."""
    monkeypatch.setenv("ADZUNA_APP_KEY", "supersecret")
    from job_sentinel.config.settings import JobSourceSettings

    s = JobSourceSettings()
    assert "supersecret" not in repr(s)
