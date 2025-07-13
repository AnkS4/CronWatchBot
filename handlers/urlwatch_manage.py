from telegram import Update
from telegram.ext import ContextTypes
from functools import wraps
import yaml
from config.logging import logger
from helpers.urlwatch_helpers import load_urls, save_urls, validate_url, get_display_name, validate_index
from config import ALLOWED_USER_IDS

def require_auth(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ALLOWED_USER_IDS:
            logger.warning("Unauthorized access attempt by %s", update.effective_user.id)
            await update.message.reply_text("❌ Unauthorized access.")
            return
        return await func(update, context)
    return wrapper

def handle_errors(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            return await func(update, context)
        except Exception as e:
            logger.exception("Error in %s: %s", func.__name__, e)
            await update.message.reply_text("💥 An error occurred. Please try again or contact support.")
    return wrapper

@require_auth
@handle_errors
async def view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display all configured URLs with enhanced formatting."""
    logger.info("View command requested by %s", update.effective_user.id)
    urls = load_urls()
    if not urls:
        await update.message.reply_text("📭 *No URLs configured.*", parse_mode='Markdown')
        return
    msg_lines = ["📋 *Current URLs Monitored:*\n"]
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
    msg_lines.append("\n")
    await update.message.reply_text("\n".join(msg_lines), parse_mode='Markdown')
    return

@require_auth
@handle_errors
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a new URL to monitor with interactive setup."""
    logger.info("Add command requested by %s", update.effective_user.id)
    if not context.args:
        await update.message.reply_text(
            "❌ Usage: `/add <url> [name]`\n\n"
            "📝 *Examples:*\n"
            "`/add https://github.com/AnkS4/CronWatchBot`\n"
            " or `/add https://github.com/AnkS4/CronWatchBot CronWatchBot`\n"
            "💡 Use `/help` to see detailed usage help.",
            parse_mode='Markdown'
        )
        return
    new_url = context.args[0]
    # Handle schemaless URLs by prepending https:// if needed
    if not new_url.startswith(('http://', 'https://')):
        test_url = 'https://' + new_url
        if validate_url(test_url):
            new_url = test_url
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
        f"🔧 Use `/editfilter {len(urls)} <filters...>` to add filters\n"
        f"💡 Use `/help` to see detailed usage help.",
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
            xpath_value = filter_arg[6:]
            filters.append({'xpath': xpath_value})
        elif filter_arg.startswith('css:'):
            css_value = filter_arg[4:]
            filters.append({'css': css_value})
        elif filter_arg.startswith('element-by-id:'):
            id_value = filter_arg[14:]
            filters.append({'element-by-id': id_value})
        elif filter_arg.startswith('element-by-class:'):
            class_value = filter_arg[17:]
            filters.append({'element-by-class': class_value})
        elif filter_arg.startswith('element-by-tag:'):
            tag_value = filter_arg[15:]
            filters.append({'element-by-tag': tag_value})
        elif ':' in filter_arg and not filter_arg.startswith('http'):
            filter_type, filter_value = filter_arg.split(':', 1)
            filters.append({filter_type: filter_value})
        else:
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
        (
        f"✅ Updated filters for entry {idx+1}:\n"
            f"🔍 *New filters:*\n" + "\n".join(filter_display) +
            "\n\n🔧 Add it to crontab with `/crontab_add <job number> <minutes>`"
        ),
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
        logger.warning("Delete command requested by %s with no arguments", update.effective_user.id)
        await update.message.reply_text("❌ Usage: `/delete <index>`", parse_mode='Markdown')
        return
    urls = load_urls()
    if not urls:
        logger.warning("Delete command requested by %s with no URLs to delete", update.effective_user.id)
        await update.message.reply_text("📭 No URLs to delete.")
        return
    idx = validate_index(context.args[0], urls)
    if idx is None:
        logger.warning("Delete command requested by %s with invalid index %s", update.effective_user.id, context.args[0])
        await update.message.reply_text(f"❌ Invalid index. Use 1-{len(urls)}.")
        return
    removed = urls.pop(idx)
    save_urls(urls)
    logger.info("Delete command requested by %s with index %s", update.effective_user.id, context.args[0])
    await update.message.reply_text(f"🗑 Deleted: *{get_display_name(removed)}*", parse_mode='Markdown')
