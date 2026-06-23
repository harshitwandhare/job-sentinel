"""
db/repository.py
─────────────────
SQLite persistence layer using **sqlite-utils**.

Why sqlite-utils over raw sqlite3?
  • ``db[table].insert()`` / ``.upsert()`` — no hand-written SQL for writes
  • Auto-creates tables from Python dicts (schema-less insertion)
  • ``db[table].transform()`` for zero-downtime schema migrations
  • Built-in ``enable_wal()`` for concurrent reader/writer safety
  • Full-text search via ``enable_fts()`` — one line to add FTS5
  • Still just SQLite under the hood — zero external services needed

Schema evolution
────────────────
  bump ``SCHEMA_VERSION`` and add a branch in ``_migrate()`` when the
  schema changes.  sqlite-utils' ``.transform()`` does column adds/renames
  without needing ALTER TABLE boilerplate.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

import sqlite_utils
from loguru import logger

from job_sentinel.core.models import (
    Application,
    ApplicationStage,
    ApplicationStatus,
    DocumentKind,
    GeneratedDocument,
    JobPosting,
)

if TYPE_CHECKING:
    from pathlib import Path

    from sqlite_utils.db import Table

SCHEMA_VERSION = 2
_TABLE = "job_postings"
_META_TABLE = "sentinel_meta"
_APP_TABLE = "applications"
_DOC_TABLE = "generated_documents"


class JobRepository:
    """
    Data-access object for the ``job_postings`` SQLite table.

    Thread-safe: sqlite-utils uses WAL mode; safe for the scheduler thread
    and Telegram bot thread to read/write concurrently.

    Parameters
    ----------
    db_path : Path
        Absolute path to the SQLite database file.
        Created (with parent directories) if it does not exist.
    """

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite_utils.Database(str(db_path))
        self._db.enable_wal()  # concurrent safe
        self._db.execute("PRAGMA foreign_keys = ON")
        self._init_schema()
        logger.info("Database ready | path={}", db_path)

    def _table(self, name: str) -> Table:
        """Typed accessor — ``db[name]`` is ``Table | View`` to mypy; we only
        ever address real tables here, so narrow it once in one place."""
        return cast("Table", self._db[name])

    # ─────────────────────────────────────────────────────────────────────
    # Schema management
    # ─────────────────────────────────────────────────────────────────────

    def _init_schema(self) -> None:
        """Create tables and run pending migrations."""
        # Meta table stores schema version
        if _META_TABLE not in self._db.table_names():
            self._table(_META_TABLE).insert({"key": "schema_version", "value": str(SCHEMA_VERSION)})
            logger.debug("Schema initialised at version {}", SCHEMA_VERSION)
        else:
            stored = self._get_meta("schema_version")
            version = int(stored) if stored else 0
            if version < SCHEMA_VERSION:
                self._migrate(from_version=version)

        # Ensure job_postings table exists with correct columns
        if _TABLE not in self._db.table_names():
            self._table(_TABLE).create(
                {
                    "posting_id": str,
                    "title": str,
                    "employer": str,
                    "location": str,
                    "job_type": str,
                    "posted_date": str,
                    "deadline": str,
                    "description_snippet": str,
                    "portal_url": str,
                    "status": str,
                    "discovered_at": str,
                    "updated_at": str,
                    "keywords_matched": str,  # JSON array
                    "source_adapter": str,
                    "raw_data": str,  # JSON object
                },
                pk="posting_id",
            )

            # Indexes for common query patterns
            self._table(_TABLE).create_index(["status"], if_not_exists=True)
            self._table(_TABLE).create_index(["discovered_at"], if_not_exists=True)
            self._table(_TABLE).create_index(["source_adapter"], if_not_exists=True)
            logger.debug("job_postings table created")

        self._ensure_applications_table()
        self._ensure_documents_table()

    def _ensure_applications_table(self) -> None:
        if _APP_TABLE not in self._db.table_names():
            self._table(_APP_TABLE).create(
                {
                    "id": str,
                    "title": str,
                    "employer": str,
                    "location": str,
                    "url": str,
                    "source": str,
                    "stage": str,
                    "salary": str,
                    "applied_date": str,
                    "deadline": str,
                    "notes": str,
                    "posting_id": str,
                    "resume_document_id": str,
                    "created_at": str,
                    "updated_at": str,
                    "raw_data": str,  # JSON
                },
                pk="id",
            )
            self._table(_APP_TABLE).create_index(["stage"], if_not_exists=True)
            self._table(_APP_TABLE).create_index(["created_at"], if_not_exists=True)
            logger.debug("applications table created")

    def _ensure_documents_table(self) -> None:
        if _DOC_TABLE not in self._db.table_names():
            self._table(_DOC_TABLE).create(
                {
                    "id": str,
                    "kind": str,
                    "label": str,
                    "title": str,
                    "employer": str,
                    "file_path": str,
                    "tex_path": str,
                    "ats_score": float,
                    "provider": str,
                    "tailored": int,  # SQLite has no bool; 0/1
                    "job_snippet": str,
                    "application_id": str,
                    "posting_id": str,
                    "created_at": str,
                    "raw_data": str,  # JSON
                },
                pk="id",
            )
            self._table(_DOC_TABLE).create_index(["kind"], if_not_exists=True)
            self._table(_DOC_TABLE).create_index(["created_at"], if_not_exists=True)
            logger.debug("generated_documents table created")

    def _get_meta(self, key: str) -> str | None:
        rows = list(self._table(_META_TABLE).rows_where("key = ?", [key]))
        return rows[0]["value"] if rows else None

    def _set_meta(self, key: str, value: str) -> None:
        self._table(_META_TABLE).upsert({"key": key, "value": value}, pk="key")

    def _migrate(self, from_version: int) -> None:
        logger.info("Migrating DB schema v{} → v{}", from_version, SCHEMA_VERSION)
        if from_version < 2:
            # Idempotent — only creates tables when they don't already exist.
            self._ensure_applications_table()
            self._ensure_documents_table()
        self._set_meta("schema_version", str(SCHEMA_VERSION))

    # ─────────────────────────────────────────────────────────────────────
    # Write operations
    # ─────────────────────────────────────────────────────────────────────

    def save_job(self, job: JobPosting) -> bool:
        """
        Persist a job posting (upsert semantics).

        If the record already exists with a user-set status (APPLIED /
        IGNORED), the status is preserved — the scraper cannot undo
        a human decision.

        Returns
        -------
        bool
            ``True`` if this was a brand-new insertion.
        """
        existing = self.get_job(job.posting_id)
        is_new = existing is None

        # Preserve human-set status
        if existing and existing.status not in (ApplicationStatus.NEW, ApplicationStatus.SEEN):
            job = job.model_copy(update={"status": existing.status})

        row = _to_row(job)
        self._table(_TABLE).upsert(row, pk="posting_id")

        action = "Inserted" if is_new else "Updated"
        logger.debug("{} job | id={} title={!r}", action, job.posting_id, job.title)
        return is_new

    def update_status(self, posting_id: str, status: ApplicationStatus) -> bool:
        """
        Update the tracking status of a job posting.

        Returns ``True`` if the record was found and updated.
        """
        if not self.exists(posting_id):
            logger.warning("update_status: posting {} not found", posting_id)
            return False

        self._table(_TABLE).update(
            posting_id,
            {
                "status": status.value,
                "updated_at": _now_iso(),
            },
        )
        logger.info("Status updated | id={} status={}", posting_id, status.value)
        return True

    def mark_seen(self, posting_id: str) -> None:
        """Convenience: mark posting as SEEN after alert is sent."""
        self.update_status(posting_id, ApplicationStatus.SEEN)

    # ─────────────────────────────────────────────────────────────────────
    # Read operations
    # ─────────────────────────────────────────────────────────────────────

    def get_job(self, posting_id: str) -> JobPosting | None:
        """Fetch a single posting by ID, or ``None``."""
        try:
            row = self._table(_TABLE).get(posting_id)
            return _from_row(dict(row))
        except sqlite_utils.db.NotFoundError:
            return None

    def exists(self, posting_id: str) -> bool:
        """Return ``True`` if this posting ID is already in the DB."""
        return self._table(_TABLE).count_where("posting_id = ?", [posting_id]) > 0

    def get_new_jobs(self) -> list[JobPosting]:
        """All postings with status NEW, newest-first."""
        return self._query_status(ApplicationStatus.NEW)

    def get_recent_jobs(self, limit: int = 10) -> list[JobPosting]:
        """Most recently discovered postings (any status)."""
        rows = self._table(_TABLE).rows_where(
            order_by="discovered_at DESC",
            limit=limit,
        )
        return [_from_row(dict(r)) for r in rows]

    def get_by_status(self, status: ApplicationStatus) -> list[JobPosting]:
        """All postings with the given status."""
        return self._query_status(status)

    def _query_status(self, status: ApplicationStatus) -> list[JobPosting]:
        rows = self._table(_TABLE).rows_where(
            "status = ?",
            [status.value],
            order_by="discovered_at DESC",
        )
        return [_from_row(dict(r)) for r in rows]

    # ─────────────────────────────────────────────────────────────────────
    # Statistics
    # ─────────────────────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, int]:
        """Aggregate counts per status — used by /stats Telegram command."""
        counts: dict[str, int] = {s.value: 0 for s in ApplicationStatus}
        for row in self._db.execute(
            f"SELECT status, COUNT(*) AS cnt FROM {_TABLE} GROUP BY status"  # noqa: S608 — _TABLE is a module constant, never user input
        ).fetchall():
            counts[row[0]] = row[1]
        counts["total"] = sum(counts.values())
        return counts

    # ─────────────────────────────────────────────────────────────────────
    # Housekeeping
    # ─────────────────────────────────────────────────────────────────────

    def close(self) -> None:
        self._db.conn.close()
        logger.debug("Database connection closed")

    # ─────────────────────────────────────────────────────────────────────
    # Application CRUD
    # ─────────────────────────────────────────────────────────────────────

    def create_application(self, app: Application) -> Application:
        """Persist a new Application row and return it."""
        self._table(_APP_TABLE).insert(_app_to_row(app))
        logger.debug("Application created | id={}", app.id)
        return app

    def get_application(self, app_id: str) -> Application | None:
        """Fetch a single Application by id, or None."""
        try:
            row = self._table(_APP_TABLE).get(app_id)
            return _app_from_row(dict(row))
        except sqlite_utils.db.NotFoundError:
            return None

    def list_applications(
        self,
        stage: ApplicationStage | None = None,
        limit: int = 200,
    ) -> list[Application]:
        """Return applications newest-first, optionally filtered by stage."""
        if stage is not None:
            rows = self._table(_APP_TABLE).rows_where(
                "stage = ?",
                [stage.value],
                order_by="created_at DESC",
                limit=limit,
            )
        else:
            rows = self._table(_APP_TABLE).rows_where(
                order_by="created_at DESC",
                limit=limit,
            )
        return [_app_from_row(dict(r)) for r in rows]

    def update_application(self, app_id: str, **fields: Any) -> bool:
        """
        Partially update an Application row.

        Always bumps ``updated_at``.  Returns True if the row existed.
        """
        if self.get_application(app_id) is None:
            return False
        fields["updated_at"] = _now_iso()
        # Coerce stage enum to its value string if passed.
        if "stage" in fields and isinstance(fields["stage"], ApplicationStage):
            fields["stage"] = fields["stage"].value
        self._table(_APP_TABLE).update(app_id, fields)
        return True

    def delete_application(self, app_id: str) -> bool:
        """Delete an application. Returns True if the row existed."""
        if self.get_application(app_id) is None:
            return False
        self._table(_APP_TABLE).delete(app_id)
        return True

    def application_stats(self) -> dict[str, int]:
        """Count of applications per stage, plus a 'total' key."""
        counts: dict[str, int] = {s.value: 0 for s in ApplicationStage}
        for row in self._db.execute(
            f"SELECT stage, COUNT(*) AS cnt FROM {_APP_TABLE} GROUP BY stage"  # noqa: S608
        ).fetchall():
            counts[row[0]] = row[1]
        counts["total"] = sum(counts.values())
        return counts

    def application_analytics(self) -> dict[str, object]:
        """
        Compute richer application analytics over the local tracker data.

        Returns a dict with three sections:
        - ``funnel``: stage → count + pct_of_applied for the conversion funnel
        - ``by_source``: source → {applied, responded, response_rate}
        - ``weekly_volume``: list of {week, count} for the last 8 ISO weeks
        """
        # ── Funnel ────────────────────────────────────────────────────────
        stage_counts: dict[str, int] = {s.value: 0 for s in ApplicationStage}
        for row in self._db.execute(
            f"SELECT stage, COUNT(*) AS cnt FROM {_APP_TABLE} GROUP BY stage"  # noqa: S608
        ).fetchall():
            stage_counts[row[0]] = row[1]

        applied = stage_counts.get(ApplicationStage.APPLIED, 0)
        funnel: list[dict[str, object]] = []
        downstream = [
            ApplicationStage.INTERVIEWING,
            ApplicationStage.OFFER,
            ApplicationStage.REJECTED,
        ]
        for stage in ApplicationStage:
            cnt = stage_counts[stage.value]
            pct: float | None = None
            if stage in downstream and applied > 0:
                pct = round(cnt / applied * 100, 1)
            funnel.append({"stage": stage.value, "count": cnt, "pct_of_applied": pct})

        # Response = interviewing + offer (any non-silence after applying)
        responded = stage_counts.get(ApplicationStage.INTERVIEWING, 0) + stage_counts.get(
            ApplicationStage.OFFER, 0
        )
        overall_response_rate: float | None = (
            round(responded / applied * 100, 1) if applied > 0 else None
        )

        # ── By source ─────────────────────────────────────────────────────
        source_rows = self._db.execute(
            f"""
            SELECT
                source,
                COUNT(*) AS total,
                SUM(CASE WHEN stage IN ('interviewing','offer') THEN 1 ELSE 0 END) AS responded
            FROM {_APP_TABLE}
            WHERE stage NOT IN ('saved','archived')
            GROUP BY source
            ORDER BY total DESC
            """  # noqa: S608
        ).fetchall()
        by_source: list[dict[str, object]] = []
        for src_row in source_rows:
            src, total, src_responded = src_row
            rr: float | None = round(src_responded / total * 100, 1) if total > 0 else None
            by_source.append(
                {
                    "source": src or "manual",
                    "applied": total,
                    "responded": src_responded,
                    "response_rate": rr,
                }
            )

        # ── Weekly volume (last 8 weeks) ───────────────────────────────────
        weekly_rows = self._db.execute(
            f"""
            SELECT
                strftime('%Y-W%W', applied_date) AS week,
                COUNT(*) AS cnt
            FROM {_APP_TABLE}
            WHERE applied_date != ''
              AND applied_date IS NOT NULL
              AND date(applied_date) >= date('now', '-56 days')
            GROUP BY week
            ORDER BY week ASC
            """  # noqa: S608
        ).fetchall()
        weekly_volume = [{"week": r[0], "count": r[1]} for r in weekly_rows]

        return {
            "funnel": funnel,
            "overall_response_rate": overall_response_rate,
            "by_source": by_source,
            "weekly_volume": weekly_volume,
        }

    # ─────────────────────────────────────────────────────────────────────
    # GeneratedDocument CRUD
    # ─────────────────────────────────────────────────────────────────────

    def create_document(self, doc: GeneratedDocument) -> GeneratedDocument:
        """Persist a new GeneratedDocument row and return it."""
        self._table(_DOC_TABLE).insert(_doc_to_row(doc))
        logger.debug("Document created | id={} kind={}", doc.id, doc.kind.value)
        return doc

    def get_document(self, doc_id: str) -> GeneratedDocument | None:
        """Fetch a single GeneratedDocument by id, or None."""
        try:
            row = self._table(_DOC_TABLE).get(doc_id)
            return _doc_from_row(dict(row))
        except sqlite_utils.db.NotFoundError:
            return None

    def list_documents(
        self,
        kind: DocumentKind | None = None,
        limit: int = 200,
    ) -> list[GeneratedDocument]:
        """Return documents newest-first, optionally filtered by kind."""
        if kind is not None:
            rows = self._table(_DOC_TABLE).rows_where(
                "kind = ?",
                [kind.value],
                order_by="created_at DESC",
                limit=limit,
            )
        else:
            rows = self._table(_DOC_TABLE).rows_where(
                order_by="created_at DESC",
                limit=limit,
            )
        return [_doc_from_row(dict(r)) for r in rows]

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document record. Returns True if the row existed."""
        if self.get_document(doc_id) is None:
            return False
        self._table(_DOC_TABLE).delete(doc_id)
        return True


