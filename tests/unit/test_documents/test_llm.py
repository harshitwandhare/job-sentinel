"""
Tests for the optional local-LLM tailor.

No Ollama required: a fake client exercises LLMTailor's logic, and respx mocks
the HTTP surface of OllamaClient.
"""

from __future__ import annotations

import httpx
import respx

from job_sentinel.documents.llm import LLMTailor, OllamaClient
from job_sentinel.profile import Experience, Profile

_BASE = "http://localhost:11434"


def _profile() -> Profile:
    return Profile(
        experience=[
            Experience(company="Lab", role="RA", bullets=["did research", "wrote code"]),
        ]
    )


class _FakeClient:
    def __init__(self, *, up: bool, model: bool, reply: object) -> None:
        self._up, self._model, self._reply = up, model, reply

    def available(self) -> bool:
        return self._up

    def has_model(self) -> bool:
        return self._model

    def ready(self) -> bool:
        return self._model

    def chat_json(self, system: str, user: str) -> object:
        if isinstance(self._reply, Exception):
            raise self._reply
        return self._reply


class TestLLMTailorFallback:
    def test_unavailable_server_keeps_original_bullets(self) -> None:
        client = _FakeClient(up=False, model=True, reply={"bullets": ["x", "y"]})
        result = LLMTailor(client).tailor(_profile(), "python research")
        assert result.profile.experience[0].bullets == ["did research", "wrote code"]

    def test_model_missing_keeps_original(self) -> None:
        client = _FakeClient(up=True, model=False, reply={"bullets": ["x", "y"]})
        result = LLMTailor(client).tailor(_profile(), "python research")
        assert result.profile.experience[0].bullets == ["did research", "wrote code"]

    def test_valid_reply_rephrases(self) -> None:
        client = _FakeClient(
            up=True, model=True, reply={"bullets": ["Led research", "Built tools"]}
        )
        result = LLMTailor(client).tailor(_profile(), "research engineer")
        assert result.profile.experience[0].bullets == ["Led research", "Built tools"]

    def test_wrong_length_reply_keeps_original(self) -> None:
        client = _FakeClient(up=True, model=True, reply={"bullets": ["only one"]})
        result = LLMTailor(client).tailor(_profile(), "research")
        assert result.profile.experience[0].bullets == ["did research", "wrote code"]

    def test_chat_error_keeps_original(self) -> None:
        client = _FakeClient(up=True, model=True, reply=RuntimeError("boom"))
        result = LLMTailor(client).tailor(_profile(), "research")
        assert result.profile.experience[0].bullets == ["did research", "wrote code"]

    def test_no_job_description_skips_llm(self) -> None:
        client = _FakeClient(up=True, model=True, reply={"bullets": ["x", "y"]})
        result = LLMTailor(client).tailor(_profile(), "")
        assert result.profile.experience[0].bullets == ["did research", "wrote code"]


class TestOllamaClient:
    @respx.mock
    def test_available_true(self) -> None:
        respx.get(f"{_BASE}/api/tags").mock(return_value=httpx.Response(200, json={"models": []}))
        assert OllamaClient(_BASE, "llama3.1:8b").available() is True

    @respx.mock
    def test_available_false_on_error(self) -> None:
        respx.get(f"{_BASE}/api/tags").mock(side_effect=httpx.ConnectError("down"))
        assert OllamaClient(_BASE, "llama3.1:8b").available() is False

    @respx.mock
    def test_has_model_matches_base_tag(self) -> None:
        respx.get(f"{_BASE}/api/tags").mock(
            return_value=httpx.Response(200, json={"models": [{"name": "llama3.1:8b"}]})
        )
        assert OllamaClient(_BASE, "llama3.1").has_model() is True

    @respx.mock
    def test_chat_json_parses_content(self) -> None:
        respx.post(f"{_BASE}/api/chat").mock(
            return_value=httpx.Response(
                200, json={"message": {"content": '{"bullets": ["a", "b"]}'}}
            )
        )
        out = OllamaClient(_BASE, "llama3.1:8b").chat_json("sys", "user")
        assert out == {"bullets": ["a", "b"]}
