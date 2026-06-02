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

import typer
from rich.console import Console
from rich.table import Table

console = Console()
app = typer.Typer(
    name="job-sentinel",
    help="Site-agnostic job portal monitor with Telegram alerts.",
    add_completion=False,
    rich_markup_mode="rich",
)
db_app = typer.Typer(help="Database inspection commands.")
app.add_typer(db_app, name="db")


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
    from job_sentinel.notifiers.telegram import TelegramNotifier

    settings = get_settings()
    configure_logging(settings.logging)

    if settings.custom_adapter_path:
        from job_sentinel.adapters.registry import load_custom_adapter

        load_custom_adapter(settings.custom_adapter_path)

    logger.info("🚀 Job Sentinel starting | adapter={} env={}", settings.site_adapter, settings.env)

    repo = JobRepository(settings.db_path)
    notifier = TelegramNotifier(settings.telegram.bot_token, settings.telegram.chat_id)
    scheduler = Scheduler(settings, repo, notifier.send_new_jobs)
    bot_app = build_application(settings, repo, scheduler, notifier)

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
