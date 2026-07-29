"""Unit tests for the `job-sentinel apps` CLI subcommands."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from job_sentinel import __main__ as main_module
from job_sentinel.db.repository import JobRepository

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()


@pytest.fixture()
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "jobs.db"
    monkeypatch.setattr(main_module, "_DEFAULT_DB", db_path)
    return db_path


def test_apps_add_persists_all_fields(isolated_db: Path) -> None:
    result = runner.invoke(
        main_module.app,
        [
            "apps",
            "add",
            "--title",
            "Backend Engineer",
            "--employer",
            "Acme Corp",
            "--location",
            "Remote",
            "--url",
            "https://example.com/job/1",
            "--source",
            "manual",
            "--stage",
            "applied",
            "--salary",
            "$120k-$140k",
            "--applied-date",
            "2026-07-01",
            "--deadline",
            "2026-08-01",
            "--notes",
            "Referred by a friend",
        ],
    )

    assert result.exit_code == 0, result.output

    repo = JobRepository(isolated_db)
    try:
        apps = repo.list_applications()
    finally:
        repo.close()

    assert len(apps) == 1
    saved = apps[0]
    assert saved.title == "Backend Engineer"
    assert saved.employer == "Acme Corp"
    assert saved.location == "Remote"
    assert saved.salary == "$120k-$140k"
    assert saved.applied_date == "2026-07-01"
    assert saved.deadline == "2026-08-01"
    assert saved.notes == "Referred by a friend"


def test_apps_add_defaults_to_empty_optional_fields(isolated_db: Path) -> None:
    result = runner.invoke(
        main_module.app,
        ["apps", "add", "--title", "Data Analyst"],
    )

    assert result.exit_code == 0, result.output

    repo = JobRepository(isolated_db)
    try:
        apps = repo.list_applications()
    finally:
        repo.close()

    saved = apps[0]
    assert saved.title == "Data Analyst"
    assert saved.salary == ""
    assert saved.applied_date == ""
    assert saved.deadline == ""
    assert saved.notes == ""


def test_apps_list_respects_limit(isolated_db: Path) -> None:
    for i in range(3):
        result = runner.invoke(
            main_module.app,
            ["apps", "add", "--title", f"Job {i}"],
        )
        assert result.exit_code == 0, result.output

    result = runner.invoke(main_module.app, ["apps", "list", "--limit", "2"])
    assert result.exit_code == 0, result.output

    repo = JobRepository(isolated_db)
    try:
        limited = repo.list_applications(limit=2)
    finally:
        repo.close()
    assert len(limited) == 2