# ─────────────────────────────────────────────────────────────────────────────
# Serialisation helpers
# ─────────────────────────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _to_row(job: JobPosting) -> dict[str, Any]:
    return {
        "posting_id": job.posting_id,
        "title": job.title,
        "employer": job.employer,
        "location": job.location,
        "job_type": job.job_type,
        "posted_date": job.posted_date,
        "deadline": job.deadline,
        "description_snippet": job.description_snippet,
        "portal_url": job.portal_url,
        "status": job.status.value,
        "discovered_at": job.discovered_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "keywords_matched": json.dumps(job.keywords_matched),
        "source_adapter": job.source_adapter,
        "raw_data": json.dumps(job.raw_data),
    }


def _from_row(row: dict[str, Any]) -> JobPosting:
    return JobPosting(
        posting_id=row["posting_id"],
        title=row.get("title", ""),
        employer=row.get("employer", ""),
        location=row.get("location", ""),
        job_type=row.get("job_type", ""),
        posted_date=row.get("posted_date", ""),
        deadline=row.get("deadline", ""),
        description_snippet=row.get("description_snippet", ""),
        portal_url=row.get("portal_url", ""),
        status=ApplicationStatus(row.get("status", "new")),
        discovered_at=_parse_dt(row.get("discovered_at", "")),
        updated_at=_parse_dt(row.get("updated_at", "")),
        keywords_matched=json.loads(row.get("keywords_matched") or "[]"),
        source_adapter=row.get("source_adapter", ""),
        raw_data=json.loads(row.get("raw_data") or "{}"),
    )


