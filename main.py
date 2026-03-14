from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from config import TOKEN
from handlers import basic, urlwatch_manage, crontab_manage
from config.logging import install_telegram_http_filter

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    install_telegram_http_filter()
    
    handlers = {
        "start": basic.start,
        "help": basic.help_command,
        "list": urlwatch_manage.view_urls,
        "add": urlwatch_manage.add_url,
        "edit": urlwatch_manage.edit_url,
        "delete": urlwatch_manage.delete_url,
        "editfilter": urlwatch_manage.edit_url_filters,
        "editprop": urlwatch_manage.edit_url_properties,
        "crontab_view": crontab_manage.crontab_view,
        "crontab_add": crontab_manage.crontab_add,
        "crontab_edit": crontab_manage.crontab_edit,
        "crontab_delete": crontab_manage.crontab_delete,
    }
    
    for cmd, handler in handlers.items():
        app.add_handler(CommandHandler(cmd, handler))
    
    app.add_handler(MessageHandler(filters.COMMAND, basic.unknown))
    print("CronWatchBot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
