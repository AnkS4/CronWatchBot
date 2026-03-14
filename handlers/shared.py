from telegram import Update
from telegram.ext import ContextTypes
from functools import wraps
from config.logging import logger
from config import ALLOWED_USER_IDS

# Error message constants
ERROR_MESSAGES = {
    'unauthorized': "❌ Unauthorized access.",
    'generic_error': "💥 An error occurred. Please try again.",
    'no_urls': "📭 No URLs configured.",
    'invalid_index': "❌ Invalid index. Use 1-{}.",
    'invalid_url': "❌ Invalid URL.",
    'url_exists': "⚠ URL already exists.",
    'invalid_args': "❌ Invalid arguments."
}

async def send_error(update: Update, error_key: str, *args):
    """Helper to send standardized error messages"""
    if not update.message:
        return
    message = ERROR_MESSAGES[error_key].format(*args) if args else ERROR_MESSAGES[error_key]
    await update.message.reply_text(message)

def auth_and_error_handler(func):
    """Combined auth and error handling decorator"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Auth check
        user_id = update.effective_user.id
        logger.info("Command received from user ID: %s", user_id)
        if user_id not in ALLOWED_USER_IDS:
            logger.warning("Unauthorized access attempt by %s", user_id)
            await send_error(update, 'unauthorized')
            return
        
        # Error handling
        try:
            return await func(update, context)
        except Exception as e:
            logger.exception("Error in %s: %s", func.__name__, e)
            await send_error(update, 'generic_error')
    
    return wrapper

def validate_args(expected_count, usage_msg):
    """Decorator for argument validation"""
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not update.message or len(context.args) < expected_count:
                if update.message:
                    await update.message.reply_text(usage_msg, parse_mode='Markdown')
                return
            return await func(update, context)
        return wrapper
    return decorator
