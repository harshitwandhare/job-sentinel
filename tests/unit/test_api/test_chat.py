"""Tests for the Sentinel chat assistant — rules routing, fallback, endpoint."""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from fastapi.testclient import TestClient

from job_sentinel.api.app import create_app
from job_sentinel.api.chat import ChatMessage, answer
from job_sentinel.core.models import JobPosting
from job_sentinel.db.repository import JobRepository
from job_sentinel.profile import Basics, Experience, Profile, SkillGroup, save_profile

if TYPE_CHECKING:
    from pathlib import Path


def _user(text: str) -> list[ChatMessage]:
    return [ChatMessage(role="user", content=text)]


def _seed(tmp_path: Path) -> tuple[Path, Path]:
    db = tmp_path / "j.db"
    repo = JobRepository(db)
    soon = (date.today() + timedelta(days=3)).strftime("%m/%d/%Y")
    repo.save_job(
        JobPosting(posting_id="a", title="Library Assistant", employer="UTD", deadline=soon)
    )
    repo.save_job(JobPosting(posting_id="b", title="Barista", deadline="Apply Immediately"))
    repo.close()

    prof = tmp_path / "p.yaml"
    save_profile(
        Profile(
            basics=Basics(name="Ada Lovelace", headline="Engineer"),
            experience=[Experience(company="Analytical", role="Engineer", bullets=["built it"])],
            skills=[SkillGroup(category="Tech", skills=["Python", "SQL"])],
        ),
        prof,
    )
    return prof, db


class TestRules:
    def test_deadlines_lists_closing_posting(self, tmp_path: Path) -> None:
        prof, db = _seed(tmp_path)
        out = answer(_user("what's closing soon?"), profile_path=prof, db_path=db)
        assert out.source == "rules"
        assert "Library Assistant" in out.reply
        assert "Barista" not in out.reply  # unparseable deadline isn't flagged

    def test_recent_jobs(self, tmp_path: Path) -> None:
        prof, db = _seed(tmp_path)
        out = answer(_user("show my recent jobs"), profile_path=prof, db_path=db)
        assert "Library Assistant" in out.reply and "Barista" in out.reply

    def test_stats(self, tmp_path: Path) -> None:
        prof, db = _seed(tmp_path)
        out = answer(_user("how many have I applied to?"), profile_path=prof, db_path=db)
        assert "2" in out.reply and out.source == "rules"

    def test_profile_summary(self, tmp_path: Path) -> None:
        prof, db = _seed(tmp_path)
        out = answer(_user("summarize my profile"), profile_path=prof, db_path=db)
        assert "Ada Lovelace" in out.reply and "Engineer at Analytical" in out.reply

    def test_long_message_is_treated_as_jd(self, tmp_path: Path) -> None:
        prof, db = _seed(tmp_path)
        jd = "We need a Python engineer with SQL experience. " * 12  # > 400 chars
        out = answer(_user(jd), profile_path=prof, db_path=db)
        assert "coverage" in out.reply.lower()
        assert "%" in out.reply

    def test_help(self, tmp_path: Path) -> None:
        prof, db = _seed(tmp_path)
        out = answer(_user("what can you do?"), profile_path=prof, db_path=db)
        assert "Deadlines" in out.reply

    def test_empty_db_answers_gracefully(self, tmp_path: Path) -> None:
        out = answer(
            _user("any deadlines?"), profile_path=tmp_path / "p.yaml", db_path=tmp_path / "j.db"
        )
        assert "scrape" in out.reply.lower()


class _FakeLLM:
    def __init__(self, reply: str | Exception) -> None:
        self._reply = reply
        self.seen_system = ""

    def chat(self, system: str, messages: list[dict[str, str]]) -> str:
        self.seen_system = system
        if isinstance(self._reply, Exception):
            raise self._reply
        return self._reply


class TestLLMBranch:
    def test_open_question_without_model_falls_back_to_help(self, tmp_path: Path) -> None:
        prof, db = _seed(tmp_path)
        out = answer(
            _user("should I do a masters thesis?"),
            profile_path=prof,
            db_path=db,
            client_factory=lambda: None,
        )
        assert out.source == "rules"
        assert "doctor" in out.reply

    def test_open_question_uses_llm_with_context(self, tmp_path: Path) -> None:
        prof, db = _seed(tmp_path)
        fake = _FakeLLM("Networking beats cold applies.")
        out = answer(
            _user("any tips for on-campus jobs?"),
            profile_path=prof,
            db_path=db,
            client_factory=lambda: fake,  # type: ignore[arg-type, return-value]
        )
        assert out.source == "llm"
        assert out.reply == "Networking beats cold applies."
        assert "Ada Lovelace" in fake.seen_system  # grounded with real context

    def test_llm_error_falls_back(self, tmp_path: Path) -> None:
        prof, db = _seed(tmp_path)
        out = answer(
            _user("random open question"),
            profile_path=prof,
            db_path=db,
            client_factory=lambda: _FakeLLM(RuntimeError("down")),  # type: ignore[arg-type, return-value]
        )
        assert out.source == "rules"


class TestEndpoint:
    def _client(self, tmp_path: Path) -> TestClient:
        return TestClient(create_app(profile_path=tmp_path / "p.yaml", db_path=tmp_path / "j.db"))

    def test_chat_endpoint_answers(self, tmp_path: Path) -> None:
        resp = self._client(tmp_path).post(
            "/api/chat", json={"messages": [{"role": "user", "content": "help"}]}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["source"] == "rules" and "Deadlines" in body["reply"]

    def test_rejects_empty_messages(self, tmp_path: Path) -> None:
        assert self._client(tmp_path).post("/api/chat", json={"messages": []}).status_code == 422

    def test_rejects_assistant_last(self, tmp_path: Path) -> None:
        resp = self._client(tmp_path).post(
            "/api/chat", json={"messages": [{"role": "assistant", "content": "hi"}]}
        )
        assert resp.status_code == 422

    def test_rejects_oversized_content(self, tmp_path: Path) -> None:
        resp = self._client(tmp_path).post(
            "/api/chat", json={"messages": [{"role": "user", "content": "x" * 9000}]}
        )
        assert resp.status_code == 422
