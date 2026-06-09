"""
__main__.py
────────────
CLI entry-point for Job Sentinel (Typer + Rich).

Commands
────────
  job-sentinel run        — Start the full bot + scheduler (primary command)
  job-sentinel scrape     — Run one scrape cycle and print results (no bot)
  job-sentinel db stats   — Print database statistics
  job-sentinel db list    — List recent jobs from the database
  job-sentinel adapters   — List available site adapters

Usage
─────
  uv run job-sentinel run
  uv run job-sentinel scrape --dry-run
  uv run job-sentinel db stats
"""

from __future__ import annotations

import contextlib
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from job_sentinel.core.models import JobPosting
    from job_sentinel.documents.tailor import Tailor

# Windows terminals default to cp1252, which raises UnicodeEncodeError on the
# ✓/emoji glyphs we print. Force UTF-8 on the standard streams when possible.
for _stream in (sys.stdout, sys.stderr):
    _reconfigure = getattr(_stream, "reconfigure", None)
    if _reconfigure is not None:
        with contextlib.suppress(Exception):
            _reconfigure(encoding="utf-8")

console = Console()
app = typer.Typer(
    name="job-sentinel",
    help="Site-agnostic job portal monitor with Telegram alerts.",
    add_completion=False,
    rich_markup_mode="rich",
)
db_app = typer.Typer(help="Database inspection commands.")
app.add_typer(db_app, name="db")
resume_app = typer.Typer(help="Universal profile + resume generation.")
app.add_typer(resume_app, name="resume")


# ─────────────────────────────────────────────────────────────────────────────
# run — primary command
# ─────────────────────────────────────────────────────────────────────────────


@app.command()
def run(
    dry_run: bool = typer.Option(False, "--dry-run", help="Scrape but don't send Telegram msgs"),
    headless: bool = typer.Option(True, "--headless/--no-headless", help="Browser headless mode"),
) -> None:
    """
    Start Job Sentinel: background scraper + Telegram bot.

    The bot runs until Ctrl+C is pressed.
    """
    import os

    # Allow CLI flags to override .env
    if dry_run:
        os.environ["DRY_RUN"] = "true"
    if not headless:
        os.environ["HEADLESS"] = "false"

    # Import here so settings load after env overrides
    from loguru import logger

    from job_sentinel.bot.handlers import build_application
    from job_sentinel.config.logging import configure_logging
    from job_sentinel.config.settings import get_settings
    from job_sentinel.core.scheduler import Scheduler
    from job_sentinel.db.repository import JobRepository
    from job_sentinel.notifiers.email import EmailNotifier
    from job_sentinel.notifiers.telegram import TelegramNotifier

    settings = get_settings()
    configure_logging(settings.logging)

    if settings.custom_adapter_path:
        from job_sentinel.adapters.registry import load_custom_adapter

        load_custom_adapter(settings.custom_adapter_path)

    logger.info("🚀 Job Sentinel starting | adapter={} env={}", settings.site_adapter, settings.env)

    repo = JobRepository(settings.db_path)
    notifier = TelegramNotifier(settings.telegram.bot_token, settings.telegram.chat_id)
    email = EmailNotifier(settings.email)

    def on_new_jobs(jobs: list[JobPosting]) -> None:
        notifier.send_new_jobs(jobs)
        email.send_new_jobs(jobs)  # no-op unless EMAIL_ENABLED is configured

    scheduler = Scheduler(settings, repo, on_new_jobs)
    bot_app = build_application(settings, repo, scheduler, notifier)

    if email.enabled:
        logger.info("Email channel enabled | recipient={}", settings.email.recipient)

    console.print(
        f"[bold green]✓ Job Sentinel running[/]\n"
        f"  Adapter  : [cyan]{settings.site_adapter}[/]\n"
        f"  Interval : [cyan]{settings.scraper.poll_interval_seconds}s[/]\n"
        f"  Dry run  : [cyan]{settings.dry_run}[/]\n"
        f"  DB       : [cyan]{settings.db_path}[/]\n"
        "Press [bold]Ctrl+C[/] to stop."
    )

    scheduler.start()

    try:
        # run_polling blocks until SIGINT/SIGTERM
        bot_app.run_polling(drop_pending_updates=True)
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down…[/]")
    finally:
        scheduler.stop()
        repo.close()
        logger.info("Job Sentinel stopped cleanly")


# ─────────────────────────────────────────────────────────────────────────────
# scrape — one-shot scrape (no bot)
# ─────────────────────────────────────────────────────────────────────────────


