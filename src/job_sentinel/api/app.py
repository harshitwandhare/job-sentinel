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

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
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


class AuthLoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class AuthCreateUserRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=8, description="At least 8 characters")
    is_admin: bool = False


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
    auth_dir: Path | None = None,
) -> FastAPI:
    """Build the FastAPI app. Paths are injectable so tests stay isolated."""
    profile_path = profile_path or DEFAULT_PROFILE_PATH
    db_path = db_path or (_DATA_DIR / "jobs.db")
    auth_dir = auth_dir or _DATA_DIR

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

    # ── Authentication (AUTH_MODE: off | demo | required) ─────────────────
    import os

    from job_sentinel.api.auth import AuthError, TokenIssuer, User, UserStore

    auth_mode = os.environ.get("AUTH_MODE", "off").strip().lower()
    if auth_mode not in ("off", "demo", "required"):
        auth_mode = "off"
    user_store = UserStore(auth_dir / "users.json")
    token_issuer = TokenIssuer(auth_dir / "auth_secret")

    def _bearer_user(request: Request) -> User | None:
        header = request.headers.get("authorization", "")
        if not header.lower().startswith("bearer "):
            return None
        try:
            return token_issuer.verify(header[7:].strip())
        except AuthError:
            return None

    # Paths that never need a token (health, docs, and the auth flow itself).
    _public_paths = ("/health", "/docs", "/openapi.json", "/api/auth/")

    @app.middleware("http")
    async def auth_gate(request: Request, call_next):  # type: ignore[no-untyped-def]
        """demo: writes need a login · required: everything needs a login."""
        path = request.url.path
        if (
            auth_mode == "off"
            or request.method == "OPTIONS"
            or any(path.startswith(p) for p in _public_paths)
            or (auth_mode == "demo" and request.method in ("GET", "HEAD"))
        ):
            return await call_next(request)
        user = _bearer_user(request)
        if user is None:
            return JSONResponse(
                status_code=401,
                content={"detail": "Login required — POST /api/auth/login for a token."},
            )
        request.state.user = user
        return await call_next(request)

    @app.get("/api/auth/status")
    def auth_status(request: Request) -> dict[str, Any]:
        user = _bearer_user(request)
        return {
            "mode": auth_mode,
            "users_exist": user_store.has_users(),
            "user": user.model_dump() if user else None,
        }

    @app.post("/api/auth/login")
    def auth_login(req: AuthLoginRequest) -> dict[str, Any]:
        try:
            user = user_store.authenticate(req.username, req.password)
        except AuthError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        return {"token": token_issuer.issue(user), "user": user.model_dump()}

    @app.post("/api/auth/users")
    def auth_create_user(req: AuthCreateUserRequest, request: Request) -> dict[str, Any]:
        """Admin-only: create an account (how you invite someone to your instance)."""
        actor = _bearer_user(request)
        if user_store.has_users() and (actor is None or not actor.is_admin):
            raise HTTPException(status_code=403, detail="Only an admin can create accounts.")
        try:
            user = user_store.add_user(
                req.username,
                req.password,
                is_admin=req.is_admin if user_store.has_users() else True,
            )
        except AuthError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"user": user.model_dump()}

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

    @app.post("/api/profile/import-resume", response_model=Profile)
    async def import_resume(file: UploadFile, ai: bool = True) -> Profile:
        """
        Parse an uploaded resume PDF into a Profile **draft**.

        Nothing is saved — the UI loads the result into the editor so the
        user reviews and saves explicitly. ``ai=true`` (default) uses the
        local LLM when available; otherwise the heuristic parser runs.
        """
        from job_sentinel.documents.resume_import import (
            ResumeImportError,
            extract_pdf_text,
            parse_resume_text,
        )

        if file.content_type not in ("application/pdf", "application/octet-stream", None):
            raise HTTPException(status_code=415, detail="Upload a PDF file.")
        data = await file.read()
        if len(data) > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="PDF is larger than 10 MB.")
        try:
            text = extract_pdf_text(data)
        except ResumeImportError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        client = _resolve_ollama() if ai else None
        return parse_resume_text(text, client=client)

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

    @app.post("/api/ops/session/check")
    def ops_session_check() -> dict[str, Any]:
        """Headless probe: is the saved portal session still valid?"""
        try:
            return get_runner().check_session()
        except OpsConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except OpsConfigError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

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
        """
        LLM provider health snapshot.

        Legacy keys (base_url, reachable, chat_model, chat_ready,
        embed_model, embed_ready) are preserved for the existing web UI.
        New keys (chat, embed sub-objects) expose the provider detail.
        """
        from job_sentinel.config.settings import LLMSettings
        from job_sentinel.documents.providers import build_chat_backend, build_embed_backend

        cfg = LLMSettings()
        chat_be = build_chat_backend(cfg)
        embed_be = build_embed_backend(cfg)

        chat_reachable = chat_be.available()
        chat_ready = chat_be.ready()
        embed_reachable = embed_be.available()
        embed_ready = embed_be.ready()

        # Legacy keys — do NOT remove (web/studio uses them).
        legacy_base = cfg.chat_base_url_resolved
        return {
            "base_url": legacy_base,
            "reachable": chat_reachable,
            "chat_model": cfg.chat_model_resolved,
            "chat_ready": chat_ready,
            "embed_model": cfg.embed_model_resolved,
            "embed_ready": embed_ready,
            # New keys for the richer UI panel.
            "chat": {
                "provider": cfg.chat_provider,
                "model": cfg.chat_model_resolved,
                "base_url": cfg.chat_base_url_resolved,
                "reachable": chat_reachable,
                "ready": chat_ready,
            },
            "embed": {
                "provider": cfg.embed_provider,
                "model": cfg.embed_model_resolved,
                "base_url": cfg.embed_base_url_resolved,
                "reachable": embed_reachable,
                "ready": embed_ready,
            },
        }

    @app.get("/api/llm/config")
    def llm_config() -> dict[str, Any]:
        """Return current LLM config (API keys masked, never raw)."""
        from job_sentinel.config.settings import LLMSettings
        from job_sentinel.documents.providers import PROVIDER_DEFAULTS

        cfg = LLMSettings()
        return {
            "chat": {
                "provider": cfg.chat_provider,
                "model": cfg.chat_model_resolved,
                "base_url": cfg.chat_base_url_resolved,
                "api_key_set": bool(cfg.chat_api_key),
                "api_key_masked": _mask_key(cfg.chat_api_key),
            },
            "embed": {
                "provider": cfg.embed_provider,
                "model": cfg.embed_model_resolved,
                "base_url": cfg.embed_base_url_resolved,
                "api_key_set": bool(cfg.embed_api_key),
                "api_key_masked": _mask_key(cfg.embed_api_key),
            },
            "providers": [
                {
                    "id": pid,
                    "label": info.label,
                    "default_base_url": info.base_url,
                    "requires_key": info.requires_key,
                    "supports_embeddings": info.supports_embeddings,
                }
                for pid, info in PROVIDER_DEFAULTS.items()
            ],
        }

    class _LLMSideInput(BaseModel):
        provider: str = ""
        model: str = ""
        base_url: str = ""
        api_key: str | None = None  # None = leave unchanged; "" = clear

    class LLMConfigPutRequest(BaseModel):
        chat: _LLMSideInput = _LLMSideInput()
        embed: _LLMSideInput = _LLMSideInput()

    class LLMTestRequest(BaseModel):
        target: str  # "chat" | "embed"

    @app.put("/api/llm/config")
    def llm_config_put(req: LLMConfigPutRequest, request: Request) -> dict[str, Any]:
        """
        Persist LLM provider settings to .env (atomic write).

        Only the LLM-related keys are touched; unrelated lines are preserved.
        Clears the settings cache so the next request picks up the new values.
        """
        # Require auth for mutating config when auth is enabled.
        if auth_mode != "off" and _bearer_user(request) is None:
            raise HTTPException(status_code=401, detail="Login required to change LLM config.")
        updates: dict[str, str] = {}
        if req.chat.provider:
            updates["CHAT_PROVIDER"] = req.chat.provider
        if req.chat.model:
            updates["CHAT_MODEL"] = req.chat.model
        if req.chat.base_url is not None:
            updates["CHAT_BASE_URL"] = req.chat.base_url
        if req.chat.api_key is not None:
            updates["CHAT_API_KEY"] = req.chat.api_key

        if req.embed.provider:
            updates["EMBED_PROVIDER"] = req.embed.provider
        if req.embed.model:
            updates["EMBED_MODEL"] = req.embed.model
        if req.embed.base_url is not None:
            updates["EMBED_BASE_URL"] = req.embed.base_url
        if req.embed.api_key is not None:
            updates["EMBED_API_KEY"] = req.embed.api_key

        _update_env_file(updates)

        from job_sentinel.config.settings import get_settings

        get_settings.cache_clear()
        return llm_config()

    @app.post("/api/llm/test")
    def llm_test(req: LLMTestRequest, request: Request) -> dict[str, Any]:
        """
        Live test of the configured chat or embed backend.

        Builds the backend from the current saved config, makes a minimal
        call, and returns {ok, detail, latency_ms}.  Never exposes secrets
        in the detail message.
        """
        import time

        if auth_mode != "off" and _bearer_user(request) is None:
            raise HTTPException(status_code=401, detail="Login required to test LLM config.")
        from job_sentinel.config.settings import LLMSettings
        from job_sentinel.documents.providers import build_chat_backend, build_embed_backend

        cfg = LLMSettings()
        start = time.monotonic()
        try:
            if req.target == "chat":
                backend = build_chat_backend(cfg)
                if not backend.available():
                    return {"ok": False, "detail": "Backend not reachable.", "latency_ms": None}
                backend.chat(
                    "You are a test assistant.", [{"role": "user", "content": "Say 'ok'."}]
                )
            elif req.target == "embed":
                backend_e = build_embed_backend(cfg)
                if not backend_e.available():
                    return {
                        "ok": False,
                        "detail": "Embed backend not reachable.",
                        "latency_ms": None,
                    }
                backend_e.embed(["ping"])
            else:
                return {
                    "ok": False,
                    "detail": "target must be 'chat' or 'embed'.",
                    "latency_ms": None,
                }
        except Exception as exc:
            # Never include the exception repr directly — it could contain API key fragments.
            safe = type(exc).__name__
            return {"ok": False, "detail": f"Request failed: {safe}", "latency_ms": None}
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return {"ok": True, "detail": "ok", "latency_ms": elapsed_ms}

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
    """
    Return a ready chat backend as an OllamaClient-compatible object, or None.

    Uses the multi-provider factory so this path benefits from CHAT_PROVIDER /
    CHAT_MODEL overrides while remaining backward-compatible with callers that
    only need available() / has_model() / chat() / chat_json().
    """
    from job_sentinel.config.settings import LLMSettings
    from job_sentinel.documents.providers import build_chat_backend

    cfg = LLMSettings()
    backend = build_chat_backend(cfg)
    return backend if (backend.available() and backend.ready()) else None  # type: ignore[return-value]


