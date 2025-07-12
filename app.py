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
from config import TOKEN, ALLOWED_USER_IDS
from crontab import CronTab

# Dynamically resolve the user's urlwatch configuration file path
URLS_FILE = os.path.expanduser("~/.config/urlwatch/urls.yaml")

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

# === CRONTAB MANAGEMENT HELPERS ===
def get_cron():
    return CronTab(user=True)

def list_urlwatch_jobs():
    cron = get_cron()
    jobs = [job for job in cron if job.comment and job.comment.startswith('urlwatch-bot-')]
    return jobs

def build_urlwatch_command(job_index: int) -> str:
    # Adjust this command to match your urlwatch invocation
    return f"urlwatch --jobs {job_index}"

# === BOT COMMAND HANDLERS ===
@require_auth
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a detailed help message with all commands."""
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
   `/crontab_add <minutes> <job number>`
   ```
   /crontab_add 60 1
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
   `/crontab_add <minutes> <job_index>`
   ```
   /crontab_add 15 2
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

@require_auth
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message with available commands."""
    await update.message.reply_text(
        """
🤖 *Welcome to CronWatchBot!*

*🚀 Getting Started:*
Step 1. To start watching a website, type: `/add <url> [optional name]`
```
/add https://www.github.com/AnkS4/CronWatchBot CronWatchBot
```
Step 2. To schedule automatic checks, type: `/crontab_add <minutes> <job number>`
```
/crontab_add 60 1
```

💡 _Tip: Use_ `/help` _to see detailed usage help._
        """,
        parse_mode='Markdown'
    )

@require_auth
@handle_errors
async def view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display all configured URLs with enhanced formatting."""
    urls = load_urls()
    if not urls:
        await update.message.reply_text("📭 *No URLs configured.*", parse_mode='Markdown')
        return

    msg_lines = ["📋 *Current URLs Monitored:*\n━━━━━━━━━━━━━━━━━━━━━━"]
    for i, entry in enumerate(urls, 1):
        name = get_display_name(entry)
        url = entry.get('url', 'No URL')
        msg_lines.append(f"\n*{i}. {name}*\n   🌐 `{url}`")
        # Show filters if present
        if 'filter' in entry and entry['filter']:
            filters = entry['filter']
            if isinstance(filters, list):
                filters_str = ', '.join(str(f) for f in filters)
            else:
                filters_str = str(filters)
            msg_lines.append(f"   🔎 Filters: `{filters_str}`")
        # Show properties if present
        props = [k for k in entry.keys() if k not in ('name', 'url', 'filter')]
        if props:
            for prop in props:
                msg_lines.append(f"   ⚙️ {prop}: `{entry[prop]}`")
    msg_lines.append("\n━━━━━━━━━━━━━━━━━━━━━━")
    await update.message.reply_text("\n".join(msg_lines), parse_mode='Markdown')


    """Display all configured URLs with complete details."""
    urls = load_urls()
    
    if not urls:
        await update.message.reply_text("📭 No URLs configured.")
        return
    
    msg_lines = ["📋 *Current URLs:*\n"]
    for i, entry in enumerate(urls, 1):
        name = get_display_name(entry)
        url = entry.get('url', 'No URL')
        
        # Start entry display
        msg_lines.append(f"*{i}. {name}*")
        msg_lines.append(f"   🌐 URL: `{url}`")
        
        # Show filters if they exist
        if 'filter' in entry and entry['filter']:
            msg_lines.append("   🔍 Filters:")
            for j, filter_item in enumerate(entry['filter'], 1):
                if isinstance(filter_item, dict):
                    # Handle complex filter objects
                    filter_str = yaml.dump(filter_item, default_flow_style=False).strip()
                    msg_lines.append(f"      {j}. `{filter_str}`")
                else:
                    # Handle simple string filters
                    msg_lines.append(f"      {j}. `{filter_item}`")
        
        # Show other properties if they exist
        other_props = {k: v for k, v in entry.items() if k not in ['name', 'url', 'filter']}
        if other_props:
            msg_lines.append("   ⚙ Other properties:")
            for key, value in other_props.items():
                if isinstance(value, (dict, list)):
                    value_str = yaml.dump(value, default_flow_style=False).strip()
                    msg_lines.append(f"      {key}: `{value_str}`")
                else:
                    msg_lines.append(f"      {key}: `{value}`")
        
        msg_lines.append("")  # Empty line between entries
    
    # Split message if too long for Telegram
    full_message = "\n".join(msg_lines)
    if len(full_message) > 4096:
        # Send in chunks
        chunks = []
        current_chunk = ["📋 *Current URLs:*\n"]
        
        for i, entry in enumerate(urls, 1):
            entry_lines = []
            name = get_display_name(entry)
            url = entry.get('url', 'No URL')
            
            entry_lines.append(f"*{i}. {name}*")
            entry_lines.append(f"   🌐 URL: `{url}`")
            
            if 'filter' in entry and entry['filter']:
                entry_lines.append("   🔍 Filters:")
                for j, filter_item in enumerate(entry['filter'], 1):
                    if isinstance(filter_item, dict):
                        filter_str = yaml.dump(filter_item, default_flow_style=False).strip()
                        entry_lines.append(f"      {j}. `{filter_str}`")
                    else:
                        entry_lines.append(f"      {j}. `{filter_item}`")
            
            other_props = {k: v for k, v in entry.items() if k not in ['name', 'url', 'filter']}
            if other_props:
                entry_lines.append("   ⚙ Other properties:")
                for key, value in other_props.items():
                    if isinstance(value, (dict, list)):
                        value_str = yaml.dump(value, default_flow_style=False).strip()
                        entry_lines.append(f"      {key}: `{value_str}`")
                    else:
                        entry_lines.append(f"      {key}: `{value}`")
            
            entry_lines.append("")
            
            entry_text = "\n".join(entry_lines)
            if len("\n".join(current_chunk + entry_lines)) > 4000:
                chunks.append("\n".join(current_chunk))
                current_chunk = [f"📋 *Current URLs (continued):*\n"] + entry_lines
            else:
                current_chunk.extend(entry_lines)
        
        if current_chunk:
            chunks.append("\n".join(current_chunk))
        
        for chunk in chunks:
            await update.message.reply_text(chunk, parse_mode='Markdown')
    else:
        await update.message.reply_text(full_message, parse_mode='Markdown')

@require_auth
@handle_errors
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a new URL to monitor with interactive setup."""
    if not context.args:
        await update.message.reply_text(
            "❌ Usage: `/add <url> [name]`\n\n"
            "📝 *Examples:*\n"
            "`/add https://example.com`\n"
            "`/add https://example.com My Website`\n\n"
            "💡 After adding, you can use `/editfilter <index>` to add filters.",
            parse_mode='Markdown'
        )
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
    
    await update.message.reply_text(
        f"✅ Added: *{custom_name}*\n\n"
        f"📋 Entry #{len(urls)} created with basic configuration.\n"
        f"🔧 Use `/editfilter {len(urls)}` to add filters\n"
        f"🔧 Use `/editprop {len(urls)}` to add other properties",
        parse_mode='Markdown'
    )

