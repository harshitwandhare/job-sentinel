"""
bot/handlers.py
────────────────
Async Telegram bot command handlers (python-telegram-bot v21).

Commands
────────
  /start   /help    — Welcome message and command reference
  /jobs            — Trigger on-demand scrape + show latest listings
  /recent          — Show last 10 jobs from DB (no scrape)
  /applied <id>    — Mark posting as applied
  /ignore  <id>    — Dismiss posting
  /status  <id>    — Full details of a specific posting
  /stats           — Aggregate counts by status
  /filters         — Show active keyword filters
  /adapters        — List available site adapters
  /ping            — Health check

Handler design
──────────────
  • Thin handlers — validate input, delegate to repo/scheduler, format reply
  • No business logic here
  • All handlers are closures over shared services (DI without a framework)
  • Use ``build_application()`` to get a fully wired ``Application`` instance
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, ContextTypes

from job_sentinel.adapters.registry import list_adapters
from job_sentinel.core.models import ApplicationStatus
from job_sentinel.notifiers.telegram import TelegramNotifier, escape

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from job_sentinel.config.settings import Settings
    from job_sentinel.core.scheduler import Scheduler
    from job_sentinel.db.repository import JobRepository

    # python-telegram-bot's Application is generic over six type parameters.
    # We don't customise any of them, so alias the fully-defaulted form once.
    BotApplication = Application[Any, Any, Any, Any, Any, Any]
    HandlerFn = Callable[[Update, ContextTypes.DEFAULT_TYPE], Coroutine[Any, Any, None]]

_MAX_LIST = 10  # max jobs per /jobs or /recent response


async def _reply(update: Update, text: str) -> None:
    """
    Reply with MarkdownV2, guarding against a missing message.

    ``update.message`` is ``Optional`` — it is ``None`` for edited messages,
    channel posts, and other update types we don't serve. We simply no-op in
    those cases rather than raising.
    """
    if update.message is not None:
        await update.message.reply_text(text, parse_mode="MarkdownV2")


# ─────────────────────────────────────────────────────────────────────────────
# Application builder
# ─────────────────────────────────────────────────────────────────────────────


def build_application(
    settings: Settings,
    repo: JobRepository,
    scheduler: Scheduler,
    notifier: TelegramNotifier,
) -> BotApplication:
    """
    Build and return a fully configured ``python-telegram-bot`` Application.

    All command handlers are registered here.  The caller runs the bot with
    ``application.run_polling()``.
    """
    app = Application.builder().token(settings.telegram.bot_token).build()

    # Set bot commands (shows up in Telegram's "/" menu)
    async def post_init(application: BotApplication) -> None:
        await application.bot.set_my_commands(
            [
                BotCommand("start", "Welcome & help"),
                BotCommand("jobs", "Trigger scrape + show recent"),
                BotCommand("recent", "Last 10 jobs from DB"),
                BotCommand("applied", "Mark as applied: /applied <id>"),
                BotCommand("ignore", "Dismiss posting: /ignore <id>"),
                BotCommand("status", "Job details: /status <id>"),
                BotCommand("stats", "Counts by status"),
                BotCommand("filters", "Active keyword filters"),
                BotCommand("adapters", "Available site adapters"),
                BotCommand("ping", "Health check"),
            ]
        )

    app.post_init = post_init

    # ── Build handler closures ────────────────────────────────────────────
    handlers = _make_handlers(settings, repo, scheduler, notifier)
    for command, handler_fn in handlers.items():
        app.add_handler(CommandHandler(command, handler_fn))

    return app


# ─────────────────────────────────────────────────────────────────────────────
# Handler factory
# ─────────────────────────────────────────────────────────────────────────────


def _make_handlers(
    settings: Settings,
    repo: JobRepository,
    scheduler: Scheduler,
    notifier: TelegramNotifier,
) -> dict[str, HandlerFn]:
    """Build all command handler coroutines as closures."""

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = (
            "👋 *Job Sentinel* is online\\!\n\n"
            "I monitor job portals and alert you the moment new postings appear\\.\n\n"
            "*Commands:*\n"
            "/jobs — Trigger a fresh scrape \\+ show recent\n"
            "/recent — Show last 10 jobs from database\n"
            "/applied `<id>` — Mark posting as applied\n"
            "/ignore `<id>` — Dismiss a posting\n"
            "/status `<id>` — Full details of a posting\n"
            "/stats — Summary counts by status\n"
            "/filters — Your active keyword filters\n"
            "/adapters — Available site adapters\n"
            "/ping — Health check\n"
        )
        await _reply(update, text)

    async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await _reply(update, "🟢 Sentinel is alive and watching\\.")

    async def jobs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await _reply(update, "🔍 Triggering a fresh scrape\\.\\.\\. \\(30\\-60 seconds\\)")
        try:
            new_count = scheduler.trigger_now()
        except Exception as exc:
            await _reply(update, f"❌ Scrape failed: `{escape(str(exc))}`")
            return

        recent = repo.get_recent_jobs(limit=_MAX_LIST)
        header = f"✅ Scrape done — {new_count} new posting(s)\\. Showing last {len(recent)}:"
        notifier.send_jobs_list(recent, header=header)

    async def recent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        jobs_list = repo.get_recent_jobs(limit=_MAX_LIST)
        if not jobs_list:
            await _reply(update, "📭 No jobs yet\\. Run /jobs to trigger a scrape\\.")
            return
        notifier.send_jobs_list(jobs_list, header=f"📋 Last {len(jobs_list)} discovered:")

    async def applied(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        pid = _arg(context)
        if not pid:
            await _reply(update, "Usage: `/applied <posting_id>`")
            return
        ok = repo.update_status(pid, ApplicationStatus.APPLIED)
        msg = (
            f"✅ `{escape(pid)}` marked as *applied*\\. Good luck\\! 🤞"
            if ok
            else f"❓ Posting `{escape(pid)}` not found\\."
        )
        await _reply(update, msg)

    async def ignore(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        pid = _arg(context)
        if not pid:
            await _reply(update, "Usage: `/ignore <posting_id>`")
            return
        ok = repo.update_status(pid, ApplicationStatus.IGNORED)
        msg = (
            f"🚫 `{escape(pid)}` marked as *ignored*\\."
            if ok
            else f"❓ Posting `{escape(pid)}` not found\\."
        )
        await _reply(update, msg)

    async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        pid = _arg(context)
        if not pid:
            await _reply(update, "Usage: `/status <posting_id>`")
            return
        job = repo.get_job(pid)
        if not job:
            await _reply(update, f"❓ `{escape(pid)}` not found\\.")
            return

        status_emoji = {
            "new": "🆕",
            "seen": "👁",
            "applied": "✅",
            "ignored": "🚫",
            "closed": "🔒",
        }.get(job.status.value, "❓")

        lines = [
            f"*{escape(job.title)}*",
            "",
            f"🏢 {escape(job.employer or 'N/A')}",
            f"📍 {escape(job.location or 'N/A')}",
            f"🕐 {escape(job.job_type or 'N/A')}",
            f"📅 Posted: {escape(job.posted_date or 'N/A')}",
            f"⏳ Deadline: {escape(job.deadline or 'N/A')}",
            "",
            f"{status_emoji} Status: *{escape(job.status.value)}*",
            f"🔌 Adapter: `{escape(job.source_adapter)}`",
            f"🔍 Found: {escape(job.discovered_at.strftime('%Y-%m-%d %H:%M UTC'))}",
            "",
        ]
        if job.description_snippet:
            lines.append(f"_{escape(job.description_snippet[:300])}_")
            lines.append("")
        lines.append(f"[View on Portal →]({escape(job.portal_url)})")

        await _reply(update, "\n".join(lines))

    async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        counts = repo.get_stats()
        lines = [
            "📊 *Job Tracking Stats*",
            "",
            f"🆕 New:     `{counts.get('new', 0)}`",
            f"👁 Seen:    `{counts.get('seen', 0)}`",
            f"✅ Applied: `{counts.get('applied', 0)}`",
            f"🚫 Ignored: `{counts.get('ignored', 0)}`",
            f"🔒 Closed:  `{counts.get('closed', 0)}`",
            "",
            f"📋 Total tracked: `{counts.get('total', 0)}`",
            f"🔌 Adapter: `{escape(settings.site_adapter)}`",
        ]
        await _reply(update, "\n".join(lines))

    async def filters_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        kws = settings.filters.keyword_filters
        if not kws:
            await _reply(
                update,
                "🔓 No filters — all postings are tracked\\.\n"
                "Set `KEYWORD_FILTERS` in \\.env to narrow results\\.",
            )
        else:
            kw_list = "\n".join(f"  • `{escape(k)}`" for k in kws)
            await _reply(update, f"🏷 *Active keyword filters:*\n{kw_list}")

    async def adapters_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        ids = list_adapters()
        active = settings.site_adapter
        lines = ["🔌 *Available adapters:*", ""]
        for aid in ids:
            mark = " ← active" if aid == active else ""
            lines.append(f"  • `{escape(aid)}`{escape(mark)}")
        lines += ["", "Set `SITE_ADAPTER` in \\.env to switch\\."]
        await _reply(update, "\n".join(lines))

    return {
        "start": start,
        "help": start,
        "ping": ping,
        "jobs": jobs,
        "recent": recent,
        "applied": applied,
        "ignore": ignore,
        "status": status_cmd,
        "stats": stats,
        "filters": filters_cmd,
        "adapters": adapters_cmd,
    }


def _arg(context: ContextTypes.DEFAULT_TYPE) -> str:
    """Extract the first argument from a bot command, stripped."""
    return context.args[0].strip() if context.args else ""
