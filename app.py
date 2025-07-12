import yaml
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
import logging
import tempfile
import shutil
from urllib.parse import urlparse
from typing import List, Dict, Optional
from functools import wraps

# === CONFIGURATION ===
TOKEN = ""
ALLOWED_USER_IDS = []
URLS_FILE = ""

# === LOGGING SETUP ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === DECORATORS ===
def require_auth(func):
    """Decorator to ensure user is authorized."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ALLOWED_USER_IDS:
            await update.message.reply_text("❌ Unauthorized access.")
            return
        return await func(update, context)
    return wrapper

def handle_errors(func):
    """Decorator for consistent error handling."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            return await func(update, context)
        except Exception as e:
            logger.exception("Error in %s: %s", func.__name__, e)
            await update.message.reply_text(f"❌ Operation failed: {str(e)}")
    return wrapper

# === HELPER FUNCTIONS ===
def load_urls() -> List[Dict]:
    """Load URL entries from YAML file."""
    if not os.path.exists(URLS_FILE):
        logger.warning("URLs file not found at %s", URLS_FILE)
        return []

    try:
        with open(URLS_FILE, "r") as f:
            data = list(yaml.safe_load_all(f))
            return [entry for entry in data if entry] if data else []
    except yaml.YAMLError as e:
        logger.error("YAML parsing error: %s", e)
        return []
    except Exception as e:
        logger.error("Error loading URLs file: %s", e)
        return []

def save_urls(urls: List[Dict]) -> None:
    """Write URL entries to YAML file atomically."""
    os.makedirs(os.path.dirname(URLS_FILE), exist_ok=True)
    
    with tempfile.NamedTemporaryFile("w", delete=False, dir=os.path.dirname(URLS_FILE)) as tmp:
        yaml.safe_dump_all(urls, tmp, sort_keys=False, default_flow_style=False)
        temp_name = tmp.name
    
    shutil.move(temp_name, URLS_FILE)
    logger.info("Successfully saved %d URLs to %s", len(urls), URLS_FILE)

def validate_url(url: str) -> bool:
    """Validate URL format."""
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme in ("http", "https") and parsed.netloc)
    except Exception:
        return False

def get_display_name(entry: Dict) -> str:
    """Get display name for URL entry."""
    return entry.get('name', entry.get('url', 'Unnamed entry'))

def validate_index(idx_str: str, urls: List[Dict]) -> Optional[int]:
    """Validate and convert index string to integer."""
    try:
        idx = int(idx_str) - 1
        if 0 <= idx < len(urls):
            return idx
        return None
    except ValueError:
        return None

# === BOT COMMAND HANDLERS ===
@require_auth
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message with available commands."""
    await update.message.reply_text(
        "🤖 *URLWatch Bot*\n\n"
        "📋 *Commands:*\n"
        "/view - View all URLs\n"
        "/add <url> [name] - Add a new URL\n"
        "/edit <index> <url> [name] - Edit a URL\n"
        "/delete <index> - Delete a URL\n\n"
        "💡 *Tip:* Use /view to see current URLs and their indices",
        parse_mode='Markdown'
    )

@require_auth
@handle_errors
async def view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display all configured URLs."""
    urls = load_urls()
    
    if not urls:
        await update.message.reply_text("📭 No URLs configured.")
        return
    
    msg_lines = ["📋 *Current URLs:*\n"]
    for i, entry in enumerate(urls, 1):
        name = get_display_name(entry)
        url = entry.get('url', 'No URL')
        msg_lines.append(f"{i}. *{name}*\n   `{url}`")
    
    await update.message.reply_text("\n".join(msg_lines), parse_mode='Markdown')

@require_auth
@handle_errors
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a new URL to monitor."""
    if not context.args:
        await update.message.reply_text("❌ Usage: `/add <url> [name]`", parse_mode='Markdown')
        return

    new_url = context.args[0]
    custom_name = " ".join(context.args[1:]) if len(context.args) > 1 else new_url

    if not validate_url(new_url):
        await update.message.reply_text("❌ Please provide a valid http/https URL.")
        return

    urls = load_urls()
    
    # Check for duplicates
    if any(entry.get('url') == new_url for entry in urls):
        await update.message.reply_text("⚠ URL already exists in the list.")
        return
    
    new_entry = {"name": custom_name, "url": new_url}
    urls.append(new_entry)
    save_urls(urls)
    
    await update.message.reply_text(f"✅ Added: *{custom_name}*", parse_mode='Markdown')

@require_auth
@handle_errors
async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edit an existing URL entry."""
    if len(context.args) < 2:
        await update.message.reply_text("❌ Usage: `/edit <index> <url> [name]`", parse_mode='Markdown')
        return

    urls = load_urls()
    if not urls:
        await update.message.reply_text("📭 No URLs to edit.")
        return

    idx = validate_index(context.args[0], urls)
    if idx is None:
        await update.message.reply_text(f"❌ Invalid index. Use 1-{len(urls)}.")
        return

    new_url = context.args[1]
    new_name = " ".join(context.args[2:]) if len(context.args) > 2 else new_url

    if not validate_url(new_url):
        await update.message.reply_text("❌ Please provide a valid http/https URL.")
        return

    old_entry = urls[idx]
    urls[idx] = {"name": new_name, "url": new_url}
    
    # Preserve existing filters if they exist
    if 'filter' in old_entry:
        urls[idx]['filter'] = old_entry['filter']
    
    save_urls(urls)
    
    await update.message.reply_text(
        f"✅ Updated entry {idx+1}:\n"
        f"*Old:* {get_display_name(old_entry)}\n"
        f"*New:* {new_name}",
        parse_mode='Markdown'
    )

@require_auth
@handle_errors
async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a URL entry."""
    if not context.args:
        await update.message.reply_text("❌ Usage: `/delete <index>`", parse_mode='Markdown')
        return

    urls = load_urls()
    if not urls:
        await update.message.reply_text("📭 No URLs to delete.")
        return

    idx = validate_index(context.args[0], urls)
    if idx is None:
        await update.message.reply_text(f"❌ Invalid index. Use 1-{len(urls)}.")
        return

    removed = urls.pop(idx)
    save_urls(urls)
    
    await update.message.reply_text(f"🗑 Deleted: *{get_display_name(removed)}*", parse_mode='Markdown')

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Global error handler."""
    logger.exception("Unhandled exception: %s", context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "💥 An unexpected error occurred. Please try again or contact support."
        )

# === MAIN BOT SETUP ===
def main():
    """Initialize and run the bot."""
    app = ApplicationBuilder().token(TOKEN).build()

    # Register command handlers
    handlers = [
        CommandHandler("start", start),
        CommandHandler("view", view),
        CommandHandler("add", add),
        CommandHandler("edit", edit),
        CommandHandler("delete", delete),
    ]
    
    for handler in handlers:
        app.add_handler(handler)

    # Global error handler
    app.add_error_handler(error_handler)

    logger.info("🤖 URLWatch Bot is running. Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