@require_auth
@handle_errors
async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edit basic URL entry (name and URL only)."""
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Usage: `/edit <index> <url> [name]`\n\n"
            "📝 *Examples:*\n"
            "`/edit 1 https://newurl.com`\n"
            "`/edit 1 https://newurl.com New Name`\n\n"
            "💡 *Other edit commands:*\n"
            "🔧 `/editfilter <index>` - Edit filters\n"
            "🔧 `/editprop <index>` - Edit other properties",
            parse_mode='Markdown'
        )
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
    urls[idx] = {**old_entry, "name": new_name, "url": new_url}
    
    save_urls(urls)
    
    await update.message.reply_text(
        f"✅ Updated entry {idx+1}:\n"
        f"*Old:* {get_display_name(old_entry)}\n"
        f"*New:* {new_name}",
        parse_mode='Markdown'
    )

@require_auth
@handle_errors
async def edit_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edit filters for a URL entry."""
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Usage: `/editfilter <index> [filter1] [filter2] ...`\n\n"
            "📝 *Examples:*\n"
            "`/editfilter 1` - Remove all filters\n"
            "`/editfilter 1 html2text strip` - Set simple filters\n"
            "`/editfilter 1 xpath://*[@id=\"price\"] html2text strip`\n"
            "`/editfilter 1 element-by-id:ProductPrice html2text`\n\n"
            "💡 *Filter types:*\n"
            "• `html2text` - Convert HTML to text\n"
            "• `strip` - Remove whitespace\n"
            "• `element-by-id:ID` - Select by element ID\n"
            "• `element-by-class:CLASS` - Select by class\n"
            "• `xpath:XPATH` - Select by XPath\n"
            "• `css:SELECTOR` - Select by CSS selector",
            parse_mode='Markdown'
        )
        return

    urls = load_urls()
    if not urls:
        await update.message.reply_text("📭 No URLs to edit.")
        return

    idx = validate_index(context.args[0], urls)
    if idx is None:
        await update.message.reply_text(f"❌ Invalid index. Use 1-{len(urls)}.")
        return

    if len(context.args) == 1:
        # Remove all filters
        if 'filter' in urls[idx]:
            del urls[idx]['filter']
        save_urls(urls)
        await update.message.reply_text(f"✅ Removed all filters from entry {idx+1}")
        return

    # Parse new filters
    filters = []
    for filter_arg in context.args[1:]:
        # Handle different filter formats
        if filter_arg.startswith('xpath:'):
            # XPath filter
            xpath_value = filter_arg[6:]  # Remove 'xpath:' prefix
            filters.append({'xpath': xpath_value})
        elif filter_arg.startswith('css:'):
            # CSS selector filter
            css_value = filter_arg[4:]  # Remove 'css:' prefix
            filters.append({'css': css_value})
        elif filter_arg.startswith('element-by-id:'):
            # Element by ID filter
            id_value = filter_arg[14:]  # Remove 'element-by-id:' prefix
            filters.append({'element-by-id': id_value})
        elif filter_arg.startswith('element-by-class:'):
            # Element by class filter
            class_value = filter_arg[17:]  # Remove 'element-by-class:' prefix
            filters.append({'element-by-class': class_value})
        elif filter_arg.startswith('element-by-tag:'):
            # Element by tag filter
            tag_value = filter_arg[15:]  # Remove 'element-by-tag:' prefix
            filters.append({'element-by-tag': tag_value})
        elif ':' in filter_arg and not filter_arg.startswith('http'):
            # Handle other complex filters generically
            filter_type, filter_value = filter_arg.split(':', 1)
            filters.append({filter_type: filter_value})
        else:
            # Handle simple filters like "html2text", "strip"
            filters.append(filter_arg)

    urls[idx]['filter'] = filters
    save_urls(urls)
    
    filter_display = []
    for i, f in enumerate(filters, 1):
        if isinstance(f, dict):
            filter_str = yaml.dump(f, default_flow_style=False).strip()
            filter_display.append(f"   {i}. `{filter_str}`")
        else:
            filter_display.append(f"   {i}. `{f}`")
    
    await update.message.reply_text(
        f"✅ Updated filters for entry {idx+1}:\n"
        f"🔍 *New filters:*\n" + "\n".join(filter_display),
        parse_mode='Markdown'
    )

