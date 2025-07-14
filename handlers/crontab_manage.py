from telegram import Update
from telegram.ext import ContextTypes
from config.logging import logger
from helpers.crotab_helpers import get_cron, list_urlwatch_jobs, build_urlwatch_command
from .shared import auth_and_error_handler, validate_args

@auth_and_error_handler
async def crontab_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View scheduled jobs."""
    jobs = list_urlwatch_jobs()
    if not jobs:
        logger.info("No scheduled jobs")
        await update.message.reply_text("🕑 *No scheduled jobs.*", parse_mode='Markdown')
        return
    
    msg = ["🕑 *Scheduled Jobs:*\n"]
    for idx, job in enumerate(jobs, 1):
        msg.append(f"*{idx}.* ⏰ `{job.slices}` - `{job.command}`")
    
    logger.info("Scheduled jobs: %s", msg)
    await update.message.reply_text("\n".join(msg), parse_mode='Markdown')

@auth_and_error_handler
@validate_args(2, "❌ Usage: `/crontab_add <job_index> <minutes>`\n📝 Example: `/crontab_add 2 15`")
async def crontab_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add scheduled job."""
    try:
        job_index = int(context.args[0])
        minutes = int(context.args[1])
        if minutes <= 0:
            raise ValueError
    except ValueError:
        logger.error("Invalid arguments: %s", context.args)
        await update.message.reply_text("❌ Invalid arguments. Use positive integers.")
        return
    
    # Simplified schedule logic
    if minutes < 60:
        schedule = f"*/{minutes} * * * *"
        human = f"every {minutes} minutes"
    elif minutes % 60 == 0 and minutes <= 1440:
        hours = minutes // 60
        schedule = f"0 */{hours} * * *"
        human = f"every {hours} hour(s)"
    elif minutes % 1440 == 0:
        days = minutes // 1440
        schedule = f"0 0 */{days} * *"
        human = f"every {days} day(s)"
    else:
        logger.error("Invalid interval: %s", minutes)
        await update.message.reply_text("❌ Invalid interval. Use <60 minutes, hour multiples, or day multiples.")
        return
    
    cron = get_cron()
    command = build_urlwatch_command(job_index)
    job = cron.new(command=command, comment=f"cronwatch-bot-{job_index}")
    job.setall(schedule)
    cron.write()

    logger.info("Added job: runs %s", human)
    await update.message.reply_text(f"✅ Added job: runs {human}")

@auth_and_error_handler
@validate_args(2, "❌ Usage: `/crontab_edit <index> <minutes>`")
async def crontab_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edit scheduled job."""
    try:
        idx = int(context.args[0]) - 1
        minutes = int(context.args[1])
    except ValueError:
        logger.error("Invalid arguments: %s", context.args)
        await update.message.reply_text("❌ Invalid arguments.")
        return
    
    jobs = list_urlwatch_jobs()
    if idx < 0 or idx >= len(jobs):
        logger.error("Invalid index: %s", idx)
        await update.message.reply_text(f"❌ Invalid index. Use 1-{len(jobs)}.")
        return
    
    job = jobs[idx]
    job.setall(f"*/{minutes} * * * *")
    get_cron().write()
    
    logger.info("Updated job %s: runs every %s minutes", idx+1, minutes)
    await update.message.reply_text(f"✅ Updated job {idx+1}")

@auth_and_error_handler
@validate_args(1, "❌ Usage: `/crontab_delete <index>`")
async def crontab_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete scheduled job."""
    try:
        idx = int(context.args[0]) - 1
    except ValueError:
        logger.error("Invalid index: %s", context.args)
        await update.message.reply_text("❌ Invalid index.")
        return
    
    jobs = list_urlwatch_jobs()
    if idx < 0 or idx >= len(jobs):
        logger.error("Invalid index: %s", idx)
        await update.message.reply_text(f"❌ Invalid index. Use 1-{len(jobs)}.")
        return
    
    cron = get_cron()
    cron.remove(jobs[idx])
    cron.write()
    
    logger.info("Deleted job %s", idx+1)
    await update.message.reply_text(f"🗑 Deleted job {idx+1}")
