"""
documents/embeddings.py
────────────────────────
Text embeddings for semantic relevance ranking.

The native Ollama path (OllamaEmbedder) is preserved for backward
compatibility.  New code should go through ``build_embed_backend`` from
``providers.py`` which routes to the configured provider automatically.
"""

from __future__ import annotations

import math

from loguru import logger

from job_sentinel.documents.providers import OllamaBackend


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
    """
    Thin client for Ollama's native embedding endpoint.

    Kept for backward compatibility.  Internally wraps OllamaBackend so
    there is a single implementation of the Ollama wire protocol.
    """

    def __init__(self, base_url: str, model: str, timeout: float = 60.0) -> None:
        self._backend = OllamaBackend(base_url=base_url, model=model, timeout=timeout)

    @property
    def model(self) -> str:
        return self._backend.model

    def available(self) -> bool:
        """True if the server answers and the embedding model is pulled."""
        return self._backend.ready()

    def embed(self, texts: list[str]) -> list[list[float]] | None:
        """Embed a batch of texts. Returns ``None`` on any failure."""
        if not texts:
            return []
        try:
            return self._backend.embed(texts)
        except Exception as exc:
            logger.warning("Embedding request failed ({}); skipping semantic rank", exc)
        return None
