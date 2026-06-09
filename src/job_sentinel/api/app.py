"""
api/app.py
───────────
A thin, local FastAPI layer over the existing typed core. The web UI is just a
surface over this — there is **no business logic here**, only HTTP plumbing that
calls the same profile/repository/tailor code the CLI uses. That keeps a single
source of truth and means the UI can never drift from the engine.

Run it:
    uv run uvicorn job_sentinel.api.app:app --reload      # or: job-sentinel serve

Local-first: it binds to localhost and only allows local origins, so nothing is
exposed off the machine.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from job_sentinel.core.models import JobPosting
from job_sentinel.documents.tailor import KeywordTailor, TailorResult
from job_sentinel.profile import Profile, load_profile

# data/ lives at the repo root (src/job_sentinel/api/app.py -> parents[3]).
_DATA_DIR = Path(__file__).resolve().parents[3] / "data"

# The local Next.js dev server (and a future packaged UI) call this API.
_LOCAL_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
]


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "job-sentinel-api"


class ProfileSummary(BaseModel):
    name: str
    education: int
    experience: int
    projects: int
    skills: int
    certifications: int
    awards: int
    publications: int


class TailorRequest(BaseModel):
    job_description: str = Field(min_length=1, description="The job text to tailor toward")


def create_app() -> FastAPI:
    """Build the FastAPI app. A factory so tests can construct fresh instances."""
    app = FastAPI(
        title="Job Sentinel API",
        version="0.1.0",
        summary="Local API over the job-sentinel core (profile, jobs, résumé tailoring).",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_LOCAL_ORIGINS,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    @app.get("/api/profile", response_model=Profile)
    def get_profile() -> Profile:
        """The full universal profile (empty if none has been created yet)."""
        return load_profile()

    @app.get("/api/profile/summary", response_model=ProfileSummary)
    def profile_summary() -> ProfileSummary:
        p = load_profile()
        return ProfileSummary(
            name=p.basics.name,
            education=len(p.education),
            experience=len(p.experience),
            projects=len(p.projects),
            skills=len(p.skills),
            certifications=len(p.certifications),
            awards=len(p.awards),
            publications=len(p.publications),
        )

    @app.get("/api/jobs", response_model=list[JobPosting])
    def list_jobs(limit: int = 20) -> list[JobPosting]:
        """Recently discovered postings (empty list if the DB doesn't exist yet)."""
        from job_sentinel.db.repository import JobRepository

        db_path = _DATA_DIR / "jobs.db"
        if not db_path.is_file():
            return []
        repo = JobRepository(db_path)
        try:
            return repo.get_recent_jobs(limit=limit)
        finally:
            repo.close()

    @app.post("/api/resume/tailor", response_model=TailorResult)
    def tailor_resume(req: TailorRequest) -> TailorResult:
        """Tailor the profile to a job description (reorder + ATS coverage). No side effects."""
        return KeywordTailor().tailor(load_profile(), req.job_description)

    return app


app = create_app()
