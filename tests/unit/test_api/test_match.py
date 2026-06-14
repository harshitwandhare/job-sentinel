"""
Tests for POST /api/match.

All LLM and embedder backends are mocked so these tests require no Ollama
instance and run offline.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from job_sentinel.api.app import create_app
from job_sentinel.core.models import JobPosting
from job_sentinel.db.repository import JobRepository
from job_sentinel.profile.models import (
    Basics,
    Experience,
    Profile,
    SkillGroup,
)

# ── fixtures ──────────────────────────────────────────────────────────────────


def _client(tmp_path, profile: Profile | None = None) -> TestClient:
    from job_sentinel.profile import save_profile

    profile_path = tmp_path / "profile.yaml"
    db_path = tmp_path / "j.db"
    if profile is not None:
        save_profile(profile, profile_path)
    return TestClient(create_app(profile_path=profile_path, db_path=db_path))


def _profile_with_skills() -> Profile:
    return Profile(
        basics=Basics(name="Ada Lovelace", summary="Software engineer"),
        experience=[
            Experience(
                company="Acme",
                role="Software Engineer",
                bullets=["developed python microservices"],
                tags=["python"],
            )
        ],
        skills=[SkillGroup(category="Languages", skills=["Python", "SQL"])],
    )


def _seed_job(tmp_path, job: JobPosting) -> None:
    repo = JobRepository(tmp_path / "j.db")
    repo.save_job(job)
    repo.close()


def _no_backends() -> Any:
    """Context manager stack that disables all LLM backends."""
    from contextlib import ExitStack

    class _FakeEmbed:
        def available(self) -> bool:
            return False

        def ready(self) -> bool:
            return False

        def embed(self, texts: list[str]) -> None:
            return None

    class _FakeChat:
        def available(self) -> bool:
            return False

        def ready(self) -> bool:
            return False

    stack = ExitStack()
    stack.enter_context(
        patch("job_sentinel.documents.match.build_embed_backend", return_value=_FakeEmbed())
    )
    stack.enter_context(
        patch("job_sentinel.documents.match.build_chat_backend", return_value=_FakeChat())
    )
    stack.enter_context(patch("job_sentinel.documents.match.LLMSettings"))
    return stack


# ── basic success paths ───────────────────────────────────────────────────────


class TestMatchWithJobDescription:
    def test_returns_match_result_shape(self, tmp_path) -> None:
        client = _client(tmp_path, _profile_with_skills())
        with _no_backends():
            resp = client.post("/api/match", json={"job_description": "python developer sql"})
        assert resp.status_code == 200
        body = resp.json()
        assert "score" in body
        assert "coverage" in body
        assert "verdict" in body
        assert "matched_keywords" in body
        assert "missing_keywords" in body
        assert "rationale" in body
        assert "strengths" in body
        assert "gaps" in body

    def test_score_between_0_and_1(self, tmp_path) -> None:
        client = _client(tmp_path, _profile_with_skills())
        with _no_backends():
            resp = client.post("/api/match", json={"job_description": "python developer"})
        assert resp.status_code == 200
        body = resp.json()
        assert 0.0 <= body["score"] <= 1.0
        assert 0.0 <= body["coverage"] <= 1.0

    def test_verdict_is_valid(self, tmp_path) -> None:
        client = _client(tmp_path, _profile_with_skills())
        with _no_backends():
            resp = client.post("/api/match", json={"job_description": "python developer"})
        assert resp.json()["verdict"] in ("strong", "moderate", "weak")

    def test_ai_false_still_works(self, tmp_path) -> None:
        client = _client(tmp_path, _profile_with_skills())
        with _no_backends():
            resp = client.post(
                "/api/match", json={"job_description": "python developer", "ai": False}
            )
        assert resp.status_code == 200
        assert resp.json()["rationale"]


class TestMatchWithPostingId:
    def test_match_via_posting_id(self, tmp_path) -> None:
        job = JobPosting(
            posting_id="job-42",
            title="Python Developer",
            employer="TechCorp",
            description_snippet="Looking for python sql skills",
        )
        _seed_job(tmp_path, job)
        client = _client(tmp_path, _profile_with_skills())
        with _no_backends():
            resp = client.post("/api/match", json={"posting_id": "job-42"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["score"] >= 0.0
        assert body["verdict"] in ("strong", "moderate", "weak")

    def test_missing_posting_id_returns_404(self, tmp_path) -> None:
        _seed_job(tmp_path, JobPosting(posting_id="exists", title="dev", employer="co"))
        client = _client(tmp_path, _profile_with_skills())
        with _no_backends():
            resp = client.post("/api/match", json={"posting_id": "not-there"})
        assert resp.status_code == 404

    def test_posting_id_uses_description_if_available(self, tmp_path) -> None:
        """Jobs with raw_data detail descriptions get richer text."""
        job = JobPosting(
            posting_id="job-rich",
            title="ML Engineer",
            employer="AI Corp",
            raw_data={"detail": {"description": "machine learning python scikit"}},
        )
        _seed_job(tmp_path, job)
        client = _client(tmp_path, _profile_with_skills())
        with _no_backends():
            resp = client.post("/api/match", json={"posting_id": "job-rich"})
        assert resp.status_code == 200
        # "python" is in both description and profile → should appear in matched
        body = resp.json()
        assert "python" in body["matched_keywords"]


# ── 400 error cases ───────────────────────────────────────────────────────────


class TestMatchBadRequests:
    def test_no_jd_or_posting_id_returns_400(self, tmp_path) -> None:
        client = _client(tmp_path, _profile_with_skills())
        with _no_backends():
            resp = client.post("/api/match", json={})
        assert resp.status_code == 400

    def test_empty_jd_string_returns_400(self, tmp_path) -> None:
        client = _client(tmp_path, _profile_with_skills())
        with _no_backends():
            resp = client.post("/api/match", json={"job_description": ""})
        assert resp.status_code == 400

    def test_whitespace_only_jd_returns_400(self, tmp_path) -> None:
        client = _client(tmp_path, _profile_with_skills())
        with _no_backends():
            resp = client.post("/api/match", json={"job_description": "   "})
        assert resp.status_code == 400

    def test_empty_profile_returns_400(self, tmp_path) -> None:
        # profile_path does not exist → Profile() empty
        client = _client(tmp_path, profile=None)
        with _no_backends():
            resp = client.post("/api/match", json={"job_description": "python developer"})
        assert resp.status_code == 400

    def test_no_db_with_posting_id_returns_404(self, tmp_path) -> None:
        """If db_path doesn't exist and posting_id is given, return 404."""
        profile_path = tmp_path / "profile.yaml"
        from job_sentinel.profile import save_profile

        save_profile(_profile_with_skills(), profile_path)
        # Use a non-existent db path
        client = TestClient(create_app(profile_path=profile_path, db_path=tmp_path / "noexist.db"))
        with _no_backends():
            resp = client.post("/api/match", json={"posting_id": "anything"})
        assert resp.status_code == 404


# ── semantic None path (embed unavailable) ────────────────────────────────────


class TestSemanticNone:
    def test_semantic_is_none_when_embedder_down(self, tmp_path) -> None:
        client = _client(tmp_path, _profile_with_skills())
        with _no_backends():
            resp = client.post("/api/match", json={"job_description": "python developer"})
        body = resp.json()
        assert body["semantic"] is None
        # score must equal coverage when semantic is None
        assert body["score"] == pytest.approx(body["coverage"])
