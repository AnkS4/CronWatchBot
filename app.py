import yaml
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
import logging
import tempfile
import shutil
from urllib.parse import urlparse

# === CONFIGURATION ===
TOKEN = ""  # Replace with your BotFather token
ALLOWED_USER_IDS = []     # Replace with your Telegram user ID(s) for security
URLS_FILE = ""  # Path to your urls.yaml

# === LOGGING SETUP ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === HELPER FUNCTIONS ===
def load_urls():
    """Load URL entries from YAML file.

    Returns
    -------
    list[dict]
        A list of urlwatch job dictionaries. Returns an empty list on failure.
    """
    if not os.path.exists(URLS_FILE):
        logger.warning("URLs file not found at %s. Returning empty list.", URLS_FILE)
        return []

    try:
        with open(URLS_FILE, "r") as f:
            data = list(yaml.safe_load_all(f)) or []
            data = [d for d in data if d]
            if not isinstance(data, list):
                raise ValueError("YAML root must be a list of urlwatch job entries.")
            return data
    except yaml.YAMLError as e:
        logger.exception("Invalid YAML syntax in %s: %s", URLS_FILE, e)
    except Exception:
        logger.exception("Unexpected error while loading URLs from %s", URLS_FILE)

    return []
    if not os.path.exists(URLS_FILE):
        return []
    try:
        with open(URLS_FILE, "r") as f:
            try:
                data = list(yaml.safe_load_all(f))
                return data if data else []
            except yaml.YAMLError as e:
                logger.error(f"YAML parsing error: {e}")
                return []
    except Exception as e:
        logger.error(f"Error loading URLs file: {e}")
        return []

def save_urls(urls: list[dict]):
    """Write URL entries to YAML file atomically."""
    os.makedirs(os.path.dirname(URLS_FILE), exist_ok=True)
    try:
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
            yaml.safe_dump_all(urls, tmp, sort_keys=False)
            temp_name = tmp.name
        shutil.move(temp_name, URLS_FILE)
    except Exception:
        logger.exception("Failed to save URLs to %s", URLS_FILE)
        raise
    try:
        with open(URLS_FILE, "w") as f:
            yaml.dump_all(urls, f, sort_keys=False)
    except Exception as e:
        logger.error(f"Error saving URLs file: {e}")
        raise

def validate_url(candidate: str) -> bool:
    """Very small URL validation helper."""
    parsed = urlparse(candidate)
    return all([parsed.scheme in ("http", "https"), parsed.netloc])

def is_authorized(user_id):
    return user_id in ALLOWED_USER_IDS

# === BOT COMMAND HANDLERS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return
    await update.message.reply_text(
        "Welcome to urlwatch bot!\n"
        "Commands:\n"
        "/view - View all URLs\n"
        "/add <url> - Add a new URL\n"
        "/edit <index> <url> - Edit a URL\n"
        "/delete <index> - Delete a URL"
    )

async def view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return
    try:
        urls = load_urls()
        if not urls:
            await update.message.reply_text("No URLs configured or failed to load YAML.")
            return
        msg = "\n".join([f"{i+1}. {u.get('name', u.get('url', 'No name'))}: {u.get('url', 'No URL')}" for i, u in enumerate(urls)])
        await update.message.reply_text(f"Current URLs:\n{msg}")
    except Exception as e:
        logger.error(f"Error in view: {e}")
        await update.message.reply_text(f"Error viewing URLs: {e}")

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /add <url> [name]")
        return

    new_url = context.args[0]
    custom_name = " ".join(context.args[1:]) if len(context.args) > 1 else new_url

    if not validate_url(new_url):
        await update.message.reply_text("Please provide a valid http/https URL.")
        return

    try:
        urls = load_urls()
        urls.append({"url": new_url, "name": custom_name})
        save_urls(urls)
        await update.message.reply_text(f"Added: {custom_name}")
    except Exception as e:
        logger.error("Error in add: %s", e, exc_info=True)
        await update.message.reply_text("Failed to add URL due to an internal error.")
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /add <url>")
        return
    new_url = context.args[0]
    try:
        urls = load_urls()
        urls.append({'url': new_url})
        save_urls(urls)
        await update.message.reply_text(f"Added: {new_url}")
    except Exception as e:
        logger.error(f"Error in add: {e}")
        await update.message.reply_text(f"Error adding URL: {e}")

