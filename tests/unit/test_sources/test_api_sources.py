"""
API tests for the /api/sources/* routes.

- GET /api/sources
- PUT /api/sources/config (.env round-trip via monkeypatch)
- POST /api/sources/search (monkeypatched sources, dedupe+errors)
- POST /api/sources/company
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from pathlib import Path

import httpx
import respx
from fastapi.testclient import TestClient

from job_sentinel.api.app import create_app
from job_sentinel.core.models import ApplicationStatus, JobPosting
from job_sentinel.sources.base import JobQuery, JobSource

# ── Helpers ──────────────────────────────────────────────────────────────────


def _client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(
            profile_path=tmp_path / "profile.yaml",
            db_path=tmp_path / "j.db",
            auth_dir=tmp_path,
        )
    )


def _make_job(title: str, employer: str, url: str = "") -> JobPosting:
    return JobPosting(
        posting_id=f"test:{title}",
        title=title,
        employer=employer,
        portal_url=url,
        status=ApplicationStatus.NEW,
        source_adapter="test",
    )


class _FakeSource(JobSource):
    SOURCE_ID = "fake"
    LABEL = "Fake"

    def __init__(self, jobs: list[JobPosting] | None = None) -> None:
        self._jobs = jobs or []

    def search(self, query: JobQuery) -> list[JobPosting]:
        return self._jobs


class _ErrorSource(JobSource):
    SOURCE_ID = "errorsrc"
    LABEL = "Error"

    def search(self, query: JobQuery) -> list[JobPosting]:
        raise RuntimeError("bang")


# ── GET /api/sources ──────────────────────────────────────────────────────────


def test_get_sources_returns_list(tmp_path: Path) -> None:
    c = _client(tmp_path)
    resp = c.get("/api/sources")
    assert resp.status_code == 200
    data = resp.json()
    assert "sources" in data
    sources = data["sources"]
    assert isinstance(sources, list)
    ids = [s["id"] for s in sources]
    assert "remoteok" in ids
    assert "adzuna" in ids


def test_sources_have_required_fields(tmp_path: Path) -> None:
    c = _client(tmp_path)
    resp = c.get("/api/sources")
    for src in resp.json()["sources"]:
        assert "id" in src
        assert "label" in src
        assert "enabled" in src
        assert "requires_key" in src
        assert "is_scraper" in src
        assert "configured" in src
        assert "homepage" in src


# ── PUT /api/sources/config ───────────────────────────────────────────────────


def test_put_sources_config_updates_env(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("")

    c = _client(tmp_path)

    with (
        patch("job_sentinel.config.settings._ENV_FILE", str(env_file)),
        patch("job_sentinel.api.app._update_env_file") as mock_update,
    ):
        resp = c.put(
            "/api/sources/config",
            json={"enabled_sources": ["remoteok", "adzuna"]},
        )
        assert resp.status_code == 200
        mock_update.assert_called_once()
        updates = mock_update.call_args[0][0]
        assert "JOB_SOURCES_ENABLED" in updates
        assert "adzuna" in updates["JOB_SOURCES_ENABLED"]


def test_put_sources_config_does_not_echo_keys(tmp_path: Path) -> None:
    c = _client(tmp_path)

    with patch("job_sentinel.api.app._update_env_file"):
        resp = c.put(
            "/api/sources/config",
            json={"keys": {"ADZUNA_APP_KEY": "super_secret_key"}},
        )
    assert resp.status_code == 200
    # The raw key must not appear in the response body
    assert "super_secret_key" not in resp.text


# ── POST /api/sources/search ──────────────────────────────────────────────────


def test_sources_search_returns_results(tmp_path: Path) -> None:
    jobs = [_make_job("Python Dev", "Corp")]
    src = _FakeSource(jobs)

    c = _client(tmp_path)
    with patch("job_sentinel.sources.registry.build_enabled_sources", return_value=[src]):
        resp = c.post("/api/sources/search", json={"keywords": "python"})

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["title"] == "Python Dev"


def test_sources_search_deduplicates(tmp_path: Path) -> None:
    dup1 = _make_job("Dev", "Co", url="https://example.com/1")
    dup2 = _make_job("Dev", "Co", url="https://example.com/1")
    src = _FakeSource([dup1, dup2])

    c = _client(tmp_path)
    with patch("job_sentinel.sources.registry.build_enabled_sources", return_value=[src]):
        resp = c.post("/api/sources/search", json={})

    assert resp.status_code == 200
    assert len(resp.json()["results"]) == 1


def test_sources_search_captures_source_errors(tmp_path: Path) -> None:
    good_src = _FakeSource([_make_job("OK Job", "GoodCo")])
    bad_src = _ErrorSource()

    c = _client(tmp_path)
    with patch(
        "job_sentinel.sources.registry.build_enabled_sources",
        return_value=[good_src, bad_src],
    ):
        resp = c.post("/api/sources/search", json={})

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 1
    assert len(data["errors"]) == 1
    assert data["errors"][0]["source"] == "errorsrc"


def test_sources_search_caps_limit(tmp_path: Path) -> None:
    many = [_make_job(f"Job {i}", f"Co{i}") for i in range(200)]
    src = _FakeSource(many)

    c = _client(tmp_path)
    with patch("job_sentinel.sources.registry.build_enabled_sources", return_value=[src]):
        resp = c.post("/api/sources/search", json={"limit": 150})

    # Server-side cap is 100
    assert resp.status_code == 200
    assert len(resp.json()["results"]) <= 100


# ── POST /api/sources/company ─────────────────────────────────────────────────

_GH_PAYLOAD = {
    "jobs": [
        {
            "id": 9999,
            "title": "SRE",
            "absolute_url": "https://boards.greenhouse.io/co/jobs/9999",
            "location": {"name": "Remote"},
            "departments": [{"name": "Engineering"}],
            "updated_at": "2026-06-01",
            "content": "Keep systems running.",
        }
    ]
}


@respx.mock
def test_sources_company_greenhouse(tmp_path: Path) -> None:
    respx.get("https://boards-api.greenhouse.io/v1/boards/testco/jobs?content=true").mock(
        return_value=httpx.Response(200, json=_GH_PAYLOAD)
    )

    c = _client(tmp_path)
    resp = c.post("/api/sources/company", json={"ats": "greenhouse", "slug": "testco"})

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["title"] == "SRE"


def test_sources_company_bad_ats(tmp_path: Path) -> None:
    c = _client(tmp_path)
    resp = c.post("/api/sources/company", json={"ats": "linkedin", "slug": "corp"})
    assert resp.status_code == 400


def test_sources_company_empty_slug(tmp_path: Path) -> None:
    c = _client(tmp_path)
    resp = c.post("/api/sources/company", json={"ats": "greenhouse", "slug": ""})
    assert resp.status_code == 400
