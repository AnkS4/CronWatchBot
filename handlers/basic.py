from typing import TYPE_CHECKING

from config import ALLOWED_USER_IDS
from config.logging import logger

from .shared import auth_and_error_handler

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes


@auth_and_error_handler
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send comprehensive help message with all available commands.

    Args:
        update: Telegram update object containing the message.
        context: Telegram context for the command.

    Returns:
        None
    """
    if update.effective_user:
        logger.info("Help command requested by %s", update.effective_user.id)
    if update.message:
        await update.message.reply_text(
            """
📚 <b>CronWatchBot — Help &amp; Command Guide</b>

<b>👋 Getting Started:</b>
Step 1. Add a website to monitor:
   <code>/add &lt;url&gt; [optional name]</code>
   <pre>/add https://news.ycombinator.com/ Hacker News</pre>
Step 2. View all monitored sites:
   <code>/list</code>
Step 3. Schedule automatic checks:
   <code>/crontab_add &lt;job number&gt; &lt;minutes&gt;</code>
   <pre>/crontab_add 1 60</pre>

<b>🔄 Managing URLs:</b>
- Edit a job:
   <code>/edit &lt;index&gt; &lt;url&gt; [name]</code>
   <pre>/edit 1 https://newurl.com New Name</pre>
- Delete a job:
   <code>/delete &lt;index&gt;</code>
   <pre>/delete 2</pre>
- Show filters or properties:
   <code>/editfilter &lt;index&gt;</code>
   <code>/editprop &lt;index&gt;</code>
- Add or change filters:
   <code>/editfilter &lt;index&gt; [filters...]</code>
   <pre>/editfilter 1 css:span.titleline&gt;a html2text</pre>
- Add or change properties:
   <code>/editprop &lt;index&gt; [property:value] ...</code>
   <pre>/editprop 1 timeout:30</pre>

<b>⏰ Scheduling (Crontab):</b>
- View all scheduled jobs:
   <code>/crontab_view</code>
- Add a schedule:
   <code>/crontab_add &lt;job_index&gt; &lt;minutes&gt;</code>
   <pre>/crontab_add 1 60</pre>
- Edit a schedule:
   <code>/crontab_edit &lt;index&gt; &lt;minutes&gt;</code>
   <pre>/crontab_edit 1 30</pre>
- Delete a schedule:
   <code>/crontab_delete &lt;index&gt;</code>

💡 <b>Tips:</b>
- Use <code>/list</code> to see all URLs and their numbers for scheduling.
- Use <code>/crontab_view</code> to see all scheduled jobs.
- Send any command without arguments (e.g. <code>/edit</code>) to see usage and examples.
- Use <code>/start</code> for a quick workflow overview.

If you get stuck, just try <code>/help</code> again or use <code>/start</code> for a simple introduction!
        """,
            parse_mode="HTML",
        )


@auth_and_error_handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message with quick start guide.

    Args:
        update: Telegram update object containing the message.
        context: Telegram context for the command.

    Returns:
        None
    """
    if update.effective_user:
        logger.info("Start command requested by %s", update.effective_user.id)
    if update.message:
        await update.message.reply_text(
            """
🤖 <b>Welcome to CronWatchBot!</b>

<b>🚀 Getting Started:</b>

Step 1. To start watching a website, type: <code>/add &lt;url&gt; [optional name]</code>
<pre>/add https://news.ycombinator.com/ Hacker News</pre>
Step 2. To edit filters, type: <code>/editfilter &lt;index&gt; [filters...]</code>
<pre>/editfilter 1 css:span.titleline&gt;a html2text</pre>
Step 3. To schedule automatic checks, type: <code>/crontab_add &lt;job number&gt; &lt;minutes&gt;</code>
<pre>/crontab_add 1 60</pre>

💡 <i>Tip: Use</i> <code>/help</code> <i>to see detailed usage help.</i>
        """,
            parse_mode="HTML",
        )


async def edited_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle edited messages with a simple response.

    Silently ignores edits from unauthorized users to avoid leaking bot existence.

    Args:
        update: Telegram update object containing the edited message.
        context: Telegram context for the command.

    Returns:
        None
    """
    if not update.effective_user or update.effective_user.id not in ALLOWED_USER_IDS:
        return
    if update.edited_message:
        await update.edited_message.reply_text("i️ Message edits are not considered.")


@auth_and_error_handler
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unknown commands and non-command text messages.

    Distinguishes between unknown commands (starting with /) and regular text messages,
    providing appropriate feedback for each case.

    Args:
        update: Telegram update object containing the message.
        context: Telegram context for the command.

    Returns:
        None
    """
    if not update.message or not update.message.text:
        return

    message_text = update.message.text.strip()
    is_command = message_text.startswith("/")

    if update.effective_user:
        logger.info(
            "%s received from %s: %s",
            "Unknown command" if is_command else "Non-command message",
            update.effective_user.id,
            message_text,
        )

    if is_command:
        await update.message.reply_text(
            "❓ Unknown command. Use <code>/help</code> for available commands.", parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            "👋 I only respond to commands.\n\n"
            "Use <code>/help</code> to see available commands or <code>/start</code> to get started.",
            parse_mode="HTML",
        )
