"""Tests for the learned field map."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from job_sentinel.profile.fieldmap import FieldMap, LearnedLabel, load_fieldmap, save_fieldmap

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def learned() -> FieldMap:
    return FieldMap(
        labels=[
            LearnedLabel(label="Are you able to work in the US?", field_id="authorized_to_work"),
            LearnedLabel(
                label="Visa status",
                field_id="work_authorization_detail",
                ats="workday",
            ),
            LearnedLabel(label="Visa status", field_id="requires_sponsorship"),
        ]
    )


def test_resolves_a_taught_wording(learned: FieldMap) -> None:
    assert learned.resolve("Are you able to work in the US? *") == "authorized_to_work"


def test_normalises_before_looking_up(learned: FieldMap) -> None:
    """Punctuation and case must not decide whether a wording is recognised."""
    assert learned.resolve("ARE YOU ABLE TO WORK IN THE U.S.") == "authorized_to_work"


def test_the_boards_own_scope_beats_the_shared_one(learned: FieldMap) -> None:
    assert learned.resolve("Visa status", "workday") == "work_authorization_detail"
    assert learned.resolve("Visa status", "greenhouse") == "requires_sponsorship"


def test_unknown_wording_resolves_to_nothing(learned: FieldMap) -> None:
    assert learned.resolve("Favourite colour") is None
    assert learned.resolve("") is None


def test_relearning_updates_in_place(learned: FieldMap) -> None:
    """Correcting a mistake must not leave the wrong answer in the file."""
    before = len(learned.labels)
    learned.learn("Are you able to work in the US?", "us_citizen_or_pr")
    assert len(learned.labels) == before
    assert learned.resolve("Are you able to work in the US?") == "us_citizen_or_pr"


def test_learning_the_same_wording_on_another_board_adds_an_entry(learned: FieldMap) -> None:
    learned.learn("Are you able to work in the US?", "us_citizen_or_pr", "lever")
    assert learned.resolve("Are you able to work in the US?", "lever") == "us_citizen_or_pr"
    assert learned.resolve("Are you able to work in the US?") == "authorized_to_work"


def test_forget_removes_only_that_scope(learned: FieldMap) -> None:
    assert learned.forget("Visa status", "workday")
    assert learned.resolve("Visa status", "workday") == "requires_sponsorship"
    assert not learned.forget("Visa status", "workday")


def test_record_use_counts_against_the_entry(learned: FieldMap) -> None:
    learned.record_use("Visa status", "workday")
    entry = next(e for e in learned.labels if e.ats == "workday")
    assert entry.uses == 1


def test_round_trips_through_yaml(tmp_path: Path, learned: FieldMap) -> None:
    path = save_fieldmap(learned, tmp_path / "fieldmap.yaml")
    again = load_fieldmap(path)
    assert again.resolve("Visa status", "workday") == "work_authorization_detail"


def test_missing_file_gives_an_empty_map(tmp_path: Path) -> None:
    assert load_fieldmap(tmp_path / "nope.yaml").labels == []
