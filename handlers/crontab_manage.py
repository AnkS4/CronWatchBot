from typing import TYPE_CHECKING

from config.logging import logger
from helpers.crontab_helpers import (
    CRONWATCH_COMMENT_PREFIX,
    build_urlwatch_command,
    get_cron,
    get_job_index_from_comment,
    list_urlwatch_jobs,
)
from helpers.urlwatch_helpers import load_urls
from utils import escape_html, format_bold, format_code

from .shared import auth_and_error_handler, send_error, validate_args

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes


MINUTES_IN_HOUR = 60
MINUTES_IN_DAY = 1440
MIN_ARGS = 2


def create_schedule_from_minutes(minutes: int) -> tuple[str | None, str | None]:
    """Create cron schedule expression and human-readable description from minutes.

    Converts a minute interval into a cron schedule expression and a human-friendly
    description. Supports minute intervals, hourly intervals, and daily intervals.

    Args:
        minutes: Interval in minutes for the cron job.

    Returns:
        Tuple of (cron_schedule, human_description) or (None, None) if invalid.

    Examples:
        >>> create_schedule_from_minutes(15)
        ('*/15 * * * *', 'every 15 minutes')
        >>> create_schedule_from_minutes(1)
        ('*/1 * * * *', 'every 1 minute')
        >>> create_schedule_from_minutes(120)
        ('0 */2 * * *', 'every 2 hours')
        >>> create_schedule_from_minutes(2160)
        ('0 */36 * * *', 'every 36 hours')
        >>> create_schedule_from_minutes(10080)
        ('0 0 */7 * *', 'every 7 days')
        >>> create_schedule_from_minutes(1440)
        ('0 0 */1 * *', 'every 1 day')
    """
    # Minute intervals (< 60 minutes)
    if minutes < MINUTES_IN_HOUR:
        label = "minute" if minutes == 1 else "minutes"
        return f"*/{minutes} * * * *", f"every {minutes} {label}"
    
    # Daily intervals (exact day multiples)
    if minutes % MINUTES_IN_DAY == 0:
        days = minutes // MINUTES_IN_DAY
        label = "day" if days == 1 else "days"
        return f"0 0 */{days} * *", f"every {days} {label}"
    
    # Hourly intervals (exact hour multiples, any duration)
    if minutes % MINUTES_IN_HOUR == 0:
        hours = minutes // MINUTES_IN_HOUR
        label = "hour" if hours == 1 else "hours"
        return f"0 */{hours} * * *", f"every {hours} {label}"
    
    return None, None


async def validate_job_index_and_minutes(
    update: Update, args: list[str] | None
) -> tuple[int | None, int | None]:
    """Validate and parse job index and minutes from command arguments.

    Args:
        update: Telegram update object for sending error messages.
        args: List of command arguments.

    Returns:
        Tuple of (job_index, minutes) or (None, None) if validation fails.
    """
    if not args or len(args) < MIN_ARGS:
        await send_error(update, "invalid_args")
        return None, None
    try:
        job_index = int(args[0])
        minutes = int(args[1])
    except ValueError, IndexError:
        await send_error(update, "invalid_args")
        return None, None

    if minutes <= 0:
        await send_error(update, "invalid_args")
        return None, None

    return job_index, minutes