@require_auth
@handle_errors
async def edit_property(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edit other properties for a URL entry."""
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Usage: `/editprop <index> [property:value] ...`\n\n"
            "📝 *Examples:*\n"
            "`/editprop 1` - Show current properties\n"
            "`/editprop 1 timeout:30` - Set timeout\n"
            "`/editprop 1 user_agent:MyBot headers.Accept:text/html`\n\n"
            "💡 *Common properties:*\n"
            "• `timeout:30` - Request timeout\n"
            "• `user_agent:MyBot` - Custom user agent\n"
            "• `headers.Accept:text/html` - HTTP headers\n"
            "• `encoding:utf-8` - Text encoding\n"
            "• `ignore_connection_errors:true` - Ignore errors",
            parse_mode='Markdown'
        )
        return

    urls = load_urls()
    if not urls:
        await update.message.reply_text("📭 No URLs to edit.")
        return

    idx = validate_index(context.args[0], urls)
    if idx is None:
        await update.message.reply_text(f"❌ Invalid index. Use 1-{len(urls)}.")
        return

    if len(context.args) == 1:
        # Show current properties
        entry = urls[idx]
        props = {k: v for k, v in entry.items() if k not in ['name', 'url', 'filter']}
        if not props:
            await update.message.reply_text(f"📋 Entry {idx+1} has no additional properties.")
            return
        
        prop_lines = []
        for key, value in props.items():
            if isinstance(value, (dict, list)):
                value_str = yaml.dump(value, default_flow_style=False).strip()
                prop_lines.append(f"   {key}: `{value_str}`")
            else:
                prop_lines.append(f"   {key}: `{value}`")
        
        await update.message.reply_text(
            f"📋 Properties for entry {idx+1}:\n" + "\n".join(prop_lines),
            parse_mode='Markdown'
        )
        return

    # Parse and set properties
    updated_props = []
    for prop_arg in context.args[1:]:
        if ':' not in prop_arg:
            await update.message.reply_text(f"❌ Invalid property format: `{prop_arg}`. Use format: `key:value`")
            return
        
        try:
            key, value = prop_arg.split(':', 1)
            
            # Handle nested properties like "headers.Accept"
            if '.' in key:
                main_key, sub_key = key.split('.', 1)
                if main_key not in urls[idx]:
                    urls[idx][main_key] = {}
                urls[idx][main_key][sub_key] = value
                updated_props.append(f"{main_key}.{sub_key}")
            else:
                # Convert boolean and numeric values
                if value.lower() in ('true', 'false'):
                    value = value.lower() == 'true'
                elif value.isdigit():
                    value = int(value)
                elif value.replace('.', '', 1).isdigit():
                    value = float(value)
                
                urls[idx][key] = value
                updated_props.append(key)
        except Exception as e:
            await update.message.reply_text(f"❌ Error setting property `{prop_arg}`: {str(e)}")
            return

    save_urls(urls)
    await update.message.reply_text(
        f"✅ Updated properties for entry {idx+1}:\n" + 
        "\n".join([f"• `{prop}`" for prop in updated_props])
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

# === CRONTAB BOT COMMANDS ===
@require_auth
@handle_errors
async def crontab_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jobs = list_urlwatch_jobs()
    if not jobs:
        await update.message.reply_text("🕑 *No urlwatch jobs found in crontab.*\nUse `/crontab_add` to add one.", parse_mode='Markdown')
        return
    msg = ["🕑 *Scheduled urlwatch jobs in crontab:*\n━━━━━━━━━━━━━━━━━━━━━━"]
    for idx, job in enumerate(jobs, 1):
        msg.append(f"\n*{idx}.* ⏰ `{job.slices}`\n   📝 `{job.command}`")
    msg.append("\n━━━━━━━━━━━━━━━━━━━━━━")
    await update.message.reply_text("\n".join(msg), parse_mode='Markdown')


@require_auth
@handle_errors
async def crontab_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Add a scheduled urlwatch job to run every N minutes.
    Usage: /crontab_add <minutes> <job_index>
    Example: /crontab_add 15 2
    """
    if len(context.args) != 2:
        await update.message.reply_text(
            "❌ Usage: `/crontab_add <minutes> <job_index>`\n"
            "📝 Example: `/crontab_add 15 2` (runs job 2 every 15 minutes)",
            parse_mode='Markdown'
        )
        return
    try:
        minutes = int(context.args[0])
        job_index_int = int(context.args[1])
        if minutes <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid arguments. Minutes must be a positive integer.\n"
            "Use `/crontab_view` to see available jobs.",
            parse_mode='Markdown'
        )
        return
    cron = get_cron()
    command = build_urlwatch_command(job_index_int)
    schedule = f"*/{minutes} * * * *"
    job = cron.new(command=command, comment=f"urlwatch-bot-{job_index_int}")
    job.setall(schedule)
    cron.write()
    await update.message.reply_text(
        f"✅ Added crontab job: `{job}`\nRuns every {minutes} minutes.",
        parse_mode='Markdown'
    )

