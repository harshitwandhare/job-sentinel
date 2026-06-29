"""Tests for POST /api/interview/questions."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from job_sentinel.api.app import create_app

if TYPE_CHECKING:
    from pathlib import Path


def _client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(profile_path=tmp_path / "profile.yaml", db_path=tmp_path / "j.db"))


# ── defaults ──────────────────────────────────────────────────────────────────


def test_returns_questions_with_defaults(tmp_path: Path) -> None:
    resp = _client(tmp_path).post("/api/interview/questions", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert "questions" in body
    assert len(body["questions"]) > 0
    assert body["source"] in ("llm", "deterministic")
    assert "role_hint" in body


def test_deterministic_fallback_when_no_llm(tmp_path: Path) -> None:
    with patch(
        "job_sentinel.documents.providers.build_chat_backend",
        side_effect=ImportError("no backend"),
    ):
        resp = _client(tmp_path).post("/api/interview/questions", json={"ai": True})
    assert resp.status_code == 200
    assert resp.json()["source"] == "deterministic"


def test_question_count_respected(tmp_path: Path) -> None:
    resp = _client(tmp_path).post("/api/interview/questions", json={"count": 5, "ai": False})
    assert resp.status_code == 200
    assert len(resp.json()["questions"]) == 5


def test_max_count_capped_at_30(tmp_path: Path) -> None:
    resp = _client(tmp_path).post("/api/interview/questions", json={"count": 99})
    assert resp.status_code == 422


def test_min_count_is_1(tmp_path: Path) -> None:
    resp = _client(tmp_path).post("/api/interview/questions", json={"count": 0})
    assert resp.status_code == 422


def test_each_question_has_category_and_question(tmp_path: Path) -> None:
    resp = _client(tmp_path).post("/api/interview/questions", json={"ai": False})
    for q in resp.json()["questions"]:
        assert "category" in q
        assert "question" in q
        assert len(q["question"]) > 5


def test_role_hint_from_role_field(tmp_path: Path) -> None:
    resp = _client(tmp_path).post(
        "/api/interview/questions", json={"role": "Data Engineer", "ai": False}
    )
    assert resp.json()["role_hint"] == "Data Engineer"


def test_role_hint_from_jd_first_line(tmp_path: Path) -> None:
    resp = _client(tmp_path).post(
        "/api/interview/questions",
        json={"job_description": "Backend Engineer\nWe are looking for…", "ai": False},
    )
    assert "Backend Engineer" in resp.json()["role_hint"]


# ── LLM path ─────────────────────────────────────────────────────────────────


def test_uses_llm_when_available(tmp_path: Path) -> None:
    mock_backend = MagicMock()
    mock_backend.available.return_value = True
    mock_backend.ready.return_value = True
    mock_backend.chat.return_value = (
        '[{"category": "Technical", "question": "Describe your favourite data structure."}]'
    )

    with patch("job_sentinel.documents.providers.build_chat_backend", return_value=mock_backend):
        resp = _client(tmp_path).post(
            "/api/interview/questions", json={"role": "Engineer", "count": 1, "ai": True}
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "llm"
    assert body["questions"][0]["category"] == "Technical"
    assert "data structure" in body["questions"][0]["question"]


def test_falls_back_when_llm_returns_invalid_json(tmp_path: Path) -> None:
    mock_backend = MagicMock()
    mock_backend.available.return_value = True
    mock_backend.ready.return_value = True
    mock_backend.chat.return_value = "not json at all"

    with patch("job_sentinel.documents.providers.build_chat_backend", return_value=mock_backend):
        resp = _client(tmp_path).post("/api/interview/questions", json={"ai": True})

    assert resp.status_code == 200
    assert resp.json()["source"] == "deterministic"


def test_llm_json_with_markdown_fences(tmp_path: Path) -> None:
    mock_backend = MagicMock()
    mock_backend.available.return_value = True
    mock_backend.ready.return_value = True
    mock_backend.chat.return_value = (
        '```json\n[{"category": "Behavioural", "question": "Tell me about yourself."}]\n```'
    )

    with patch("job_sentinel.documents.providers.build_chat_backend", return_value=mock_backend):
        resp = _client(tmp_path).post(
            "/api/interview/questions", json={"role": "Eng", "count": 1, "ai": True}
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "llm"
    assert body["questions"][0]["question"] == "Tell me about yourself."
