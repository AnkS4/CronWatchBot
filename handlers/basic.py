from telegram import Update
from telegram.ext import ContextTypes
from config.logging import logger
from .shared import auth_and_error_handler

@auth_and_error_handler
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message."""
    logger.info("Help command requested by %s", update.effective_user.id)
    await update.message.reply_text(
        """
📚 *CronWatchBot — Help & Command Guide*

*👋 Getting Started:*
Step 1. Add a website to monitor:
   `/add <url> [optional name]`
   ```
   /add https://github.com/AnkS4/CronWatchBot CronWatchBot Repo
   ```
Step 2. View all monitored sites:
   `/view`
Step 3. Schedule automatic checks:
   `/crontab_add <job number> <minutes>`
   ```
   /crontab_add 1 60
   ```

*🔄 Managing URLs:*
- Edit a job:
   `/edit <index> <url> [name]`
   ```
   /edit 1 https://newurl.com New Name
   ```
- Delete a job:
   `/delete <index>`
   ```
   /delete 2
   ```
- Show filters or properties:
   `/editfilter <index>`
   `/editprop <index>`
- Add or change filters:
   `/editfilter <index> [filters...]`
   ```
   /editfilter 1 html2text strip
   ```
- Add or change properties:
   `/editprop <index> [property:value] ...`
   ```
   /editprop 1 timeout:30
   ```

*⏰ Scheduling (Crontab):*
- View all scheduled jobs:
   `/crontab_view`
- Add a schedule:
   `/crontab_add <job_index> <minutes>`
   ```
   /crontab_add 2 15
   ```
- Edit a schedule:
   `/crontab_edit <index> <min> <hour> <dom> <month> <dow> <job_index>`
   ```
   /crontab_edit 1 0 12 * * * 2
   ```
- Delete a schedule:
   `/crontab_delete <index>`

💡 *Tips:*
- Use `/view` to see all URLs and their numbers for scheduling.
- Use `/crontab_view` to see all scheduled jobs.
- Send any command without arguments (e.g. `/edit`) to see usage and examples.
- Use `/start` for a quick workflow overview.

If you get stuck, just try `/help` again or use `/start` for a simple introduction!
        """,
        parse_mode='Markdown'
    )

@auth_and_error_handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message."""
    logger.info("Start command requested by %s", update.effective_user.id)
    await update.message.reply_text(
        """
🤖 *Welcome to CronWatchBot!*

*🚀 Getting Started:*

Step 1. To start watching a website, type: `/add <url> [optional name]`
```
/add https://www.github.com/AnkS4/CronWatchBot CronWatchBot
```
Step 2. To edit filters, type: `/editfilter <index> [filters...]`
```
/editfilter 1 xpath://span[@id=\"repo-stars-counter-star\"] html2text strip
```
Step 3. To schedule automatic checks, type: `/crontab_add <job number> <minutes>`
```
/crontab_add 1 60
```

💡 _Tip: Use_ `/help` _to see detailed usage help._
        """,
        parse_mode='Markdown'
    )

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unknown commands."""
    if update.message and update.message.text and update.message.text.startswith("/"):
        await update.message.reply_text("❓ Unknown command. Use `/help` for available commands.")
