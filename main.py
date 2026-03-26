from typing import TYPE_CHECKING, Any

from dotenv import load_dotenv
from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

from config import TOKEN
from config.logging import install_telegram_http_filter, logger
from handlers import basic, crontab_manage, urlwatch_manage

load_dotenv()  # Load environment variables first

# Reload existing crontab on startup to ensure crond picks up persisted jobs
try:
    from helpers.crontab_helpers import get_cron

    cron = get_cron()
    cron.write()  # This signals crond to reload via crontab command
    logger.info("Reloaded existing crontab entries")
except Exception as e:
    logger.warning("Failed to reload crontab on startup: %s", e)


async def post_init(application: Application) -> None:  # type: ignore[type-arg]
    """Set bot commands after initialization."""
    commands = [
        BotCommand("start", "Get started with the bot"),
        BotCommand("help", "Show detailed help and command guide"),
        BotCommand("list", "View all monitored URLs"),
        BotCommand("add", "Add a new URL to monitor"),
        BotCommand("edit", "Edit an existing URL"),
        BotCommand("delete", "Delete a URL"),
        BotCommand("editfilter", "Edit filters for a URL"),
        BotCommand("editprop", "Edit properties for a URL"),
        BotCommand("check", "Check current output of a URL"),
        BotCommand("crontab_view", "View all scheduled cron jobs"),
        BotCommand("crontab_add", "Add a new cron job"),
        BotCommand("crontab_edit", "Edit an existing cron job"),
        BotCommand("crontab_delete", "Delete a cron job"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands set successfully")


def main() -> None:
    """Initialize and run the CronWatchBot."""
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    install_telegram_http_filter()

    command_handlers: dict[
        str, Callable[[Update, ContextTypes.DEFAULT_TYPE], Coroutine[Any, Any, None]]
    ] = {
        "start": basic.start,
        "help": basic.help_command,
        "list": urlwatch_manage.view_urls,
        "add": urlwatch_manage.add_url,
        "edit": urlwatch_manage.edit_url,
        "delete": urlwatch_manage.delete_url,
        "editfilter": urlwatch_manage.edit_url_filters,
        "editprop": urlwatch_manage.edit_url_properties,
        "check": urlwatch_manage.check_url_output,
        "crontab_view": crontab_manage.crontab_view,
        "crontab_add": crontab_manage.crontab_add,
        "crontab_edit": crontab_manage.crontab_edit,
        "crontab_delete": crontab_manage.crontab_delete,
    }

    for cmd, handler in command_handlers.items():
        app.add_handler(CommandHandler(cmd, handler))

    app.add_handler(MessageHandler(filters.TEXT, basic.unknown))
    logger.info("CronWatchBot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