async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /edit <index> <url> [name]")
        return

    try:
        idx = int(context.args[0]) - 1
    except ValueError:
        await update.message.reply_text("Index must be a number.")
        return

    new_url = context.args[1]
    new_name = " ".join(context.args[2:]) if len(context.args) > 2 else new_url

    if not validate_url(new_url):
        await update.message.reply_text("Please provide a valid http/https URL.")
        return

    try:
        urls = load_urls()
        if not urls:
            await update.message.reply_text("No URLs to edit.")
            return
        if 0 <= idx < len(urls):
            old_entry = urls[idx]
            urls[idx] = {"url": new_url, "name": new_name}
            save_urls(urls)
            await update.message.reply_text(
                f"Updated entry {idx+1}:\n- Old: {old_entry.get('name', old_entry.get('url'))}\n- New: {new_name}"
            )
        else:
            await update.message.reply_text("Invalid index.")
    except Exception as e:
        logger.error("Error in edit: %s", e, exc_info=True)
        await update.message.reply_text("Failed to edit URL due to an internal error.")
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /edit <index> <url>")
        return
    try:
        idx = int(context.args[0]) - 1
        new_url = context.args[1]
        urls = load_urls()
        if not urls:
            await update.message.reply_text("No URLs to edit or failed to load YAML.")
            return
        if 0 <= idx < len(urls):
            old_url = urls[idx].get('url', 'No URL')
            urls[idx]['url'] = new_url
            save_urls(urls)
            await update.message.reply_text(f"Changed URL {idx+1} from {old_url} to {new_url}")
        else:
            await update.message.reply_text("Invalid index.")
    except ValueError:
        await update.message.reply_text("Index must be a number.")
    except Exception as e:
        logger.error(f"Error in edit: {e}")
        await update.message.reply_text(f"Error editing URL: {e}")

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /delete <index>")
        return
    try:
        idx = int(context.args[0]) - 1
    except ValueError:
        await update.message.reply_text("Index must be a number.")
        return

    try:
        urls = load_urls()
        if not urls:
            await update.message.reply_text("No URLs to delete.")
            return
        if 0 <= idx < len(urls):
            removed = urls.pop(idx)
            save_urls(urls)
            await update.message.reply_text(f"Deleted: {removed.get('name', removed.get('url'))}")
        else:
            await update.message.reply_text("Invalid index.")
    except Exception as e:
        logger.error("Error in delete: %s", e, exc_info=True)
        await update.message.reply_text("Failed to delete URL due to an internal error.")
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /delete <index>")
        return
    try:
        idx = int(context.args[0]) - 1
        urls = load_urls()
        if not urls:
            await update.message.reply_text("No URLs to delete or failed to load YAML.")
            return
        if 0 <= idx < len(urls):
            removed = urls.pop(idx)
            save_urls(urls)
            await update.message.reply_text(f"Deleted: {removed.get('url', 'No URL')}")
        else:
            await update.message.reply_text("Invalid index.")
    except ValueError:
        await update.message.reply_text("Index must be a number.")
    except Exception as e:
        logger.error(f"Error in delete: {e}")
        await update.message.reply_text(f"Error deleting URL: {e}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Global error handler that logs exceptions and notifies the user."""
    logger.exception("Unhandled exception while processing update %s: %s", update, context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text("An unexpected error occurred. The incident has been logged.")

# === MAIN BOT SETUP ===
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("view", view))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("edit", edit))
    app.add_handler(CommandHandler("delete", delete))

    # Global error handler
    app.add_error_handler(error_handler)

    logger.info("Bot is running. Press Ctrl+C to stop.")
    app.run_polling()