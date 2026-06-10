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
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from job_sentinel.api.chat import ChatMessage, ChatReply
from job_sentinel.api.chat import answer as chat_answer
from job_sentinel.api.ops import OpsConfigError, OpsConflictError, get_runner
from job_sentinel.core.models import ApplicationStatus, JobPosting
from job_sentinel.documents.tailor import KeywordTailor, TailorResult
from job_sentinel.profile import DEFAULT_PROFILE_PATH, Profile, load_profile, save_profile

if TYPE_CHECKING:
    from job_sentinel.documents.llm import OllamaClient
    from job_sentinel.documents.tailor import Tailor

# data/ lives at the repo root (src/job_sentinel/api/app.py -> parents[3]).
_DATA_DIR = Path(__file__).resolve().parents[3] / "data"

# The local Next.js dev server (and a future packaged UI) call this API.
# Next picks the next free port when 3000 is taken, so accept any localhost
# port rather than a fixed list — the API still only binds to 127.0.0.1.
_LOCAL_ORIGIN_REGEX = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"


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


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=40)


class LoginRequest(BaseModel):
    timeout: int = Field(default=300, ge=30, le=900, description="Seconds to wait for sign-in")


class ScrapeRequest(BaseModel):
    send: bool = Field(default=False, description="Send alerts (default: dry run)")


class CoverRequest(BaseModel):
    job_description: str = Field(default="", description="Optional JD to target")
    role: str = Field(default="", description="Role title for the opening line")
    company: str = Field(default="", description="Company / department name")
    ai: bool = Field(default=False, description="Polish with the local LLM (if available)")


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
        allow_origin_regex=_LOCAL_ORIGIN_REGEX,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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

    @app.get("/api/stats")
    def db_stats() -> dict[str, int]:
        """Counts per tracking status — the UI twin of `job-sentinel db stats`."""
        from job_sentinel.db.repository import JobRepository

        if not db_path.is_file():
            return {}
        repo = JobRepository(db_path)
        try:
            return repo.get_stats()
        finally:
            repo.close()

    @app.get("/api/ops/status")
    def ops_status() -> dict[str, Any]:
        """Session/login/scrape/watcher state in one snapshot (polled by the UI)."""
        return get_runner().status()

    @app.post("/api/ops/login")
    def ops_login(req: LoginRequest) -> dict[str, bool]:
        """Start the interactive portal login (opens a browser on this machine)."""
        try:
            get_runner().start_login(timeout=req.timeout)
        except OpsConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except OpsConfigError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return {"started": True}

    @app.post("/api/ops/scrape")
    def ops_scrape(req: ScrapeRequest) -> dict[str, bool]:
        """Run one scrape cycle in the background (dry-run unless `send`)."""
        try:
            get_runner().start_scrape(send=req.send)
        except OpsConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except OpsConfigError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return {"started": True}

    @app.post("/api/ops/watcher/start")
    def ops_watcher_start() -> dict[str, bool]:
        """Start continuous monitoring (the UI twin of `job-sentinel run`)."""
        try:
            get_runner().start_watcher()
        except OpsConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except OpsConfigError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return {"running": True}

    @app.post("/api/ops/watcher/stop")
    def ops_watcher_stop() -> dict[str, bool]:
        """Stop continuous monitoring."""
        try:
            get_runner().stop_watcher()
        except OpsConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"running": False}

    @app.get("/api/llm/status")
    def llm_status() -> dict[str, Any]:
        """Local-LLM health — the UI twin of `job-sentinel resume doctor`."""
        from job_sentinel.config.settings import LLMSettings
        from job_sentinel.documents.embeddings import OllamaEmbedder
        from job_sentinel.documents.llm import OllamaClient

        cfg = LLMSettings()
        client = OllamaClient(cfg.base_url, cfg.model)
        reachable = client.available()
        return {
            "base_url": cfg.base_url,
            "reachable": reachable,
            "chat_model": cfg.model,
            "chat_ready": reachable and client.has_model(),
            "embed_model": cfg.embed_model,
            "embed_ready": reachable and OllamaEmbedder(cfg.base_url, cfg.embed_model).available(),
        }

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

    @app.post("/api/chat", response_model=ChatReply)
    def chat(req: ChatRequest) -> ChatReply:
        """The Sentinel assistant: data questions answered from real state, rest via local LLM."""
        if req.messages[-1].role != "user":
            raise HTTPException(status_code=422, detail="The last message must be from the user.")
        return chat_answer(
            req.messages,
            profile_path=profile_path,
            db_path=db_path,
            client_factory=_resolve_ollama,
        )

    @app.post("/api/resume/cover")
    def build_cover(req: CoverRequest) -> FileResponse:
        """Render a cover-letter PDF. 503 if the LaTeX engine isn't installed."""
        from datetime import date

        from job_sentinel.documents import (
            RenderError,
            build_cover_letter_pdf,
            cover_letter_paragraphs,
        )

        profile = load_profile(profile_path)
        if profile.is_empty():
            raise HTTPException(status_code=400, detail="Profile is empty; create one first.")

        client = _resolve_ollama() if req.ai else None
        paragraphs = cover_letter_paragraphs(
            profile,
            role=req.role,
            company=req.company,
            job_description=req.job_description,
            client=client,
        )
        out = _DATA_DIR / "cover_api.pdf"
        try:
            pdf = build_cover_letter_pdf(
                profile,
                paragraphs,
                out,
                role=req.role,
                company=req.company,
                today=date.today().strftime("%B %d, %Y"),
            )
        except RenderError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return FileResponse(pdf, media_type="application/pdf", filename="cover_letter.pdf")

    return app


def _resolve_ollama() -> OllamaClient | None:
    """Return a ready OllamaClient if reachable with the model pulled, else None."""
    from job_sentinel.config.settings import LLMSettings
    from job_sentinel.documents.llm import OllamaClient

    cfg = LLMSettings()
    client = OllamaClient(cfg.base_url, cfg.model)
    return client if (client.available() and client.has_model()) else None


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
