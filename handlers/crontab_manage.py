from telegram import Update
from telegram.ext import ContextTypes
from functools import wraps
from config.logging import logger
from helpers.crotab_helpers import get_cron, list_urlwatch_jobs, build_urlwatch_command
from config import ALLOWED_USER_IDS

def require_auth(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ALLOWED_USER_IDS:
            await update.message.reply_text("❌ Unauthorized access.")
            return
        return await func(update, context)
    return wrapper

def handle_errors(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            return await func(update, context)
        except Exception as e:
            logger.exception("Error in %s: %s", func.__name__, e)
            await update.message.reply_text("💥 An error occurred. Please try again or contact support.")
    return wrapper

@require_auth
@handle_errors
async def crontab_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jobs = list_urlwatch_jobs()
    if not jobs:
        await update.message.reply_text("🕑 *No urlwatch jobs found in crontab.*\nUse `/crontab_add` to add one.", parse_mode='Markdown')
        return
    msg = ["🕑 *Scheduled urlwatch jobs in crontab:*\n"]
    for idx, job in enumerate(jobs, 1):
        msg.append(f"\n*{idx}.* ⏰ `{job.slices}`\n   📝 `{job.command}`")
    await update.message.reply_text("\n".join(msg), parse_mode='Markdown')

@require_auth
@handle_errors
async def crontab_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Add a scheduled urlwatch job to run every N minutes.
    Usage: /crontab_add <job_index> <minutes>
    Example: /crontab_add 2 15
    """
    if len(context.args) != 2:
        await update.message.reply_text(
            "❌ Usage: `/crontab_add <job_index> <minutes>`\n"
            "📝 Example: `/crontab_add 2 15` (runs job 2 every 15 minutes)",
            parse_mode='Markdown'
        )
        return
    try:
        job_index_int = int(context.args[0])
        minutes = int(context.args[1])
        if minutes <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid arguments. Minutes must be a positive integer.\n"
            "Use `/crontab_view` to see available jobs.",
            parse_mode='Markdown'
        )
        return
    cron = get_cron()
    command = build_urlwatch_command(job_index_int)
    schedule = f"*/{minutes} * * * *"
    job = cron.new(command=command, comment=f"urlwatch-bot-{job_index_int}")
    job.setall(schedule)
    cron.write()
    await update.message.reply_text(
        f"✅ Added crontab job: `{job}`\nRuns every {minutes} minutes.",
        parse_mode='Markdown'
    )

@require_auth
@handle_errors
async def crontab_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 7:
        await update.message.reply_text(
            "❌ Usage: `/crontab_edit <index> <min> <hour> <dom> <month> <dow> <job_index>`\n"
            "📝 Example: `/crontab_edit 1 0 12 * * * 2`",
            parse_mode='Markdown'
        )
        return
    idx_str = context.args[0]
    schedule = context.args[1:6]
    job_index = context.args[6]
    try:
        idx = int(idx_str) - 1
        job_index_int = int(job_index)
    except ValueError:
        await update.message.reply_text("❌ Invalid index or job index.")
        return
    jobs = list_urlwatch_jobs()
    if idx < 0 or idx >= len(jobs):
        await update.message.reply_text(f"❌ Invalid job index. Use 1-{len(jobs)}.")
        return
    cron = get_cron()
    job = jobs[idx]
    job.setall(" ".join(schedule))
    job.set_command(build_urlwatch_command(job_index_int))
    job.set_comment(f"urlwatch-bot-{job_index}")
    cron.write()
    await update.message.reply_text(f"✏ Edited crontab job {idx+1}: `{job}`", parse_mode='Markdown')

@require_auth
@handle_errors
async def crontab_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: `/crontab_delete <index>`", parse_mode='Markdown')
        return
    try:
        idx = int(context.args[0]) - 1
    except ValueError:
        await update.message.reply_text("❌ Invalid index.")
        return
    jobs = list_urlwatch_jobs()
    if idx < 0 or idx >= len(jobs):
        await update.message.reply_text(f"❌ Invalid job index. Use 1-{len(jobs)}.")
        return
    cron = get_cron()
    cron.remove(jobs[idx])
    cron.write()
    await update.message.reply_text(f"🗑 Deleted crontab job {idx+1}.")
