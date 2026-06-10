"""Tests for semantic (embedding-based) tailoring with a fake embedder."""

from __future__ import annotations

from job_sentinel.documents.semantic import SemanticTailor
from job_sentinel.profile import Experience, Profile

# A job description that shares NO keywords with either role, so the keyword
# tailor leaves the original order — isolating the semantic reordering.
_JD = "deep neural network research"


def _profile() -> Profile:
    return Profile(
        experience=[
            Experience(company="Cafe", role="Barista", bullets=["served drinks"]),
            Experience(company="Lab", role="Engineer", bullets=["trained models"]),
        ]
    )


class _FakeEmbedder:
    def __init__(self, *, up: bool, vectors: list[list[float]] | None) -> None:
        self._up = up
        self._vectors = vectors

    def available(self) -> bool:
        return self._up

    def embed(self, texts: list[str]) -> list[list[float]] | None:
        return self._vectors


def test_reorders_by_similarity() -> None:
    # texts = [jd, Barista, Engineer]; jd vector matches the Engineer vector.
    embedder = _FakeEmbedder(up=True, vectors=[[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]])
    result = SemanticTailor(embedder).tailor(_profile(), _JD)  # type: ignore[arg-type]
    assert result.profile.experience[0].role == "Engineer"


def test_unavailable_embedder_keeps_keyword_order() -> None:
    embedder = _FakeEmbedder(up=False, vectors=None)
    result = SemanticTailor(embedder).tailor(_profile(), _JD)  # type: ignore[arg-type]
    assert result.profile.experience[0].role == "Barista"  # original order preserved


def test_embed_failure_falls_back() -> None:
    embedder = _FakeEmbedder(up=True, vectors=None)  # embed() returns None
    result = SemanticTailor(embedder).tailor(_profile(), _JD)  # type: ignore[arg-type]
    assert result.profile.experience[0].role == "Barista"


def test_empty_jd_is_noop() -> None:
    embedder = _FakeEmbedder(up=True, vectors=[[1.0]])
    result = SemanticTailor(embedder).tailor(_profile(), "")  # type: ignore[arg-type]
    assert result.profile.experience[0].role == "Barista"
