from telegram import Update
from telegram.ext import ContextTypes
from typing import Optional, Tuple
from config.logging import logger
from helpers.crontab_helpers import get_cron, list_urlwatch_jobs, build_urlwatch_command, CRONWATCH_COMMENT_PREFIX
from .shared import auth_and_error_handler, validate_args, send_error

def create_schedule_from_minutes(minutes: int) -> Tuple[Optional[str], Optional[str]]:
    """Create cron schedule and human description from minutes."""
    if minutes < 60:
        return f"*/{minutes} * * * *", f"every {minutes} minutes"
    if minutes % 1440 == 0:
        days = minutes // 1440
        return f"0 0 */{days} * *", f"every {days} day(s)"
    if minutes % 60 == 0 and minutes <= 1440:
        hours = minutes // 60
        return f"0 */{hours} * * *", f"every {hours} hour(s)"
    return None, None

async def validate_job_index_and_minutes(update: Update, args: list) -> Tuple[Optional[int], Optional[int]]:
    """Validate job index and minutes arguments."""
    try:
        job_index = int(args[0])
        minutes = int(args[1])
        if minutes <= 0:
            raise ValueError("Minutes must be positive")
        return job_index, minutes
    except (ValueError, IndexError):
        await send_error(update, 'invalid_args')
        return None, None

@auth_and_error_handler
async def crontab_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View scheduled jobs."""
    logger.info("CrontabView command requested by %s", update.effective_user.id)
    jobs = list_urlwatch_jobs()
    if not jobs:
        if update.message:
            await update.message.reply_text("🕑 *No scheduled jobs.*", parse_mode='Markdown')
        return
    
    msg = ["🕑 *Scheduled Jobs:*\n"]
    for idx, job in enumerate(jobs, 1):
        msg.append(f"*{idx}.* ⏰ `{job.slices}` - `{job.command}`")
    
    if update.message:
        await update.message.reply_text("\n".join(msg), parse_mode='Markdown')

@auth_and_error_handler
@validate_args(2, "❌ Usage: `/crontab_add <job_index> <minutes>`\n📝 Example: `/crontab_add 2 15`")
async def crontab_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add scheduled job."""
    logger.info("CrontabAdd command requested by %s", update.effective_user.id)
    job_index, minutes = await validate_job_index_and_minutes(update, context.args)
    if job_index is None:
        return
    
    # Validate job index against existing URLs
    from helpers.urlwatch_helpers import load_urls
    urls = load_urls()
    if not urls or job_index < 1 or job_index > len(urls):
        await send_error(update, 'invalid_index', len(urls) if urls else 0)
        return
    
    schedule, human = create_schedule_from_minutes(minutes)
    if schedule is None:
        if update.message:
            await update.message.reply_text("❌ Invalid interval. Use <60 minutes, hour multiples, or day multiples.")
        return
    
    cron = get_cron()
    command = build_urlwatch_command(job_index)
    job = cron.new(command=command, comment=f"{CRONWATCH_COMMENT_PREFIX}{job_index}")
    job.setall(schedule)
    
    try:
        cron.write()
    except Exception as e:
        logger.error("Failed to write crontab: %s", e)
        if update.message:
            await update.message.reply_text("❌ Failed to save crontab. Check permissions and cron service.")
        return

    logger.info("Added job: runs %s", human)
    if update.message:
        await update.message.reply_text(f"✅ Added job: runs {human}")

@auth_and_error_handler
@validate_args(2, "❌ Usage: `/crontab_edit <index> <minutes>`\n📝 Example: `/crontab_edit 1 30`")
async def crontab_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edit scheduled job."""
    logger.info("CrontabEdit command requested by %s", update.effective_user.id)
    job_index, minutes = await validate_job_index_and_minutes(update, context.args)
    if job_index is None:
        return
    
    # Validate job index exists
    jobs = list_urlwatch_jobs()
    if job_index < 1 or job_index > len(jobs):
        await send_error(update, 'invalid_index', len(jobs))
        return
    
    # Create proper schedule using the same logic as crontab_add
    schedule, human = create_schedule_from_minutes(minutes)
    if schedule is None:
        if update.message:
            await update.message.reply_text("❌ Invalid interval. Use <60 minutes, hour multiples, or day multiples.")
        return
    
    job = jobs[job_index - 1]  # Convert to 0-based index
    job.setall(schedule)
    
    try:
        get_cron().write()
    except Exception as e:
        logger.error("Failed to write crontab: %s", e)
        if update.message:
            await update.message.reply_text("❌ Failed to save crontab. Check permissions and cron service.")
        return
    
    logger.info("Updated job %s: runs %s", job_index, human)
    if update.message:
        await update.message.reply_text(f"✅ Updated job {job_index}: runs {human}")

@auth_and_error_handler
@validate_args(1, "❌ Usage: `/crontab_delete <index>`")
async def crontab_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete scheduled job."""
    logger.info("CrontabDelete command requested by %s", update.effective_user.id)
    try:
        idx = int(context.args[0]) - 1
        if idx < 0:
            raise ValueError("Invalid job index")
    except ValueError:
        await send_error(update, 'invalid_args')
        return
    
    jobs = list_urlwatch_jobs()
    if idx >= len(jobs):
        await send_error(update, 'invalid_index', len(jobs))
        return
    
    cron = get_cron()
    cron.remove(jobs[idx])
    
    try:
        cron.write()
    except Exception as e:
        logger.error("Failed to write crontab: %s", e)
        if update.message:
            await update.message.reply_text("❌ Failed to save crontab. Check permissions and cron service.")
        return
    
    logger.info("Deleted job %s", idx+1)
    if update.message:
        await update.message.reply_text(f"🗑 Deleted job {idx+1}")
