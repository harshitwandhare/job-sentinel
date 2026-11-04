"""Regression: a database with duplicate meta rows must still open."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

from job_sentinel.db.repository import JobRepository

if TYPE_CHECKING:
    from pathlib import Path


def test_duplicate_schema_version_rows_do_not_break_opening(tmp_path: Path) -> None:
    """An older code path inserted schema_version without a primary key, so a
    real tracker ended up with the row twice. The back-fill that adds a unique
    index then failed on every open, which made the whole database unusable.
    """
    db_path = tmp_path / "jobs.db"
    con = sqlite3.connect(db_path)
    con.execute("CREATE TABLE sentinel_meta (key TEXT, value TEXT)")
    con.executemany(
        "INSERT INTO sentinel_meta (key, value) VALUES (?, ?)",
        [("schema_version", "2"), ("schema_version", "2")],
    )
    con.commit()
    con.close()

    repo = JobRepository(db_path)
    try:
        assert repo.list_applications() == []
    finally:
        repo.close()

    con = sqlite3.connect(db_path)
    rows = list(con.execute("SELECT key FROM sentinel_meta"))
    con.close()
    assert rows == [("schema_version",)], "the duplicate must be gone, not merely tolerated"
