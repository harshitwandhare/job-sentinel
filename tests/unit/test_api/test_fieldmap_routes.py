"""Tests for the learned-field-map routes and their effect on matching."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from job_sentinel.api.app import create_app
from job_sentinel.profile import AnswerBank, AnswerField, FieldKind, save_answers

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def paths(tmp_path: Path) -> dict[str, Path]:
    bank = AnswerBank(
        fields=[
            AnswerField(
                id="authorized_to_work",
                match=["legally authorized to work"],
                kind=FieldKind.RADIO,
                value="Yes",
            ),
            AnswerField(id="gpa", match=["gpa"], kind=FieldKind.TEXT, value="x"),
        ],
        private=["gpa"],
    )
    save_answers(bank, tmp_path / "answers.yaml")
    return {
        "answers": tmp_path / "answers.yaml",
        "fieldmap": tmp_path / "fieldmap.yaml",
        "tmp": tmp_path,
    }


@pytest.fixture
def client(paths: dict[str, Path]) -> TestClient:
    return TestClient(
        create_app(
            profile_path=paths["tmp"] / "profile.yaml",
            db_path=paths["tmp"] / "jobs.db",
            auth_dir=paths["tmp"],
            answers_path=paths["answers"],
            fieldmap_path=paths["fieldmap"],
        )
    )


UNKNOWN = "Can you work in this country without help from us?"


def test_an_unknown_wording_matches_nothing_before_it_is_taught(client: TestClient) -> None:
    body = client.post("/api/answers/match", json={"labels": [UNKNOWN]}).json()
    assert body[0]["field_id"] is None


def test_once_taught_the_wording_resolves(client: TestClient) -> None:
    client.post(
        "/api/fieldmap/learn",
        json={"label": UNKNOWN, "field_id": "authorized_to_work", "ats": "workday"},
    )
    body = client.post("/api/answers/match", json={"labels": [UNKNOWN], "ats": "workday"}).json()
    assert body[0]["field_id"] == "authorized_to_work"
    assert body[0]["value"] == "Yes"
    assert body[0]["learned"] is True


def test_a_wording_taught_for_one_board_does_not_answer_on_another(client: TestClient) -> None:
    """Boards word different questions the same way; a global map answers the
    wrong one."""
    client.post(
        "/api/fieldmap/learn",
        json={"label": UNKNOWN, "field_id": "authorized_to_work", "ats": "workday"},
    )
    body = client.post("/api/answers/match", json={"labels": [UNKNOWN], "ats": "greenhouse"}).json()
    assert body[0]["field_id"] is None


def test_teaching_an_unknown_field_id_is_refused(client: TestClient) -> None:
    """A mapping to a field that does not exist would silently resolve to
    nothing on the next form."""
    resp = client.post("/api/fieldmap/learn", json={"label": UNKNOWN, "field_id": "nope"})
    assert resp.status_code == 404


def test_a_learned_private_field_still_hands_out_no_value(client: TestClient) -> None:
    client.post("/api/fieldmap/learn", json={"label": "Academic average", "field_id": "gpa"})
    body = client.post("/api/answers/match", json={"labels": ["Academic average"]}).json()
    assert body[0]["field_id"] == "gpa"
    assert body[0]["private"] is True
    assert body[0]["value"] is None


def test_the_bank_wins_over_a_learned_wording(client: TestClient) -> None:
    """Teaching must never override an answer the user wrote by hand."""
    client.post(
        "/api/fieldmap/learn",
        json={"label": "Are you legally authorized to work here?", "field_id": "gpa"},
    )
    body = client.post(
        "/api/answers/match", json={"labels": ["Are you legally authorized to work here?"]}
    ).json()
    assert body[0]["field_id"] == "authorized_to_work"


def test_forget_drops_the_wording(client: TestClient) -> None:
    client.post("/api/fieldmap/learn", json={"label": UNKNOWN, "field_id": "authorized_to_work"})
    assert client.delete(f"/api/fieldmap/{UNKNOWN}").json() == {"removed": True}
    body = client.post("/api/answers/match", json={"labels": [UNKNOWN]}).json()
    assert body[0]["field_id"] is None


def test_use_counts_are_recorded(client: TestClient) -> None:
    client.post("/api/fieldmap/learn", json={"label": UNKNOWN, "field_id": "authorized_to_work"})
    client.post("/api/answers/match", json={"labels": [UNKNOWN]})
    client.post("/api/answers/match", json={"labels": [UNKNOWN]})
    assert client.get("/api/fieldmap").json()["labels"][0]["uses"] == 2