@app.command()
def scrape(
    dry_run: bool = typer.Option(True, "--dry-run/--send", help="Send alerts? (default: dry-run)"),
) -> None:
    """Run a single scrape cycle and print results. Does NOT start the bot."""
    import os

    os.environ["DRY_RUN"] = str(dry_run).lower()

    from job_sentinel.config.logging import configure_logging
    from job_sentinel.config.settings import get_settings
    from job_sentinel.core.scheduler import Scheduler
    from job_sentinel.db.repository import JobRepository
    from job_sentinel.notifiers.telegram import TelegramNotifier

    settings = get_settings()
    configure_logging(settings.logging)

    if settings.custom_adapter_path:
        from job_sentinel.adapters.registry import load_custom_adapter

        load_custom_adapter(settings.custom_adapter_path)

    repo = JobRepository(settings.db_path)
    notifier = TelegramNotifier(settings.telegram.bot_token, settings.telegram.chat_id)
    scheduler = Scheduler(settings, repo, notifier.send_new_jobs)

    console.print(f"[bold]Running one scrape cycle[/] | adapter=[cyan]{settings.site_adapter}[/]")
    new_count = scheduler.trigger_now()
    console.print(f"[green]✓ Done[/] | new jobs found: [bold]{new_count}[/]")
    repo.close()


# ─────────────────────────────────────────────────────────────────────────────
# serve — local HTTP API (backend for the web UI)
# ─────────────────────────────────────────────────────────────────────────────


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Bind address (localhost by default)"),
    port: int = typer.Option(8000, help="Port"),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload on code changes (dev)"),
) -> None:
    """Run the local HTTP API (needs the 'web' extra: pip install -e '.[web]')."""
    try:
        import uvicorn
    except ImportError as exc:
        console.print(
            "[red]The API needs the 'web' extra.[/] Install it: "
            "[bold]uv sync --extra web[/] (or pip install -e '.[web]')."
        )
        raise typer.Exit(code=1) from exc

    console.print(f"[bold green]✓ Job Sentinel API[/] → http://{host}:{port}  (docs at /docs)")
    uvicorn.run("job_sentinel.api.app:app", host=host, port=port, reload=reload)


# ─────────────────────────────────────────────────────────────────────────────
# login — capture an authenticated session (one-time, interactive)
# ─────────────────────────────────────────────────────────────────────────────


@app.command()
def login(
    timeout: int = typer.Option(300, help="Seconds to wait for you to finish signing in"),
) -> None:
    """
    Open a visible browser so you can sign in once, then save the session.

    Portals like 12twenty sit behind a Cloudflare challenge, so the bot can't
    log in headlessly. Sign in here as a human (clear the challenge + enter your
    email/password); the resulting cookies are saved to ``session_path`` and
    reused by ``run``/``scrape`` so they stay logged in.
    """
    from job_sentinel.adapters.registry import get_adapter
    from job_sentinel.config.logging import configure_logging
    from job_sentinel.config.settings import get_settings
    from job_sentinel.core.browser import browser_context

    settings = get_settings()
    configure_logging(settings.logging)

    if settings.custom_adapter_path:
        from job_sentinel.adapters.registry import load_custom_adapter

        load_custom_adapter(settings.custom_adapter_path)

    # Force a visible browser so the user can complete the login + challenge.
    scraper = settings.scraper.model_copy(update={"headless": False})
    adapter = get_adapter(settings.site_adapter, scraper)
    ready = adapter.LOGGED_IN_SELECTOR

    console.print(
        "[bold]A browser window will open.[/] Sign in to the portal "
        "(clear any challenge and enter your email/password).\n"
        "The session saves automatically once your listings appear."
    )

    with browser_context(scraper) as ctx:
        page = ctx.new_page()
        page.goto(settings.portal.jobs_url, wait_until="domcontentloaded")
        if ready:
            try:
                page.wait_for_selector(ready, timeout=timeout * 1000)
            except Exception:
                console.print(
                    "[red]Didn't detect a signed-in page in time.[/] "
                    "Re-run [bold]job-sentinel login[/] and finish signing in."
                )
                return
        else:
            page.wait_for_timeout(timeout * 1000)

        settings.session_path.parent.mkdir(parents=True, exist_ok=True)
        ctx.storage_state(path=str(settings.session_path))

    console.print(f"[green]✓ Session saved[/] → [cyan]{settings.session_path}[/]")


# ─────────────────────────────────────────────────────────────────────────────
# resume — universal profile + PDF generation (works without the bot configured)
# ─────────────────────────────────────────────────────────────────────────────


