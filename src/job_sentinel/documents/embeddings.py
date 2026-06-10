"""
documents/embeddings.py
────────────────────────
Local text embeddings via Ollama, for semantic relevance ranking.

Same philosophy as the rest of the AI layer: a *local* model (e.g.
``nomic-embed-text``), no API key, nothing leaves the machine, and a clean
``available()`` gate so callers degrade gracefully when it isn't installed.
"""

from __future__ import annotations

import math

import httpx
from loguru import logger


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity of two vectors; 0.0 if either is empty or zero-norm."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


class OllamaEmbedder:
    """Thin client for Ollama's embedding endpoint."""

    def __init__(self, base_url: str, model: str, timeout: float = 60.0) -> None:
        self._base = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    @property
    def model(self) -> str:
        return self._model

    def available(self) -> bool:
        """True if the server answers and the embedding model is pulled."""
        try:
            resp = httpx.get(f"{self._base}/api/tags", timeout=3.0)
            resp.raise_for_status()
            names = [m.get("name", "") for m in resp.json().get("models", [])]
        except Exception:
            return False
        base = self._model.split(":")[0]
        return any(n == self._model or n.split(":")[0] == base for n in names)

    def embed(self, texts: list[str]) -> list[list[float]] | None:
        """Embed a batch of texts. Returns ``None`` on any failure."""
        if not texts:
            return []
        try:
            resp = httpx.post(
                f"{self._base}/api/embed",
                json={"model": self._model, "input": texts},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            embeddings = resp.json().get("embeddings")
            if isinstance(embeddings, list) and len(embeddings) == len(texts):
                return embeddings
            logger.warning("Embedder returned an unexpected shape — skipping semantic rank")
        except Exception as exc:
            logger.warning("Embedding request failed ({}); skipping semantic rank", exc)
        return None
