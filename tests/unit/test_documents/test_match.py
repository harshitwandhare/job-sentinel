"""
Tests for documents/match.py.

All LLM and embedder backends are monkeypatched so the test suite never
requires Ollama or any live network connection.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from job_sentinel.documents.match import (
    MatchResult,
    _deterministic_rationale,
    _verdict,
    match_profile_to_job,
)
from job_sentinel.profile.models import Experience, Profile, Project, SkillGroup

# ── helpers ──────────────────────────────────────────────────────────────────


def _profile() -> Profile:
    return Profile(
        experience=[
            Experience(
                company="Acme",
                role="Software Engineer",
                bullets=["built python services", "wrote sql queries"],
                tags=["python", "sql"],
            )
        ],
        projects=[
            Project(
                name="ML Toolkit",
                description="machine learning utilities",
                bullets=["scikit-learn, pandas"],
                tags=["python", "ml"],
            )
        ],
        skills=[
            SkillGroup(category="Languages", skills=["Python", "SQL"]),
            SkillGroup(category="Tools", skills=["Docker", "Git"]),
        ],
    )


def _empty_profile() -> Profile:
    return Profile()


class _FakeEmbedder:
    """Embedder that returns fixed vectors to exercise the blending path."""

    def __init__(self, *, up: bool, vectors: list[list[float]] | None = None) -> None:
        self._up = up
        self._vectors = vectors or [[1.0, 0.0], [0.9, 0.1]]

    def available(self) -> bool:
        return self._up

    def ready(self) -> bool:
        return self._up

    def embed(self, texts: list[str]) -> list[list[float]] | None:
        if not self._up:
            return None
        # Return one vector per text (reuse pool in round-robin).
        pool = self._vectors
        return [pool[i % len(pool)] for i in range(len(texts))]


class _FakeChatBackend:
    """Chat backend that returns a canned JSON response."""

    def __init__(self, *, up: bool, response: dict[str, Any] | None = None) -> None:
        self._up = up
        self._response = response or {
            "rationale": "This is a test rationale.",
            "strengths": ["python skill"],
            "gaps": ["missing kubernetes"],
        }

    def available(self) -> bool:
        return self._up

    def ready(self) -> bool:
        return self._up

    def chat_json(self, system: str, user: str) -> dict[str, Any]:
        return self._response


# ── verdict thresholds ────────────────────────────────────────────────────────


class TestVerdict:
    def test_strong(self) -> None:
        assert _verdict(0.70) == "strong"
        assert _verdict(1.0) == "strong"

    def test_moderate(self) -> None:
        assert _verdict(0.45) == "moderate"
        assert _verdict(0.69) == "moderate"

    def test_weak(self) -> None:
        assert _verdict(0.0) == "weak"
        assert _verdict(0.44) == "weak"


# ── deterministic fallback ────────────────────────────────────────────────────


class TestDeterministicRationale:
    def test_strong_verdict_wording(self) -> None:
        rat, strengths, gaps = _deterministic_rationale(
            0.8, None, ["python", "sql"], ["kubernetes"], "strong"
        )
        assert "strong" in rat
        assert any("python" in s for s in strengths)
        assert any("kubernetes" in g for g in gaps)

    def test_semantic_pct_in_rationale(self) -> None:
        rat, _, _ = _deterministic_rationale(0.5, 0.6, ["python"], [], "moderate")
        assert "60%" in rat

    def test_empty_matched_and_missing(self) -> None:
        rat, strengths, gaps = _deterministic_rationale(0.0, None, [], [], "weak")
        assert isinstance(rat, str)
        assert strengths == []
        assert gaps == []


# ── blend math ────────────────────────────────────────────────────────────────


class TestBlendMath:
    def _run_no_ai(
        self,
        fake_embedder: _FakeEmbedder | None,
        profile: Profile,
        jd: str,
    ) -> MatchResult:
        """Run match_profile_to_job with backends patched."""
        with (
            patch(
                "job_sentinel.documents.match.build_embed_backend",
                return_value=fake_embedder,
            ),
            patch(
                "job_sentinel.documents.match.LLMSettings",
            ),
        ):
            return match_profile_to_job(profile, jd, use_ai=False)

    def test_coverage_only_when_no_embedder(self) -> None:
        embedder = _FakeEmbedder(up=False)
        result = self._run_no_ai(embedder, _profile(), "python sql developer")
        assert result.semantic is None
        assert result.score == pytest.approx(result.coverage)

    def test_blend_50_50_when_embedder_available(self) -> None:
        # Vectors designed so cosine = 1.0 (identical unit vectors).
        embedder = _FakeEmbedder(up=True, vectors=[[1.0, 0.0], [1.0, 0.0]])

        with (
            patch("job_sentinel.documents.match.build_embed_backend", return_value=embedder),
            patch("job_sentinel.documents.match.LLMSettings"),
        ):
            result = match_profile_to_job(_profile(), "python sql developer", use_ai=False)

        assert result.semantic is not None
        expected = 0.5 * result.coverage + 0.5 * result.semantic
        assert result.score == pytest.approx(expected, abs=1e-9)

    def test_semantic_clamped_to_zero_one(self) -> None:
        # cosine_similarity returns negative for anti-parallel vectors;
        # our clamp must bring it to 0.
        embedder = _FakeEmbedder(up=True, vectors=[[1.0, 0.0], [-1.0, 0.0]])
        with (
            patch("job_sentinel.documents.match.build_embed_backend", return_value=embedder),
            patch("job_sentinel.documents.match.LLMSettings"),
        ):
            result = match_profile_to_job(_profile(), "python", use_ai=False)
        if result.semantic is not None:
            assert 0.0 <= result.semantic <= 1.0
        assert 0.0 <= result.score <= 1.0


# ── no-LLM deterministic fallback ─────────────────────────────────────────────


class TestDeterministicFallback:
    def test_use_ai_false_no_backend_call(self) -> None:
        with (
            patch("job_sentinel.documents.match.build_embed_backend") as mock_embed,
            patch("job_sentinel.documents.match.LLMSettings"),
        ):
            mock_embed.return_value = _FakeEmbedder(up=False)
            result = match_profile_to_job(_profile(), "python sql", use_ai=False)

        assert isinstance(result.rationale, str) and result.rationale
        assert isinstance(result.strengths, list)
        assert isinstance(result.gaps, list)

    def test_strengths_contain_matched_keywords(self) -> None:
        with (
            patch("job_sentinel.documents.match.build_embed_backend") as mock_embed,
            patch("job_sentinel.documents.match.LLMSettings"),
        ):
            mock_embed.return_value = _FakeEmbedder(up=False)
            result = match_profile_to_job(_profile(), "python sql docker", use_ai=False)

        # At least one matched keyword should appear in strengths
        all_strength_text = " ".join(result.strengths)
        assert any(kw in all_strength_text for kw in result.matched_keywords)

    def test_gaps_contain_missing_keywords(self) -> None:
        with (
            patch("job_sentinel.documents.match.build_embed_backend") as mock_embed,
            patch("job_sentinel.documents.match.LLMSettings"),
        ):
            mock_embed.return_value = _FakeEmbedder(up=False)
            result = match_profile_to_job(_profile(), "python kubernetes rust", use_ai=False)

        all_gap_text = " ".join(result.gaps)
        # kubernetes/rust should be in missing and reflected in gaps
        assert "kubernetes" in all_gap_text or "rust" in all_gap_text


# ── AI rationale ──────────────────────────────────────────────────────────────


class TestAIRationale:
    def _run_with_backends(
        self,
        fake_embedder: _FakeEmbedder,
        fake_chat: _FakeChatBackend,
        jd: str = "python sql developer",
    ) -> MatchResult:
        with (
            patch("job_sentinel.documents.match.build_embed_backend", return_value=fake_embedder),
            patch("job_sentinel.documents.match.build_chat_backend", return_value=fake_chat),
            patch("job_sentinel.documents.match.LLMSettings"),
        ):
            return match_profile_to_job(_profile(), jd, use_ai=True)

    def test_ai_rationale_used_when_ready(self) -> None:
        result = self._run_with_backends(
            _FakeEmbedder(up=False),
            _FakeChatBackend(up=True),
        )
        assert result.rationale == "This is a test rationale."
        assert "python skill" in result.strengths
        assert "missing kubernetes" in result.gaps

    def test_bad_json_shape_falls_back(self) -> None:
        bad_chat = _FakeChatBackend(up=True, response={"wrong": "keys"})
        result = self._run_with_backends(_FakeEmbedder(up=False), bad_chat)
        # Should not be the canned response — deterministic fallback fires
        assert result.rationale != "This is a test rationale."
        assert isinstance(result.rationale, str) and result.rationale

    def test_chat_unavailable_falls_back(self) -> None:
        result = self._run_with_backends(
            _FakeEmbedder(up=False),
            _FakeChatBackend(up=False),
        )
        assert isinstance(result.rationale, str) and result.rationale


# ── empty JD handling ─────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_jd_returns_valid_result(self) -> None:
        with (
            patch("job_sentinel.documents.match.build_embed_backend") as mock_embed,
            patch("job_sentinel.documents.match.LLMSettings"),
        ):
            mock_embed.return_value = _FakeEmbedder(up=False)
            result = match_profile_to_job(_profile(), "", use_ai=False)

        assert result.score == 0.0
        assert result.verdict == "weak"
        assert result.semantic is None

    def test_result_is_valid_pydantic_model(self) -> None:
        with (
            patch("job_sentinel.documents.match.build_embed_backend") as mock_embed,
            patch("job_sentinel.documents.match.LLMSettings"),
        ):
            mock_embed.return_value = _FakeEmbedder(up=False)
            result = match_profile_to_job(_profile(), "python", use_ai=False)

        # Re-validate to confirm the model invariants hold
        validated = MatchResult.model_validate(result.model_dump())
        assert 0.0 <= validated.score <= 1.0
        assert validated.verdict in ("strong", "moderate", "weak")

    def test_score_pct_rounds_correctly(self) -> None:
        with (
            patch("job_sentinel.documents.match.build_embed_backend") as mock_embed,
            patch("job_sentinel.documents.match.LLMSettings"),
        ):
            mock_embed.return_value = _FakeEmbedder(up=False)
            result = match_profile_to_job(_profile(), "python sql", use_ai=False)

        assert isinstance(result.score_pct, int)
        assert 0 <= result.score_pct <= 100

    def test_importable_without_live_backends(self) -> None:
        """Module-level import must never block on network I/O."""
        import importlib

        import job_sentinel.documents.match as _mod

        assert hasattr(_mod, "match_profile_to_job")
        assert hasattr(_mod, "MatchResult")
        importlib.reload(_mod)  # second import is also clean
