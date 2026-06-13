"""
Tests for the applications + documents API routes and the build-endpoint
document-persistence side-effect.

PDF build is monkeypatched to avoid requiring Tectonic/LaTeX on the CI machine.
The existing test_app.py already shows the pattern: test_build_with_profile_returns_pdf_or_503
accepts both 200 and 503.  Here we patch at a lower level so we can assert on
the X-Document-Id header and the repository row unconditionally.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from job_sentinel.api.app import create_app
from job_sentinel.core.models import Application, ApplicationStage, DocumentKind, GeneratedDocument
from job_sentinel.db.repository import JobRepository

if TYPE_CHECKING:
    from pathlib import Path


# ── helpers ───────────────────────────────────────────────────────────────────


def _client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(profile_path=tmp_path / "profile.yaml", db_path=tmp_path / "j.db"),
        raise_server_exceptions=True,
    )


def _seed_app(tmp_path: Path, **kwargs: object) -> Application:
    db = tmp_path / "j.db"
    repo = JobRepository(db)
    app = Application(title="SWE", employer="Acme", **kwargs)  # type: ignore[arg-type]
    repo.create_application(app)
    repo.close()
    return app


def _seed_doc(tmp_path: Path, **kwargs: object) -> GeneratedDocument:
    db = tmp_path / "j.db"
    repo = JobRepository(db)
    merged: dict[str, object] = {"kind": DocumentKind.RESUME}
    merged.update(kwargs)
    doc = GeneratedDocument(**merged)  # type: ignore[arg-type]
    repo.create_document(doc)
    repo.close()
    return doc


# ── GET /api/applications ─────────────────────────────────────────────────────


def test_list_applications_empty(tmp_path: Path) -> None:
    resp = _client(tmp_path).get("/api/applications")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_applications_with_data(tmp_path: Path) -> None:
    _seed_app(tmp_path)
    resp = _client(tmp_path).get("/api/applications")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "SWE"


def test_list_applications_stage_filter(tmp_path: Path) -> None:
    _seed_app(tmp_path, stage=ApplicationStage.APPLIED)
    _seed_app(tmp_path, stage=ApplicationStage.SAVED)
    resp = _client(tmp_path).get("/api/applications?stage=applied")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["stage"] == "applied"


# ── POST /api/applications ────────────────────────────────────────────────────


def test_create_application_manual(tmp_path: Path) -> None:
    resp = _client(tmp_path).post(
        "/api/applications",
        json={"title": "Backend Eng", "employer": "BigCo", "stage": "saved"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Backend Eng"
    assert body["stage"] == "saved"
    assert "id" in body


def test_create_application_from_posting_404(tmp_path: Path) -> None:
    resp = _client(tmp_path).post(
        "/api/applications",
        json={"posting_id": "nonexistent-id"},
    )
    assert resp.status_code == 404


def test_create_application_from_posting(tmp_path: Path) -> None:
    from job_sentinel.core.models import JobPosting

    db = tmp_path / "j.db"
    repo = JobRepository(db)
    posting = JobPosting(
        posting_id="p-001",
        title="ML Engineer",
        employer="AI Corp",
        location="Austin, TX",
        portal_url="https://example.com",
        source_adapter="12twenty",
    )
    repo.save_job(posting)
    repo.close()

    resp = _client(tmp_path).post("/api/applications", json={"posting_id": "p-001"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "ML Engineer"
    assert body["employer"] == "AI Corp"
    assert body["posting_id"] == "p-001"
    assert body["stage"] == "applied"  # defaults to APPLIED when sourced from a posting


# ── GET /api/applications/{id} ────────────────────────────────────────────────


def test_get_application_found(tmp_path: Path) -> None:
    app = _seed_app(tmp_path)
    resp = _client(tmp_path).get(f"/api/applications/{app.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == app.id


def test_get_application_not_found(tmp_path: Path) -> None:
    resp = _client(tmp_path).get("/api/applications/ghost-id")
    assert resp.status_code == 404


# ── PATCH /api/applications/{id} ─────────────────────────────────────────────


def test_patch_application_stage(tmp_path: Path) -> None:
    app = _seed_app(tmp_path)
    resp = _client(tmp_path).patch(f"/api/applications/{app.id}", json={"stage": "interviewing"})
    assert resp.status_code == 200
    assert resp.json()["stage"] == "interviewing"


def test_patch_application_notes(tmp_path: Path) -> None:
    app = _seed_app(tmp_path)
    resp = _client(tmp_path).patch(
        f"/api/applications/{app.id}", json={"notes": "great culture fit"}
    )
    assert resp.status_code == 200
    assert resp.json()["notes"] == "great culture fit"


def test_patch_application_not_found(tmp_path: Path) -> None:
    resp = _client(tmp_path).patch("/api/applications/ghost", json={"stage": "offer"})
    assert resp.status_code == 404


# ── DELETE /api/applications/{id} ────────────────────────────────────────────


def test_delete_application(tmp_path: Path) -> None:
    app = _seed_app(tmp_path)
    resp = _client(tmp_path).delete(f"/api/applications/{app.id}")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    # Confirm it's gone.
    assert _client(tmp_path).get(f"/api/applications/{app.id}").status_code == 404


def test_delete_application_not_found(tmp_path: Path) -> None:
    resp = _client(tmp_path).delete("/api/applications/ghost")
    assert resp.status_code == 404


# ── GET /api/applications/stats ──────────────────────────────────────────────


def test_applications_stats_empty(tmp_path: Path) -> None:
    resp = _client(tmp_path).get("/api/applications/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert "saved" in body


def test_applications_stats_counts(tmp_path: Path) -> None:
    _seed_app(tmp_path, stage=ApplicationStage.APPLIED)
    _seed_app(tmp_path, stage=ApplicationStage.APPLIED)
    _seed_app(tmp_path, stage=ApplicationStage.SAVED)
    resp = _client(tmp_path).get("/api/applications/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["applied"] == 2
    assert body["saved"] == 1
    assert body["total"] == 3


# ── GET /api/documents ────────────────────────────────────────────────────────


def test_list_documents_empty(tmp_path: Path) -> None:
    resp = _client(tmp_path).get("/api/documents")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_documents_with_data(tmp_path: Path) -> None:
    _seed_doc(tmp_path, title="SWE")
    resp = _client(tmp_path).get("/api/documents")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_list_documents_kind_filter(tmp_path: Path) -> None:
    _seed_doc(tmp_path, kind=DocumentKind.RESUME)
    _seed_doc(tmp_path, kind=DocumentKind.COVER_LETTER)
    resp = _client(tmp_path).get("/api/documents?kind=resume")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["kind"] == "resume"


# ── GET /api/documents/{id}/file ─────────────────────────────────────────────


def test_document_file_not_found_row(tmp_path: Path) -> None:
    resp = _client(tmp_path).get("/api/documents/ghost/file")
    assert resp.status_code == 404


def test_document_file_missing_on_disk(tmp_path: Path) -> None:
    doc = _seed_doc(tmp_path, file_path="/nonexistent/file.pdf")
    resp = _client(tmp_path).get(f"/api/documents/{doc.id}/file")
    assert resp.status_code == 404


def test_document_file_returns_pdf(tmp_path: Path) -> None:
    # Write a fake PDF bytes to disk.
    pdf_path = tmp_path / "fake.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")
    doc = _seed_doc(tmp_path, file_path=str(pdf_path))
    resp = _client(tmp_path).get(f"/api/documents/{doc.id}/file")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"


# ── DELETE /api/documents/{id} ────────────────────────────────────────────────


def test_delete_document(tmp_path: Path) -> None:
    doc = _seed_doc(tmp_path)
    resp = _client(tmp_path).delete(f"/api/documents/{doc.id}")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_delete_document_not_found(tmp_path: Path) -> None:
    resp = _client(tmp_path).delete("/api/documents/ghost")
    assert resp.status_code == 404


def test_delete_document_unlinks_file(tmp_path: Path) -> None:
    pdf = tmp_path / "resume.pdf"
    pdf.write_bytes(b"%PDF fake")
    doc = _seed_doc(tmp_path, file_path=str(pdf))
    assert pdf.exists()
    _client(tmp_path).delete(f"/api/documents/{doc.id}")
    assert not pdf.exists()


# ── Build endpoints persist a GeneratedDocument ───────────────────────────────


def _fake_pdf(*args: object, **_kwargs: object) -> object:  # type: ignore[return]
    """Monkeypatch target: write a stub PDF and return its path.

    Accepts both build_resume_pdf(profile, out) and
    build_cover_letter_pdf(profile, paragraphs, out, ...) signatures by
    treating the last positional argument as the output path.
    """
    from pathlib import Path as _Path

    p = _Path(str(args[-1]))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"%PDF-1.4 stub")
    return p


@pytest.fixture()
def profile_client(tmp_path: Path) -> TestClient:
    """A TestClient with a minimal (non-empty) profile seeded."""
    client = TestClient(
        create_app(profile_path=tmp_path / "profile.yaml", db_path=tmp_path / "j.db"),
    )
    client.put(
        "/api/profile",
        json={"basics": {"name": "Ada"}, "skills": [{"category": "PL", "skills": ["Python"]}]},
    )
    return client


def test_resume_build_persists_document_and_sets_header(
    tmp_path: Path, profile_client: TestClient
) -> None:
    with patch("job_sentinel.documents.build_resume_pdf", side_effect=_fake_pdf):
        resp = profile_client.post("/api/resume/build", json={})

    assert resp.status_code == 200
    doc_id = resp.headers.get("x-document-id")
    assert doc_id, "X-Document-Id header must be set"

    # Verify a DB row was written.
    repo = JobRepository(tmp_path / "j.db")
    doc = repo.get_document(doc_id)
    repo.close()
    assert doc is not None
    assert doc.kind == DocumentKind.RESUME


def test_cover_build_persists_document_and_sets_header(
    tmp_path: Path, profile_client: TestClient
) -> None:
    with patch("job_sentinel.documents.build_cover_letter_pdf", side_effect=_fake_pdf):
        resp = profile_client.post("/api/resume/cover", json={"role": "Intern", "company": "Corp"})

    assert resp.status_code == 200
    doc_id = resp.headers.get("x-document-id")
    assert doc_id, "X-Document-Id header must be set"

    repo = JobRepository(tmp_path / "j.db")
    doc = repo.get_document(doc_id)
    repo.close()
    assert doc is not None
    assert doc.kind == DocumentKind.COVER_LETTER
    assert doc.title == "Intern"
    assert doc.employer == "Corp"
