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
exposed off the machine. ``create_app`` takes optional profile/DB paths so tests
never touch the user's real ``data/`` files.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from job_sentinel.core.models import ApplicationStatus, JobPosting
from job_sentinel.documents.tailor import KeywordTailor, TailorResult
from job_sentinel.profile import DEFAULT_PROFILE_PATH, Profile, load_profile, save_profile

if TYPE_CHECKING:
    from job_sentinel.documents.tailor import Tailor

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


class BuildRequest(BaseModel):
    job_description: str = Field(default="", description="Optional JD to tailor toward")
    ai: bool = Field(default=False, description="Use the local LLM to rephrase (if available)")


class StatusRequest(BaseModel):
    status: ApplicationStatus


def _summary(p: Profile) -> ProfileSummary:
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


def create_app(
    profile_path: Path | None = None,
    db_path: Path | None = None,
) -> FastAPI:
    """Build the FastAPI app. Paths are injectable so tests stay isolated."""
    profile_path = profile_path or DEFAULT_PROFILE_PATH
    db_path = db_path or (_DATA_DIR / "jobs.db")

    app = FastAPI(
        title="Job Sentinel API",
        version="0.2.0",
        summary="Local API over the job-sentinel core (profile, jobs, résumé tailoring).",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_LOCAL_ORIGINS,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    @app.get("/api/profile", response_model=Profile)
    def get_profile() -> Profile:
        return load_profile(profile_path)

    @app.put("/api/profile", response_model=Profile)
    def put_profile(profile: Profile) -> Profile:
        """Replace the stored profile (validated by pydantic) and persist it."""
        save_profile(profile, profile_path)
        return profile

    @app.get("/api/profile/summary", response_model=ProfileSummary)
    def profile_summary() -> ProfileSummary:
        return _summary(load_profile(profile_path))

    @app.get("/api/jobs", response_model=list[JobPosting])
    def list_jobs(limit: int = 20) -> list[JobPosting]:
        from job_sentinel.db.repository import JobRepository

        if not db_path.is_file():
            return []
        repo = JobRepository(db_path)
        try:
            return repo.get_recent_jobs(limit=limit)
        finally:
            repo.close()

    @app.post("/api/jobs/{posting_id}/status", response_model=JobPosting)
    def set_job_status(posting_id: str, req: StatusRequest) -> JobPosting:
        from job_sentinel.db.repository import JobRepository

        if not db_path.is_file():
            raise HTTPException(status_code=404, detail="No job database yet")
        repo = JobRepository(db_path)
        try:
            if not repo.update_status(posting_id, req.status):
                raise HTTPException(status_code=404, detail=f"Posting {posting_id} not found")
            job = repo.get_job(posting_id)
        finally:
            repo.close()
        if job is None:  # pragma: no cover - defensive
            raise HTTPException(status_code=404, detail=f"Posting {posting_id} not found")
        return job

    @app.post("/api/resume/tailor", response_model=TailorResult)
    def tailor_resume(req: TailorRequest) -> TailorResult:
        return KeywordTailor().tailor(load_profile(profile_path), req.job_description)

    @app.post("/api/resume/build")
    def build_resume(req: BuildRequest) -> FileResponse:
        """Render a PDF and return it. 503 if the LaTeX engine isn't installed."""
        from job_sentinel.documents import RenderError, build_resume_pdf

        profile = load_profile(profile_path)
        if profile.is_empty():
            raise HTTPException(status_code=400, detail="Profile is empty; create one first.")

        if req.job_description:
            tailor = _resolve_tailor(use_ai=req.ai)
            profile = tailor.tailor(profile, req.job_description).profile

        out = _DATA_DIR / "resume_api.pdf"
        try:
            pdf = build_resume_pdf(profile, out)
        except RenderError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return FileResponse(pdf, media_type="application/pdf", filename="resume.pdf")

    return app


def _resolve_tailor(*, use_ai: bool) -> Tailor:
    """Pick the LLM tailor if requested and reachable, else the keyword tailor."""
    base: Tailor = KeywordTailor()
    if not use_ai:
        return base
    from job_sentinel.config.settings import LLMSettings
    from job_sentinel.documents.llm import LLMTailor, OllamaClient

    cfg = LLMSettings()
    client = OllamaClient(cfg.base_url, cfg.model)
    if client.available() and client.has_model():
        return LLMTailor(client)
    return base


app = create_app()
