"""Tests for the answer-bank API routes."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from job_sentinel.api.app import create_app
from job_sentinel.profile import AnswerBank, AnswerField, FieldKind, save_answers

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    bank = AnswerBank(
        updated="2026-11-03",
        fields=[
            AnswerField(
                id="authorized_to_work",
                match=["legally authorized to work in the united states"],
                kind=FieldKind.RADIO,
                value="Yes",
                options=["Yes", "No"],
            ),
            AnswerField(
                id="gpa",
                match=["gpa"],
                kind=FieldKind.TEXT,
                value="9.9",
                note="Read it off your transcript.",
            ),
        ],
        private=["gpa"],
        resume_routing=[{"match": ["machine learning"], "file": "ai.pdf"}],
    )
    save_answers(bank, tmp_path / "answers.yaml")
    return TestClient(
        create_app(
            profile_path=tmp_path / "profile.yaml",
            db_path=tmp_path / "jobs.db",
            auth_dir=tmp_path,
            answers_path=tmp_path / "answers.yaml",
        )
    )


def test_get_answers_returns_the_bank(client: TestClient) -> None:
    body = client.get("/api/answers").json()
    assert body["updated"] == "2026-11-03"
    assert [f["id"] for f in body["fields"]] == ["authorized_to_work", "gpa"]


def test_match_resolves_labels_in_order(client: TestClient) -> None:
    labels = [
        "Are you legally authorized to work in the United States? *",
        "Favourite colour",
    ]
    body = client.post("/api/answers/match", json={"labels": labels}).json()
    assert [m["label"] for m in body] == labels
    assert body[0]["field_id"] == "authorized_to_work"
    assert body[0]["value"] == "Yes"
    assert body[0]["options"] == ["Yes", "No"]


def test_unmatched_label_comes_back_with_a_null_field(client: TestClient) -> None:
    """The filler needs to show the user what it skipped, not silently drop it."""
    body = client.post("/api/answers/match", json={"labels": ["Favourite colour"]}).json()
    assert body[0]["field_id"] is None
    assert body[0]["value"] is None


def test_private_field_never_hands_out_its_value(client: TestClient) -> None:
    """A stored GPA must still not reach the filler."""
    body = client.post("/api/answers/match", json={"labels": ["Cumulative GPA"]}).json()
    assert body[0]["field_id"] == "gpa"
    assert body[0]["private"] is True
    assert body[0]["value"] is None
    assert "transcript" in body[0]["note"]


def test_empty_label_list_is_fine(client: TestClient) -> None:
    assert client.post("/api/answers/match", json={"labels": []}).json() == []


@pytest.mark.parametrize(
    ("title", "expected"),
    [("Machine Learning Intern", "ai.pdf"), ("Barista", None)],
)
def test_resume_routing_route(client: TestClient, title: str, expected: str | None) -> None:
    body = client.get("/api/answers/resume", params={"title": title}).json()
    assert body["title"] == title
    assert body["file"] == expected
    # No resume_root in this bank, so there is nowhere on disk to point at.
    assert body["path"] is None
    assert body["exists"] is False


def test_missing_answers_file_gives_an_empty_bank(tmp_path: Path) -> None:
    client = TestClient(
        create_app(
            profile_path=tmp_path / "profile.yaml",
            db_path=tmp_path / "jobs.db",
            auth_dir=tmp_path,
            answers_path=tmp_path / "absent.yaml",
        )
    )
    assert client.get("/api/answers").json()["fields"] == []
    body = client.post("/api/answers/match", json={"labels": ["Anything"]}).json()
    assert body[0]["field_id"] is None