@auth_and_error_handler
async def crontab_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display all scheduled cron jobs managed by CronWatchBot.

    Args:
        update: Telegram update object containing the message.
        context: Telegram context for the command.

    Returns:
        None
    """
    if update.effective_user:
        logger.info("CrontabView command requested by %s", update.effective_user.id)
    jobs = list_urlwatch_jobs()
    if not jobs:
        if update.message:
            await update.message.reply_text("🕑 <b>No scheduled jobs.</b>", parse_mode="HTML")
        return

    msg = ["🕑 <b>Scheduled Jobs:</b>\n"]
    for idx, job in enumerate(jobs, 1):
        msg.append(f"<b>{idx}.</b> ⏰ {format_code(job.slices)} - {format_code(job.command)}")

    if update.message:
        await update.message.reply_text("\n".join(msg), parse_mode="HTML")


@auth_and_error_handler
@validate_args(2, "❌ Usage: <code>/crontab_add &lt;job_index&gt; &lt;minutes&gt;</code>\n📝 Example: <code>/crontab_add 2 15</code>")
async def crontab_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a new scheduled cron job for a URL entry.

    Creates a cron job that will run urlwatch for the specified URL entry
    at the given interval.

    Args:
        update: Telegram update object containing the message.
        context: Telegram context containing command arguments [job_index, minutes].

    Returns:
        None
    """
    if update.effective_user:
        logger.info("CrontabAdd command requested by %s", update.effective_user.id)
    job_index, minutes = await validate_job_index_and_minutes(update, context.args)
    if job_index is None:
        return

    # Validate job index against existing URLs
    urls = load_urls()
    if not urls or job_index < 1 or job_index > len(urls):
        await send_error(update, "invalid_index", len(urls) if urls else 0)
        return

    # Validate job_index for crontab safety (defense in depth)
    assert isinstance(job_index, int) and job_index >= 1, f"Invalid job_index for crontab: {job_index}"
    
    # Check if a cron job already exists for this URL index
    cron = get_cron()
    existing_jobs = [
        job
        for job in cron
        if job.comment and job.comment == f"{CRONWATCH_COMMENT_PREFIX}{job_index}"
    ]

    if existing_jobs:
        if update.message:
            await update.message.reply_text(
                f"⚠️ A cron job already exists for URL #{job_index}.\n\n"
                f"Use <code>/crontab_edit {job_index} &lt;minutes&gt;</code> to update the schedule,\n"
                f"or <code>/crontab_delete {len(existing_jobs)}</code> to remove it first.",
                parse_mode="HTML"
            )
        return

    if minutes is None:
        return  # Already handled by validate_job_index_and_minutes
    schedule, human = create_schedule_from_minutes(minutes)
    if schedule is None:
        if update.message:
            await update.message.reply_text(
                "❌ Invalid interval. Use <60 minutes, hour multiples, or day multiples."
            )
        return
    
    # At this point, schedule is not None, so human should also not be None
    assert human is not None  # Type safety: create_schedule_from_minutes guarantees this

    # Validate job_index for crontab safety (defense in depth)
    assert isinstance(job_index, int) and job_index >= 1, f"Invalid job_index for crontab: {job_index}"
    
    command = build_urlwatch_command(job_index)
    job = cron.new(command=command, comment=f"{CRONWATCH_COMMENT_PREFIX}{job_index}")
    job.setall(schedule)

    try:
        cron.write()
    except Exception as e:
        logger.error("Failed to write crontab: %s", e)
        if update.message:
            await update.message.reply_text(
                "❌ Failed to save crontab. Check permissions and cron service."
            )
        return

    logger.info("Added job: runs %s", human)
    if update.message:
        # Get URL details for better feedback
        url_entry = urls[job_index - 1]
        url_name = url_entry.get("name", f"URL #{job_index}")
        url_url = url_entry.get("url", "")

        summary = f"✅ Added scheduled job:\n\n📌 {format_bold(url_name)}\n   🔗 {format_code(url_url)}\n   ⏰ Runs {escape_html(human)}\n   📋 Job #{len(list_urlwatch_jobs())} created."
        await update.message.reply_text(summary, parse_mode="HTML")