@resume_app.command("init")
def resume_init(
    force: bool = typer.Option(False, "--force", help="Overwrite an existing profile.yaml"),
) -> None:
    """Create a starter profile.yaml you can edit like an Overleaf source."""
    from job_sentinel.profile import DEFAULT_PROFILE_PATH, example_profile, save_profile

    if DEFAULT_PROFILE_PATH.exists() and not force:
        console.print(
            f"[yellow]Profile already exists[/] at [cyan]{DEFAULT_PROFILE_PATH}[/]. "
            "Use [bold]--force[/] to overwrite."
        )
        return
    path = save_profile(example_profile(), DEFAULT_PROFILE_PATH)
    console.print(f"[green]✓ Wrote starter profile[/] → [cyan]{path}[/]")
    console.print("Edit it, then run [bold]resume build[/].")


@resume_app.command("show")
def resume_show() -> None:
    """Summarise the current profile (section counts)."""
    from job_sentinel.profile import load_profile

    profile = load_profile()
    if profile.is_empty():
        console.print("[yellow]Profile is empty.[/] Run [bold]resume init[/] to start.")
        return

    table = Table(title=f"Profile — {profile.basics.name or 'unnamed'}")
    table.add_column("Section", style="cyan")
    table.add_column("Entries", justify="right")
    table.add_row("Education", str(len(profile.education)))
    table.add_row("Experience", str(len(profile.experience)))
    table.add_row("Projects", str(len(profile.projects)))
    table.add_row("Skill groups", str(len(profile.skills)))
    table.add_row("Certifications", str(len(profile.certifications)))
    table.add_row("Awards", str(len(profile.awards)))
    table.add_row("Publications", str(len(profile.publications)))
    console.print(table)


