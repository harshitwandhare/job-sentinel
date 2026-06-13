"""
documents/semantic.py
───────────────────────
Semantic relevance ranking for tailoring.

Where :class:`~job_sentinel.documents.tailor.KeywordTailor` orders content by
literal keyword overlap, :class:`SemanticTailor` orders it by *meaning* — cosine
similarity between local embeddings of each profile item and the job description.
So "built ML models" ranks for a posting that says "machine learning" even with no
shared token.

It implements the same :class:`Tailor` protocol and composes over the keyword
tailor: keyword tailoring still computes the ATS coverage score (ATS parsers are
literal), while embeddings decide the *ordering*. If the embedder isn't available,
it transparently returns the keyword tailor's result.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from job_sentinel.documents.embeddings import cosine_similarity
from job_sentinel.documents.tailor import KeywordTailor, TailorResult

if TYPE_CHECKING:
    from job_sentinel.documents.embeddings import OllamaEmbedder
    from job_sentinel.documents.providers import EmbedBackend
    from job_sentinel.documents.tailor import Tailor
    from job_sentinel.profile.models import Experience, Profile, Project


def _experience_text(x: Experience) -> str:
    return " ".join([x.role, x.company, *x.bullets, *x.tags])


def _project_text(p: Project) -> str:
    return " ".join([p.name, p.description, *p.bullets, *p.tags])


class SemanticTailor:
    """Tailor that orders content by embedding similarity, atop the keyword tailor."""

    def __init__(self, embedder: OllamaEmbedder | EmbedBackend, base: Tailor | None = None) -> None:
        self._embedder = embedder
        self._base: Tailor = base or KeywordTailor()

    def tailor(self, profile: Profile, job_description: str) -> TailorResult:
        result = self._base.tailor(profile, job_description)
        if not job_description or not self._embedder.available():
            return result

        tailored = result.profile
        exp_texts = [_experience_text(x) for x in tailored.experience]
        proj_texts = [_project_text(p) for p in tailored.projects]

        vectors = self._embedder.embed([job_description, *exp_texts, *proj_texts])
        if vectors is None:
            return result  # embedder failed mid-flight — keep keyword ordering

        jd_vec = vectors[0]
        rest = vectors[1:]
        exp_vecs = rest[: len(exp_texts)]
        proj_vecs = rest[len(exp_texts) :]

        tailored.experience = [
            x
            for _, x in sorted(
                zip(
                    (cosine_similarity(jd_vec, v) for v in exp_vecs),
                    tailored.experience,
                    strict=False,
                ),
                key=lambda t: t[0],
                reverse=True,
            )
        ]
        tailored.projects = [
            p
            for _, p in sorted(
                zip(
                    (cosine_similarity(jd_vec, v) for v in proj_vecs),
                    tailored.projects,
                    strict=False,
                ),
                key=lambda t: t[0],
                reverse=True,
            )
        ]

        return TailorResult(
            profile=tailored,
            score=result.score,
            matched_keywords=result.matched_keywords,
            missing_keywords=result.missing_keywords,
        )
