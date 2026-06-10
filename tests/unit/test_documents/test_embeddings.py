"""Tests for local embeddings (cosine + Ollama embedder, HTTP mocked)."""

from __future__ import annotations

import httpx
import respx

from job_sentinel.documents.embeddings import OllamaEmbedder, cosine_similarity

_BASE = "http://localhost:11434"


class TestCosine:
    def test_identical_is_one(self) -> None:
        assert cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 1.0

    def test_orthogonal_is_zero(self) -> None:
        assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0

    def test_empty_or_mismatched_is_zero(self) -> None:
        assert cosine_similarity([], [1.0]) == 0.0
        assert cosine_similarity([1.0, 2.0], [1.0]) == 0.0

    def test_zero_norm_is_zero(self) -> None:
        assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


class TestEmbedder:
    @respx.mock
    def test_available_true_when_model_present(self) -> None:
        respx.get(f"{_BASE}/api/tags").mock(
            return_value=httpx.Response(200, json={"models": [{"name": "nomic-embed-text"}]})
        )
        assert OllamaEmbedder(_BASE, "nomic-embed-text").available() is True

    @respx.mock
    def test_available_false_when_missing(self) -> None:
        respx.get(f"{_BASE}/api/tags").mock(return_value=httpx.Response(200, json={"models": []}))
        assert OllamaEmbedder(_BASE, "nomic-embed-text").available() is False

    @respx.mock
    def test_embed_returns_vectors(self) -> None:
        respx.post(f"{_BASE}/api/embed").mock(
            return_value=httpx.Response(200, json={"embeddings": [[0.1, 0.2], [0.3, 0.4]]})
        )
        out = OllamaEmbedder(_BASE, "m").embed(["a", "b"])
        assert out == [[0.1, 0.2], [0.3, 0.4]]

    @respx.mock
    def test_embed_none_on_shape_mismatch(self) -> None:
        respx.post(f"{_BASE}/api/embed").mock(
            return_value=httpx.Response(200, json={"embeddings": [[0.1]]})
        )
        assert OllamaEmbedder(_BASE, "m").embed(["a", "b"]) is None

    def test_embed_empty_input(self) -> None:
        assert OllamaEmbedder(_BASE, "m").embed([]) == []
