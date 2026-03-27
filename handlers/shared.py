from collections import defaultdict
from functools import wraps
import time
from typing import TYPE_CHECKING, Any

from config import ALLOWED_USER_IDS
from config.logging import logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from telegram import Update
    from telegram.ext import ContextTypes

# Rate limiting
_last_command: dict[int, float] = defaultdict(float)
RATE_LIMIT_SECONDS = 0.5  # Allow 2 commands per second

# Error message constants
ERROR_MESSAGES = {
    "unauthorized": "❌ Unauthorized access.",
    "generic_error": "💥 An error occurred. Please try again.",
    "no_urls": "📭 No URLs configured.",
    "invalid_index": "❌ Invalid index. Use 1-{}.",
    "invalid_url": "❌ Invalid URL.",
    "url_exists": "⚠ URL already exists.",
    "invalid_args": "❌ Invalid arguments.",
    "rate_limit": "⏱️ Please wait a moment before sending another command.",
}


async def send_error(update: Update, error_key: str, *args: Any) -> None:
    """Send standardized error messages to the user.

    Args:
        update: Telegram update object containing the message.
        error_key: Key to lookup error message in ERROR_MESSAGES dict.
        *args: Optional format arguments for the error message.

    Returns:
        None
    """
    if not update.message:
        return
    message = ERROR_MESSAGES[error_key].format(*args) if args else ERROR_MESSAGES[error_key]
    await update.message.reply_text(message)


def auth_and_error_handler(func: Callable[..., Any]) -> Callable[..., Any]:
    """Combined authentication, rate limiting, and error handling decorator.

    Checks if the user is authorized (in ALLOWED_USER_IDS) and enforces
    rate limiting to prevent command flooding before executing the command
    handler. Also wraps the handler in a try-except block to catch and log
    any exceptions.

    Args:
        func: The async command handler function to wrap.

    Returns:
        Wrapped function with auth, rate limiting, and error handling.
    """

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        if not update.effective_user:
            return
        user_id = update.effective_user.id
        logger.info("Command received from user ID: %s", user_id)
        if user_id not in ALLOWED_USER_IDS:
            logger.warning("Unauthorized access attempt by %s", user_id)
            await send_error(update, "unauthorized")
            return

        # Rate limiting: prevent command flooding
        now = time.monotonic()
        if now - _last_command[user_id] < RATE_LIMIT_SECONDS:
            logger.warning("Rate limit exceeded by user %s", user_id)
            await send_error(update, "rate_limit")
            return
        _last_command[user_id] = now

        try:
            return await func(update, context)
        except Exception as e:
            logger.exception("Error in %s: %s", func.__name__, e)
            await send_error(update, "generic_error")

    return wrapper


def validate_args(expected_count: int, usage_msg: str) -> Callable[..., Any]:
    """Decorator for validating command argument count.

    Checks if the command has at least the expected number of arguments.
    If not, sends the usage message to the user.

    Args:
        expected_count: Minimum number of arguments required.
        usage_msg: Usage message to display if validation fails.

    Returns:
        Decorator function that wraps the command handler.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
            if not update.message or not context.args or len(context.args) < expected_count:
                if update.message:
                    await update.message.reply_text(usage_msg, parse_mode="HTML")
                return
            return await func(update, context)

        return wrapper

    return decorator
