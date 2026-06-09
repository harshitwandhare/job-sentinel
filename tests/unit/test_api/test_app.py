"""Tests for the local HTTP API (FastAPI TestClient — no server needed)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from job_sentinel.api.app import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def test_health() -> None:
    resp = _client().get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_profile_endpoint_shape() -> None:
    resp = _client().get("/api/profile")
    assert resp.status_code == 200
    body = resp.json()
    # Always a valid profile shape, even when empty.
    assert "basics" in body
    assert "experience" in body and isinstance(body["experience"], list)


def test_profile_summary_shape() -> None:
    resp = _client().get("/api/profile/summary")
    assert resp.status_code == 200
    body = resp.json()
    for key in ("education", "experience", "projects", "skills"):
        assert key in body and isinstance(body[key], int)


def test_jobs_returns_list() -> None:
    resp = _client().get("/api/jobs?limit=5")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_tailor_endpoint_reports_coverage() -> None:
    resp = _client().post("/api/resume/tailor", json={"job_description": "python and react"})
    assert resp.status_code == 200
    body = resp.json()
    assert 0.0 <= body["score"] <= 1.0
    assert "matched_keywords" in body and "missing_keywords" in body
    assert "profile" in body


def test_tailor_requires_non_empty_description() -> None:
    resp = _client().post("/api/resume/tailor", json={"job_description": ""})
    assert resp.status_code == 422  # pydantic min_length validation
