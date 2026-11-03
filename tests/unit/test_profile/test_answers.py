"""Tests for the application answer bank."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from job_sentinel.profile.answers import (
    AnswerBank,
    AnswerField,
    FieldKind,
    example_answers,
    load_answers,
    normalise,
    save_answers,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def bank() -> AnswerBank:
    return AnswerBank(
        fields=[
            AnswerField(
                id="us_citizen_or_pr",
                match=["are you a us citizen or permanent resident", "citizenship status"],
                kind=FieldKind.RADIO,
                value="No",
            ),
            AnswerField(
                id="authorized_to_work",
                match=["legally authorized to work in the united states"],
                kind=FieldKind.RADIO,
                value="Yes",
            ),
            AnswerField(id="degree", match=["degree"], kind=FieldKind.SELECT, value="Master"),
            AnswerField(
                id="degree_level",
                match=["what degree level are you pursuing"],
                kind=FieldKind.SELECT,
                value="Graduate",
            ),
            AnswerField(id="gpa", match=["gpa"], kind=FieldKind.TEXT, value=None),
        ],
        private=["gpa"],
        resume_routing=[
            {"match": ["machine learning", "ai"], "file": "ai.pdf"},
            {"match": ["software engineer"], "file": "swe.pdf"},
        ],
    )


# ── normalise ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Are you a U.S. Citizen? *", "are you a us citizen"),
        ("Bachelor's Degree", "bachelors degree"),
        ("E-mail Address", "e mail address"),
    ],
)
def test_normalise(raw: str, expected: str) -> None:
    assert normalise(raw) == expected


def test_abbreviation_dots_do_not_split_the_word() -> None:
    """Regression: 'U.S.' became 'u s', so 'us citizen' never matched."""
    assert normalise("U.S. Citizen") == "us citizen"


def test_exotic_whitespace_collapses() -> None:
    """Form labels routinely carry non-breaking spaces. Built by codepoint
    rather than pasted, so the source cannot be misread as a normal space."""
    nbsp = chr(0x00A0)
    assert normalise(f"  Phone{nbsp}Number:  ") == "phone number"


# ── find ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "label",
    [
        "Are you a U.S. Citizen or Permanent Resident? *",
        "Are you a US citizen or permanent resident",
        "ARE YOU A U.S. CITIZEN OR PERMANENT RESIDENT?",
    ],
)
def test_finds_the_same_field_through_different_phrasings(bank: AnswerBank, label: str) -> None:
    found = bank.find(label)
    assert found is not None
    assert found.id == "us_citizen_or_pr"


def test_longest_match_wins(bank: AnswerBank) -> None:
    """A specific question must beat a field matching one of its words."""
    found = bank.find("What degree level are you pursuing?")
    assert found is not None
    assert found.id == "degree_level"


def test_unknown_label_returns_none(bank: AnswerBank) -> None:
    assert bank.find("What is your favourite colour?") is None
    assert bank.find("") is None


def test_private_fields_carry_no_value(bank: AnswerBank) -> None:
    gpa = bank.find("Cumulative GPA")
    assert gpa is not None
    assert bank.is_private(gpa.id)
    assert not gpa.answerable


def test_answerable_is_false_for_empty_values() -> None:
    assert not AnswerField(id="x", value=None).answerable
    assert not AnswerField(id="x", value="").answerable
    assert AnswerField(id="x", value="Yes").answerable


# ── resume routing ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Machine Learning Engineer Intern", "ai.pdf"),
        ("AI Systems Software Engineering Intern", "ai.pdf"),
        ("Software Engineer Intern", "swe.pdf"),
        ("Barista", None),
    ],
)
def test_resume_routing(bank: AnswerBank, title: str, expected: str | None) -> None:
    assert bank.resume_for(title) == expected


@pytest.mark.parametrize("title", ["Chair Designer", "Said Consulting Analyst", "Retail Associate"])
def test_short_tokens_do_not_match_inside_words(bank: AnswerBank, title: str) -> None:
    """Regression: the 'ai' rule matched 'chair' and 'said' as substrings."""
    assert bank.resume_for(title) is None


# ── persistence ───────────────────────────────────────────────────────────────


def test_round_trips_through_yaml(tmp_path: Path, bank: AnswerBank) -> None:
    path = save_answers(bank, tmp_path / "answers.yaml")
    assert path.is_file()
    again = load_answers(path)
    assert [f.id for f in again.fields] == [f.id for f in bank.fields]
    assert again.private == bank.private
    assert again.resume_for("Machine Learning Intern") == "ai.pdf"


def test_missing_file_gives_an_empty_bank(tmp_path: Path) -> None:
    empty = load_answers(tmp_path / "nope.yaml")
    assert empty.fields == []
    assert empty.find("anything") is None


def test_example_bank_is_usable_and_leaves_judgement_calls_blank() -> None:
    seed = example_answers()
    assert seed.fields
    sponsorship = seed.find("Will you now or in the future require sponsorship?")
    assert sponsorship is not None
    assert not sponsorship.answerable, "the user answers the sponsorship question themselves"
    assert seed.is_private("gpa")
