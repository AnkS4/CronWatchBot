from telegram import Update
from telegram.ext import ContextTypes
from functools import wraps
from config.logging import logger
from config import ALLOWED_USER_IDS

def auth_and_error_handler(func):
    """Combined auth and error handling decorator"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Auth check
        if update.effective_user.id not in ALLOWED_USER_IDS:
            logger.warning("Unauthorized access attempt by %s", update.effective_user.id)
            await update.message.reply_text("❌ Unauthorized access.")
            return
        
        # Error handling
        try:
            return await func(update, context)
        except Exception as e:
            logger.exception("Error in %s: %s", func.__name__, e)
            await update.message.reply_text("💥 An error occurred. Please try again.")
    
    return wrapper

def validate_args(expected_count, usage_msg):
    """Decorator for argument validation"""
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if len(context.args) < expected_count:
                await update.message.reply_text(usage_msg, parse_mode='Markdown')
                return
            return await func(update, context)
        return wrapper
    return decorator