def _parse_dt(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return datetime.now(tz=UTC)


# ── Application helpers ───────────────────────────────────────────────────────


def _app_to_row(app: Application) -> dict[str, Any]:
    return {
        "id": app.id,
        "title": app.title,
        "employer": app.employer,
        "location": app.location,
        "url": app.url,
        "source": app.source,
        "stage": app.stage.value,
        "salary": app.salary,
        "applied_date": app.applied_date,
        "deadline": app.deadline,
        "notes": app.notes,
        "posting_id": app.posting_id,
        "resume_document_id": app.resume_document_id,
        "created_at": app.created_at.isoformat(),
        "updated_at": app.updated_at.isoformat(),
        "raw_data": json.dumps(app.raw_data),
    }


def _app_from_row(row: dict[str, Any]) -> Application:
    return Application(
        id=row["id"],
        title=row.get("title", ""),
        employer=row.get("employer", ""),
        location=row.get("location", ""),
        url=row.get("url", ""),
        source=row.get("source", ""),
        stage=ApplicationStage(row.get("stage", ApplicationStage.SAVED.value)),
        salary=row.get("salary", ""),
        applied_date=row.get("applied_date", ""),
        deadline=row.get("deadline", ""),
        notes=row.get("notes", ""),
        posting_id=row.get("posting_id") or None,
        resume_document_id=row.get("resume_document_id") or None,
        created_at=_parse_dt(row.get("created_at", "")),
        updated_at=_parse_dt(row.get("updated_at", "")),
        raw_data=json.loads(row.get("raw_data") or "{}"),
    )


# ── GeneratedDocument helpers ─────────────────────────────────────────────────


def _doc_to_row(doc: GeneratedDocument) -> dict[str, Any]:
    return {
        "id": doc.id,
        "kind": doc.kind.value,
        "label": doc.label,
        "title": doc.title,
        "employer": doc.employer,
        "file_path": doc.file_path,
        "tex_path": doc.tex_path,
        "ats_score": doc.ats_score,
        "provider": doc.provider,
        "tailored": 1 if doc.tailored else 0,
        "job_snippet": doc.job_snippet,
        "application_id": doc.application_id,
        "posting_id": doc.posting_id,
        "created_at": doc.created_at.isoformat(),
        "raw_data": json.dumps(doc.raw_data),
    }


def _doc_from_row(row: dict[str, Any]) -> GeneratedDocument:
    ats_raw = row.get("ats_score")
    return GeneratedDocument(
        id=row["id"],
        kind=DocumentKind(row.get("kind", DocumentKind.RESUME.value)),
        label=row.get("label", ""),
        title=row.get("title", ""),
        employer=row.get("employer", ""),
        file_path=row.get("file_path", ""),
        tex_path=row.get("tex_path") or None,
        ats_score=float(ats_raw) if ats_raw is not None else None,
        provider=row.get("provider", ""),
        tailored=bool(row.get("tailored", 0)),
        job_snippet=row.get("job_snippet", ""),
        application_id=row.get("application_id") or None,
        posting_id=row.get("posting_id") or None,
        created_at=_parse_dt(row.get("created_at", "")),
        raw_data=json.loads(row.get("raw_data") or "{}"),
    )