@require_auth
@handle_errors
async def crontab_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 7:
        await update.message.reply_text(
            "❌ Usage: `/crontab_edit <index> <min> <hour> <dom> <month> <dow> <job_index>`\n"
            "📝 Example: `/crontab_edit 1 0 12 * * * 2`",
            parse_mode='Markdown'
        )
        return
    idx_str = context.args[0]
    schedule = context.args[1:6]
    job_index = context.args[6]
    try:
        idx = int(idx_str) - 1
        job_index_int = int(job_index)
    except ValueError:
        await update.message.reply_text("❌ Invalid index or job index.")
        return
    jobs = list_urlwatch_jobs()
    if idx < 0 or idx >= len(jobs):
        await update.message.reply_text(f"❌ Invalid job index. Use 1-{len(jobs)}.")
        return
    cron = get_cron()
    job = jobs[idx]
    job.setall(" ".join(schedule))
    job.set_command(build_urlwatch_command(job_index_int))
    job.set_comment(f"urlwatch-bot-{job_index}")
    cron.write()
    await update.message.reply_text(f"✏ Edited crontab job {idx+1}: `{job}`", parse_mode='Markdown')

@require_auth
@handle_errors
async def crontab_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: `/crontab_delete <index>`", parse_mode='Markdown')
        return
    try:
        idx = int(context.args[0]) - 1
    except ValueError:
        await update.message.reply_text("❌ Invalid index.")
        return
    jobs = list_urlwatch_jobs()
    if idx < 0 or idx >= len(jobs):
        await update.message.reply_text(f"❌ Invalid job index. Use 1-{len(jobs)}.")
        return
    cron = get_cron()
    cron.remove(jobs[idx])
    cron.write()
    await update.message.reply_text(f"🗑 Deleted crontab job {idx+1}.")

# === MAIN BOT SETUP ===
def main():
    """Initialize and run the bot."""
    app = ApplicationBuilder().token(TOKEN).build()

    # Register command handlers
    handlers = [
        app.add_handler(CommandHandler("start", start))
    ]
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("view", view))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("delete", delete))
    app.add_handler(CommandHandler("edit", edit))
    app.add_handler(CommandHandler("editfilter", edit_filter))
    app.add_handler(CommandHandler("editprop", edit_property))
    app.add_handler(CommandHandler("crontab_view", crontab_view))
    app.add_handler(CommandHandler("crontab_add", crontab_add))
    app.add_handler(CommandHandler("crontab_edit", crontab_edit))
    app.add_handler(CommandHandler("crontab_delete", crontab_delete))

    app.add_error_handler(error_handler)

    logger.info("🤖 URLWatch Bot is running. Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
