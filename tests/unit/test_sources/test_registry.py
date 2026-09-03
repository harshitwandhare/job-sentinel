"""Tests for the source registry and settings CSV parsing."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from job_sentinel.sources import registry
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
    assert "wellfound" in ids


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


def _settings(enabled: list[str]) -> Any:
    """Minimal stand-in for Settings: the registry only reads job_sources."""
    from job_sentinel.config.settings import JobSourceSettings

    job_sources = JobSourceSettings(
        _env_file=None,  # type: ignore[call-arg]
        JOB_SOURCES_ENABLED=enabled,
        THEMUSE_API_KEY="muse-key",
        ADZUNA_APP_ID="adz-id",
        ADZUNA_APP_KEY="adz-key",
        USAJOBS_API_KEY="usa-key",
        USAJOBS_EMAIL="me@example.com",
    )
    return SimpleNamespace(job_sources=job_sources)


def test_register_twice_warns(caplog: pytest.LogCaptureFixture) -> None:
    register_source(_FakeSource)
    with caplog.at_level("WARNING"):
        register_source(_FakeSource)
    assert _registry["fake_test_source"] is _FakeSource


def test_get_source_wraps_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _registry.pop("remoteok", None)

    def _boom(name: str) -> object:
        raise ImportError("no module")

    monkeypatch.setattr(registry.importlib, "import_module", _boom)
    with pytest.raises(ValueError, match="Failed to load built-in source 'remoteok'"):
        get_source("remoteok")


def test_instantiate_injects_api_keys() -> None:
    settings = _settings(["themuse"])
    muse = registry._instantiate_source("themuse", settings)
    assert muse._api_key == "muse-key"

    adzuna = registry._instantiate_source("adzuna", settings)
    assert adzuna.configured()
    assert adzuna._country == "us"

    usajobs = registry._instantiate_source("usajobs", settings)
    assert usajobs.configured()


def test_build_enabled_sources_returns_instances() -> None:
    sources = registry.build_enabled_sources(_settings(["remoteok", "arbeitnow"]))
    assert [s.SOURCE_ID for s in sources] == ["remoteok", "arbeitnow"]


def test_build_enabled_sources_skips_unloadable() -> None:
    """A source that will not instantiate is dropped, the rest still load."""
    sources = registry.build_enabled_sources(_settings(["__nope__", "remoteok"]))
    assert [s.SOURCE_ID for s in sources] == ["remoteok"]


def test_all_sources_status_shape() -> None:
    statuses = registry.all_sources_status(_settings(["remoteok"]))
    by_id = {s["id"]: s for s in statuses}
    assert by_id["remoteok"]["enabled"] is True
    assert by_id["themuse"]["enabled"] is False
    for entry in statuses:
        assert set(entry) == {
            "id",
            "label",
            "enabled",
            "requires_key",
            "is_scraper",
            "configured",
            "homepage",
        }


def test_all_sources_status_falls_back_to_class(monkeypatch: pytest.MonkeyPatch) -> None:
    """If a source cannot be instantiated, it is still listed as unconfigured."""
    real = registry._instantiate_source

    def _fail_remoteok(source_id: str, settings: Any) -> Any:
        if source_id == "remoteok":
            raise RuntimeError("missing extra")
        return real(source_id, settings)

    monkeypatch.setattr(registry, "_instantiate_source", _fail_remoteok)
    statuses = registry.all_sources_status(_settings(["remoteok"]))
    remoteok = next(s for s in statuses if s["id"] == "remoteok")
    assert remoteok["configured"] is False
    assert remoteok["enabled"] is True


def test_all_sources_status_drops_unloadable(monkeypatch: pytest.MonkeyPatch) -> None:
    """A source that neither instantiates nor imports is left out entirely."""
    monkeypatch.setattr(
        registry,
        "_instantiate_source",
        lambda source_id, settings: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    monkeypatch.setattr(
        registry,
        "get_source",
        lambda source_id: (_ for _ in ()).throw(ValueError("gone")),
    )
    assert registry.all_sources_status(_settings(["remoteok"])) == []
