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
            logger.warning("Unauthorized access attempt by %s", update.effective_user.id)
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
        logger.warning("No urlwatch jobs found in crontab.")
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
    # Determine appropriate cron schedule for any N minutes
    if minutes < 60:
        schedule = f"*/{minutes} * * * *"
        human = f"every {minutes} minutes"
    elif minutes % 1440 == 0:
        # Divides evenly into days
        days = minutes // 1440
        schedule = f"0 0 */{days} * *"
        human = f"every {days} day(s)"
    elif minutes % 60 == 0 and (minutes // 60) < 24 and 24 % (minutes // 60) == 0:
        # Divides evenly into 24 hours
        hours = minutes // 60
        schedule = f"0 */{hours} * * *"
        human = f"every {hours} hour(s)"
    else:
        logger.warning("Invalid minutes: %d", minutes)
        await update.message.reply_text(
            f"❌ Sorry, {minutes} minutes is not a standard cron interval.\n"
            f"Cron can only schedule intervals minutes that is less than 60 minutes, multiple of hour (60, 120, 180, ...) till 24-hour period or multiple of day(s) (1440, 2880, ...).\n"
            f"For complex intervals (like {minutes}), consider using an external scheduler or background script.",
            parse_mode='Markdown'
        )
        return
    job = cron.new(command=command, comment=f"cronwatch-bot-{job_index_int}")
    job.setall(schedule)
    cron.write()
    await update.message.reply_text(
        f"✅ Added crontab job: `{job}`\nRuns {human}.",
        parse_mode='Markdown'
    )

@require_auth
@handle_errors
async def crontab_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Usage: `/crontab_edit <index> <minutes>`\n"
            "📝 Example: `/crontab_edit 1 15`",
            parse_mode='Markdown'
        )
        return
    idx_str = context.args[0]
    minutes = context.args[1]
    try:
        idx = int(idx_str) - 1
        minutes_int = int(minutes)
    except ValueError:
        await update.message.reply_text("❌ Invalid index or minutes.")
        return
    jobs = list_urlwatch_jobs()
    if idx < 0 or idx >= len(jobs):
        await update.message.reply_text(f"❌ Invalid job index. Use 1-{len(jobs)}.")
        return
    cron = get_cron()
    job = jobs[idx]
    job.setall(f"*/{minutes_int} * * * *")
    job.set_command(build_urlwatch_command(idx+1))
    job.set_comment(f"urlwatch-bot-{idx+1}")
    cron.write()
    await update.message.reply_text(f"✏ Edited crontab job {idx+1}: `{job}`", parse_mode='Markdown')

@require_auth
@handle_errors
async def crontab_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        logger.warning("No index provided for crontab delete.")
        await update.message.reply_text("❌ Usage: `/crontab_delete <index>`", parse_mode='Markdown')
        return

    try:
        idx = int(context.args[0]) - 1

    except ValueError:
        logger.warning("Invalid index provided: %s", context.args[0])
        await update.message.reply_text("❌ Invalid index.")
        return
    
    jobs = list_urlwatch_jobs()
    
    if idx < 0 or idx >= len(jobs):
        logger.warning("Invalid job index: %d", idx)
        await update.message.reply_text(f"❌ Invalid job index. Use 1-{len(jobs)}.")
        return
    cron = get_cron()
    cron.remove(jobs[idx])
    cron.write()
    logger.info("Deleted crontab job %s", idx)
    await update.message.reply_text(f"🗑 Deleted crontab job {idx+1}.")