@auth_and_error_handler
@validate_args(2, "❌ Usage: <code>/crontab_edit &lt;index&gt; &lt;minutes&gt;</code>\n📝 Example: <code>/crontab_edit 1 30</code>")
async def crontab_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Edit the schedule of an existing cron job.

    Args:
        update: Telegram update object containing the message.
        context: Telegram context containing command arguments [job_index, minutes].

    Returns:
        None
    """
    if update.effective_user:
        logger.info("CrontabEdit command requested by %s", update.effective_user.id)
    job_index, minutes = await validate_job_index_and_minutes(update, context.args)
    if job_index is None:
        return

    # Get the cron instance first
    cron = get_cron()

    # Get jobs from this cron instance
    jobs = [job for job in cron if job.comment and job.comment.startswith(CRONWATCH_COMMENT_PREFIX)]

    # Validate job index exists
    if job_index < 1 or job_index > len(jobs):
        await send_error(update, "invalid_index", len(jobs))
        return

    # Create proper schedule using the same logic as crontab_add
    if minutes is None:
        return  # Already handled by validate_job_index_and_minutes
    schedule, human = create_schedule_from_minutes(minutes)
    if schedule is None:
        if update.message:
            await update.message.reply_text(
                "❌ Invalid interval. Use <60 minutes, hour multiples, or day multiples."
            )
        return
    
    # At this point, schedule is not None, so human should also not be None
    assert human is not None  # Type safety: create_schedule_from_minutes guarantees this

    # Modify the job from this cron instance
    job = jobs[job_index - 1]  # Convert to 0-based index
    job.setall(schedule)

    try:
        cron.write()
    except Exception as e:
        logger.error("Failed to write crontab: %s", e)
        if update.message:
            await update.message.reply_text(
                "❌ Failed to save crontab. Check permissions and cron service."
            )
        return

    logger.info("Edited job %d: now runs %s", job_index, human)
    if update.message:
        # Get URL details for better feedback
        url_index = get_job_index_from_comment(job.comment)
        urls = load_urls()
        if url_index and urls and 1 <= url_index <= len(urls):
            url_entry = urls[url_index - 1]
            url_name = url_entry.get("name", f"URL #{url_index}")
            url_url = url_entry.get("url", "")
            summary = f"✅ Updated scheduled job:\n\n📌 {format_bold(url_name)}\n   🔗 {format_code(url_url)}\n   ⏰ Now runs {escape_html(human)}\n   📋 Job #{job_index} updated."
            await update.message.reply_text(summary, parse_mode="HTML")
        else:
            await update.message.reply_text(f"✅ Updated job {job_index}: runs {human}")


@auth_and_error_handler
@validate_args(1, "❌ Usage: <code>/crontab_delete &lt;index&gt;</code>")
async def crontab_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete a scheduled cron job.

    Args:
        update: Telegram update object containing the message.
        context: Telegram context containing command arguments [job_index].

    Returns:
        None
    """
    if update.effective_user:
        logger.info("CrontabDelete command requested by %s", update.effective_user.id)
    if not context.args:
        return
    try:
        idx = int(context.args[0]) - 1
    except ValueError, IndexError:
        await send_error(update, "invalid_args")
        return

    if idx < 0:
        await send_error(update, "invalid_args")
        return

    # Get jobs from the same cron instance to avoid instance mismatch
    cron = get_cron()
    jobs = [job for job in cron if job.comment and job.comment.startswith(CRONWATCH_COMMENT_PREFIX)]
    if idx >= len(jobs):
        await send_error(update, "invalid_index", len(jobs))
        return

    cron.remove(jobs[idx])

    try:
        cron.write()
    except Exception as e:
        logger.error("Failed to write crontab: %s", e)
        if update.message:
            await update.message.reply_text(
                "❌ Failed to save crontab. Check permissions and cron service."
            )
        return

    logger.info("Deleted job %s", idx + 1)
    if update.message:
        # Get URL details for better feedback
        job = jobs[idx]
        url_index = get_job_index_from_comment(job.comment)
        urls = load_urls()
        if url_index and urls and 1 <= url_index <= len(urls):
            url_entry = urls[url_index - 1]
            url_name = url_entry.get("name", f"URL #{url_index}")
            url_url = url_entry.get("url", "")
            summary = f"🗑 Deleted scheduled job:\n\n📌 {format_bold(url_name)}\n   🔗 {format_code(url_url)}\n   📋 Job #{idx + 1} removed."
            await update.message.reply_text(summary, parse_mode="HTML")
        else:
            await update.message.reply_text(f"🗑 Deleted job {idx + 1}")