def _resolve_tailor(*, use_ai: bool) -> Tailor:
    """Pick the LLM tailor if requested and reachable, else the keyword tailor."""
    base: Tailor = KeywordTailor()
    if not use_ai:
        return base
    from job_sentinel.config.settings import LLMSettings
    from job_sentinel.documents.llm import LLMTailor
    from job_sentinel.documents.providers import build_chat_backend

    cfg = LLMSettings()
    backend = build_chat_backend(cfg)
    if backend.available() and backend.ready():
        return LLMTailor(backend)
    return base


def _mask_key(key: str) -> str:
    """Return a masked representation: 'sk-…XXXX' or '' if unset."""
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return key[:3] + "…" + key[-4:]


def _update_env_file(updates: dict[str, str]) -> None:
    """
    Atomically update or append LLM-related keys in the .env file.

    Reads the existing file, updates only the specified keys, then writes
    via a temp-file + rename to avoid partial writes.  Lines for unrelated
    keys are preserved verbatim.
    """
    import os
    import tempfile

    from job_sentinel.config.settings import _ENV_FILE

    env_path = Path(_ENV_FILE)
    existing_lines: list[str] = []
    if env_path.is_file():
        existing_lines = env_path.read_text(encoding="utf-8").splitlines(keepends=True)

    remaining = dict(updates)  # keys still to be written
    new_lines: list[str] = []
    for line in existing_lines:
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            new_lines.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in remaining:
            new_lines.append(f"{key}={remaining.pop(key)}\n")
        else:
            new_lines.append(line)

    # Append any keys that weren't already in the file.
    for key, value in remaining.items():
        new_lines.append(f"{key}={value}\n")

    # Atomic write via temp file in the same directory.
    fd, tmp = tempfile.mkstemp(dir=env_path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.writelines(new_lines)
        Path(tmp).replace(env_path)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


app = create_app()