@resume_app.command("build")
def resume_build(
    out: Path = typer.Option(  # noqa: B008 — typer reads the default at decoration time
        Path("data/resume.pdf"), "--out", "-o", help="Output PDF path"
    ),
    job_text: str = typer.Option("", "--job-text", "-j", help="Tailor to this job description"),
    job_id: str = typer.Option("", "--job-id", help="Tailor to a stored posting (by id)"),
    ai: bool = typer.Option(False, "--ai", help="Rephrase bullets with a local LLM (needs Ollama)"),
) -> None:
    """
    Render the profile to an ATS-friendly PDF (and matching .tex).

    With ``--job-text`` (paste a description) or ``--job-id`` (a posting already
    in the DB), the résumé is tailored: relevant content is reordered to lead
    and an ATS keyword-coverage score is reported. Add ``--ai`` to also rephrase
    bullets with a local model (falls back to keyword tailoring if unavailable).
    """
    from job_sentinel.documents import RenderError, build_resume_pdf
    from job_sentinel.profile import load_profile

    profile = load_profile()
    if profile.is_empty():
        console.print("[yellow]Profile is empty.[/] Run [bold]resume init[/] first.")
        raise typer.Exit(code=1)

    description = job_text or (_load_job_description(job_id) if job_id else "")
    if description:
        tailor = _build_tailor(use_ai=ai)
        result = tailor.tailor(profile, description)
        profile = result.profile
        console.print(f"[bold]ATS keyword coverage:[/] [cyan]{result.score_pct}%[/]")
        if result.missing_keywords:
            preview = ", ".join(result.missing_keywords[:12])
            console.print(f"[yellow]Missing from résumé:[/] {preview}")
    elif ai:
        console.print("[yellow]--ai needs a job to tailor toward; pass --job-text or --job-id.[/]")

    try:
        pdf = build_resume_pdf(profile, out)
    except RenderError as exc:
        console.print(f"[red]Could not build the PDF.[/]\n{exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"[green]✓ Resume built[/] → [cyan]{pdf}[/]")


def _build_tailor(*, use_ai: bool) -> Tailor:
    """Return a Tailor — the local-LLM one if requested (and reachable), else keyword."""
    from job_sentinel.documents import KeywordTailor

    if not use_ai:
        return KeywordTailor()

    from job_sentinel.config.settings import LLMSettings
    from job_sentinel.documents.llm import LLMTailor, OllamaClient

    cfg = LLMSettings()
    client = OllamaClient(cfg.base_url, cfg.model)
    if not client.available():
        console.print(
            "[yellow]Ollama not reachable[/] — using keyword tailoring. "
            "Run [bold]job-sentinel resume doctor[/] to set it up."
        )
        return KeywordTailor()
    if not client.has_model():
        console.print(
            f"[yellow]Model '{cfg.model}' not pulled[/] — using keyword tailoring. "
            f"Run [bold]job-sentinel resume doctor --pull[/]."
        )
        return KeywordTailor()
    console.print(f"[green]Using local model[/] [cyan]{cfg.model}[/] for rephrasing.")
    return LLMTailor(client)


@resume_app.command("doctor")
def resume_doctor(
    pull: bool = typer.Option(False, "--pull", help="Pull the configured model if missing"),
) -> None:
    """Check the local-LLM setup (Ollama) and optionally pull the model."""
    import shutil
    import subprocess

    from job_sentinel.config.settings import LLMSettings
    from job_sentinel.documents.llm import OllamaClient

    cfg = LLMSettings()
    client = OllamaClient(cfg.base_url, cfg.model)
    ollama_bin = shutil.which("ollama")

    table = Table(title="Résumé AI — local model status")
    table.add_column("Check", style="cyan")
    table.add_column("Result")
    table.add_row("ollama installed", "✓" if ollama_bin else "✗  (https://ollama.com/download)")
    reachable = client.available()
    table.add_row("server reachable", f"✓  {cfg.base_url}" if reachable else f"✗  {cfg.base_url}")
    has_model = reachable and client.has_model()
    table.add_row(f"model '{cfg.model}'", "✓ pulled" if has_model else "✗ not pulled")
    console.print(table)

    if not ollama_bin:
        console.print("Install Ollama, then run [bold]ollama serve[/] and re-check.")
        return
    if not reachable:
        console.print("Start the server with [bold]ollama serve[/], then re-check.")
        return
    if not has_model:
        if pull:
            console.print(f"Pulling [cyan]{cfg.model}[/] (multi-GB; one-time)…")
            subprocess.run([ollama_bin, "pull", cfg.model], check=False)  # noqa: S603 — fixed argv, PATH-resolved
        else:
            console.print(f"Pull it with [bold]ollama pull {cfg.model}[/] or rerun with --pull.")
        return
    console.print('[green]✓ Ready[/] — use [bold]resume build --ai --job-text "…"[/].')


def _load_job_description(posting_id: str) -> str:
    """Fetch a stored posting and flatten it into a description for tailoring."""
    from job_sentinel.db.repository import JobRepository

    db_path = Path(__file__).resolve().parents[2] / "data" / "jobs.db"
    if not db_path.is_file():
        console.print(f"[yellow]No database yet[/] at {db_path}; run a scrape first.")
        return ""
    repo = JobRepository(db_path)
    try:
        job = repo.get_job(posting_id)
    finally:
        repo.close()
    if job is None:
        console.print(f"[yellow]Posting {posting_id} not found in the DB.[/]")
        return ""
    return " ".join([job.title, job.employer, job.job_type, job.description_snippet])


# ─────────────────────────────────────────────────────────────────────────────
# db stats / list
# ─────────────────────────────────────────────────────────────────────────────


@db_app.command("stats")
def db_stats() -> None:
    """Print aggregate job counts from the database."""
    from job_sentinel.config.settings import get_settings
    from job_sentinel.db.repository import JobRepository

    settings = get_settings()
    repo = JobRepository(settings.db_path)
    counts = repo.get_stats()
    repo.close()

    table = Table(title="Job Sentinel — DB Stats", show_header=True)
    table.add_column("Status", style="cyan")
    table.add_column("Count", justify="right")
    for key, val in counts.items():
        table.add_row(key, str(val))
    console.print(table)


@db_app.command("list")
def db_list(limit: int = typer.Option(10, help="Number of recent jobs to show")) -> None:
    """List recent jobs from the database."""
    from job_sentinel.config.settings import get_settings
    from job_sentinel.db.repository import JobRepository

    settings = get_settings()
    repo = JobRepository(settings.db_path)
    jobs = repo.get_recent_jobs(limit=limit)
    repo.close()

    if not jobs:
        console.print("[yellow]No jobs in database yet.[/]")
        return

    table = Table(title=f"Last {len(jobs)} Jobs", show_header=True)
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Title", style="bold")
    table.add_column("Employer")
    table.add_column("Status", style="cyan")
    table.add_column("Found")

    for job in jobs:
        table.add_row(
            job.posting_id[:12],
            job.title[:40],
            job.employer[:25],
            job.status.value,
            job.discovered_at.strftime("%m-%d %H:%M"),
        )
    console.print(table)


# ─────────────────────────────────────────────────────────────────────────────
# adapters list
# ─────────────────────────────────────────────────────────────────────────────


@app.command()
def adapters() -> None:
    """List all available site adapters."""
    from job_sentinel.adapters.registry import list_adapters
    from job_sentinel.config.settings import get_settings

    settings = get_settings()
    active = settings.site_adapter
    ids = list_adapters()

    table = Table(title="Available Site Adapters")
    table.add_column("ID", style="cyan")
    table.add_column("Active", justify="center")
    for aid in ids:
        table.add_row(aid, "✓" if aid == active else "")
    console.print(table)


# ─────────────────────────────────────────────────────────────────────────────
# Entry-point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app()
