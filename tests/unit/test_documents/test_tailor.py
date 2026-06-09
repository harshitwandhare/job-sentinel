"""Tests for the deterministic keyword tailor."""

from __future__ import annotations

from job_sentinel.documents import KeywordTailor, extract_keywords
from job_sentinel.profile import Experience, Profile, Project, SkillGroup


class TestExtractKeywords:
    def test_lowercases_and_drops_stopwords(self) -> None:
        kw = extract_keywords("We are looking for a Python and SQL developer")
        assert "python" in kw
        assert "sql" in kw
        assert "are" not in kw and "for" not in kw

    def test_keeps_techy_tokens(self) -> None:
        kw = extract_keywords("Experience with C++, C#, and Node.js")
        assert "c++" in kw
        assert "c#" in kw
        assert "node.js" in kw

    def test_empty(self) -> None:
        assert extract_keywords("") == set()


def _profile() -> Profile:
    return Profile(
        experience=[
            Experience(company="Cafe", role="Barista", bullets=["served coffee"], tags=["service"]),
            Experience(
                company="Lab",
                role="Research Assistant",
                bullets=["trained machine learning models in python"],
                tags=["python", "machine learning", "research"],
            ),
        ],
        projects=[
            Project(name="Portfolio site", description="HTML/CSS site", tags=["web"]),
            Project(
                name="ML Pipeline",
                description="data pipeline",
                bullets=["python, pandas, scikit-learn"],
                tags=["python", "ml", "data"],
            ),
        ],
        skills=[
            SkillGroup(category="Soft", skills=["Communication"]),
            SkillGroup(category="Tech", skills=["Python", "Machine Learning", "SQL"]),
        ],
    )


class TestKeywordTailor:
    def test_reorders_relevant_experience_first(self) -> None:
        jd = "Seeking a research assistant with Python and machine learning experience."
        result = KeywordTailor().tailor(_profile(), jd)
        assert result.profile.experience[0].role == "Research Assistant"
        assert result.profile.projects[0].name == "ML Pipeline"
        assert result.profile.skills[0].category == "Tech"

    def test_reports_coverage_and_missing(self) -> None:
        jd = "Python, machine learning, and Kubernetes."
        result = KeywordTailor().tailor(_profile(), jd)
        assert 0.0 < result.score <= 1.0
        assert "python" in result.matched_keywords
        # nobody has kubernetes on their profile here
        assert "kubernetes" in result.missing_keywords

    def test_empty_job_description_is_safe(self) -> None:
        result = KeywordTailor().tailor(_profile(), "")
        assert result.score == 0.0
        assert result.matched_keywords == []

    def test_does_not_mutate_original_profile(self) -> None:
        profile = _profile()
        original_first = profile.experience[0].role
        KeywordTailor().tailor(profile, "python machine learning")
        assert profile.experience[0].role == original_first  # deep-copied internally
