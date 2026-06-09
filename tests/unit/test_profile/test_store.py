"""Tests for the universal-profile models and YAML round-trip."""

from __future__ import annotations

from typing import TYPE_CHECKING

from job_sentinel.profile import (
    Experience,
    Profile,
    example_profile,
    load_profile,
    save_profile,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_empty_profile_is_valid_and_flagged_empty() -> None:
    p = Profile()
    assert p.is_empty() is True
    assert p.basics.name == ""
    assert p.education == []


def test_example_profile_is_populated() -> None:
    p = example_profile()
    assert p.is_empty() is False
    assert p.basics.name
    assert p.experience and p.projects and p.skills


def test_load_missing_file_returns_empty(tmp_path: Path) -> None:
    assert load_profile(tmp_path / "nope.yaml").is_empty() is True


def test_yaml_round_trip(tmp_path: Path) -> None:
    original = example_profile()
    path = save_profile(original, tmp_path / "profile.yaml")
    assert path.is_file()

    reloaded = load_profile(path)
    assert reloaded.basics.name == original.basics.name
    assert [e.company for e in reloaded.experience] == [e.company for e in original.experience]
    assert reloaded.skills[0].skills == original.skills[0].skills


def test_tags_survive_round_trip(tmp_path: Path) -> None:
    p = Profile(experience=[Experience(company="X", role="Dev", tags=["python", "ml"])])
    reloaded = load_profile(save_profile(p, tmp_path / "p.yaml"))
    assert reloaded.experience[0].tags == ["python", "ml"]
