from telegram.ext import ApplicationBuilder, CommandHandler
from config import TOKEN
from handlers import basic, urlwatch_manage, crontab_manage


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Basic commands
    app.add_handler(CommandHandler("start", basic.start))
    app.add_handler(CommandHandler("help", basic.help_command))

    # Urlwatch management
    app.add_handler(CommandHandler("view", urlwatch_manage.view))
    app.add_handler(CommandHandler("add", urlwatch_manage.add))
    app.add_handler(CommandHandler("edit", urlwatch_manage.edit))
    app.add_handler(CommandHandler("editfilter", urlwatch_manage.edit_filter))
    app.add_handler(CommandHandler("editprop", urlwatch_manage.edit_property))
    app.add_handler(CommandHandler("delete", urlwatch_manage.delete))

    # Crontab management
    app.add_handler(CommandHandler("crontab_view", crontab_manage.crontab_view))
    app.add_handler(CommandHandler("crontab_add", crontab_manage.crontab_add))
    app.add_handler(CommandHandler("crontab_edit", crontab_manage.crontab_edit))
    app.add_handler(CommandHandler("crontab_delete", crontab_manage.crontab_delete))

    # Start the bot
    print("CronWatchBot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
