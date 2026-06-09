"""Tests for cover-letter composition (deterministic + LLM fallback)."""

from __future__ import annotations

from job_sentinel.documents.coverletter import compose_cover_letter, cover_letter_paragraphs
from job_sentinel.profile import Basics, Experience, Profile, SkillGroup


def _profile() -> Profile:
    return Profile(
        basics=Basics(name="Ada Lovelace", summary="Engineer who ships."),
        experience=[
            Experience(company="Analytical", role="Engineer", bullets=["Built the engine"]),
        ],
        skills=[SkillGroup(category="Tech", skills=["Python", "Math"])],
    )


class TestComposeCoverLetter:
    def test_includes_role_company_and_facts(self) -> None:
        paras = compose_cover_letter(
            _profile(), role="Research Assistant", company="UTD", job_description=""
        )
        text = "\n".join(paras)
        assert "Research Assistant" in text
        assert "UTD" in text
        assert "Engineer at Analytical" in text
        assert "Python" in text
        assert paras[-1].startswith("I would welcome")

    def test_generic_phrasing_without_role(self) -> None:
        paras = compose_cover_letter(_profile())
        assert "the role you've advertised" in paras[0]
        assert "your team" in paras[0]

    def test_handles_empty_profile(self) -> None:
        paras = compose_cover_letter(Profile())
        assert len(paras) >= 2  # intro + closing always present


class _FakeClient:
    def __init__(self, *, up: bool, model: bool, reply: object) -> None:
        self._up, self._model, self._reply = up, model, reply

    def available(self) -> bool:
        return self._up

    def has_model(self) -> bool:
        return self._model

    def chat_json(self, system: str, user: str) -> object:
        if isinstance(self._reply, Exception):
            raise self._reply
        return self._reply


class TestLLMPolish:
    def test_no_client_returns_draft(self) -> None:
        out = cover_letter_paragraphs(_profile(), client=None)
        assert out == compose_cover_letter(_profile())

    def test_unavailable_client_falls_back(self) -> None:
        client = _FakeClient(up=False, model=True, reply={"paragraphs": ["x"]})
        assert cover_letter_paragraphs(_profile(), client=client) == compose_cover_letter(
            _profile()
        )

    def test_valid_reply_used(self) -> None:
        client = _FakeClient(up=True, model=True, reply={"paragraphs": ["Polished one.", "Two."]})
        assert cover_letter_paragraphs(_profile(), client=client) == ["Polished one.", "Two."]

    def test_malformed_reply_falls_back(self) -> None:
        client = _FakeClient(up=True, model=True, reply={"paragraphs": []})
        assert cover_letter_paragraphs(_profile(), client=client) == compose_cover_letter(
            _profile()
        )

    def test_error_falls_back(self) -> None:
        client = _FakeClient(up=True, model=True, reply=RuntimeError("boom"))
        assert cover_letter_paragraphs(_profile(), client=client) == compose_cover_letter(
            _profile()
        )
