from telegram import Update
from telegram.ext import ContextTypes
import yaml
from config.logging import logger
from helpers.urlwatch_helpers import load_urls, save_urls, validate_url, get_display_name, validate_index
from .shared import auth_and_error_handler, validate_args

@auth_and_error_handler
async def view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display all URLs."""
    logger.info("View command requested by %s", update.effective_user.id)
    urls = load_urls()
    if not urls:
        await update.message.reply_text("📭 *No URLs configured.*", parse_mode='Markdown')
        return
    
    msg = ["📋 *URLs:*\n"]
    for i, entry in enumerate(urls, 1):
        name = get_display_name(entry)
        msg.append(f"*{i}. {name}*\n   🌐 `{entry.get('url', 'No URL')}`")
        
        # Show filters and properties concisely
        if 'filter' in entry and entry['filter']:
            filters = entry['filter']
            filters_str = ', '.join(str(f) for f in filters) if isinstance(filters, list) else str(filters)
            msg.append(f"   🔎 `{filters_str}`")
        
        props = [f"{k}: {v}" for k, v in entry.items() if k not in ('name', 'url', 'filter')]
        if props:
            msg.append(f"   ⚙️ `{'; '.join(props)}`")
    
    await update.message.reply_text("\n".join(msg), parse_mode='Markdown')

@auth_and_error_handler
@validate_args(1, "❌ Usage: `/add <url> [name]`\n📝 Example: `/add https://github.com/user/repo My Repo`")
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add new URL."""
    new_url = context.args[0]
    if not new_url.startswith(('http://', 'https://')):
        new_url = 'https://' + new_url
    
    if not validate_url(new_url):
        await update.message.reply_text("❌ Invalid URL.")
        return
    
    urls = load_urls()
    if any(entry.get('url') == new_url for entry in urls):
        await update.message.reply_text("⚠ URL already exists.")
        return
    
    name = " ".join(context.args[1:]) if len(context.args) > 1 else new_url
    urls.append({"name": name, "url": new_url})
    save_urls(urls)
    
    await update.message.reply_text(
        f"✅ Added: *{name}*\n📋 Entry #{len(urls)} created.",
        parse_mode='Markdown'
    )

@auth_and_error_handler
@validate_args(2, "❌ Usage: `/edit <index> <url> [name]`")
async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edit URL entry."""
    urls = load_urls()
    if not urls:
        await update.message.reply_text("📭 No URLs to edit.")
        return
    
    idx = validate_index(context.args[0], urls)
    if idx is None:
        await update.message.reply_text(f"❌ Invalid index. Use 1-{len(urls)}.")
        return
    
    new_url = context.args[1]
    if not validate_url(new_url):
        await update.message.reply_text("❌ Invalid URL.")
        return
    
    name = " ".join(context.args[2:]) if len(context.args) > 2 else new_url
    old_name = get_display_name(urls[idx])
    urls[idx].update({"name": name, "url": new_url})
    save_urls(urls)
    
    await update.message.reply_text(
        f"✅ Updated entry {idx+1}: *{old_name}* → *{name}*",
        parse_mode='Markdown'
    )

@auth_and_error_handler
@validate_args(1, """❌ Usage: `/editfilter <index> [filters...]`
📝 Examples:
• `/editfilter 1` - Remove filters
• `/editfilter 1 html2text strip`
• `/editfilter 1 xpath://*[@id="price"] html2text`""")
async def edit_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edit filters."""
    urls = load_urls()
    if not urls:
        await update.message.reply_text("📭 No URLs to edit.")
        return
    
    idx = validate_index(context.args[0], urls)
    if idx is None:
        await update.message.reply_text(f"❌ Invalid index. Use 1-{len(urls)}.")
        return
    
    if len(context.args) == 1:
        urls[idx].pop('filter', None)
        save_urls(urls)
        await update.message.reply_text(f"✅ Removed filters from entry {idx+1}")
        return
    
    filters = []
    for arg in context.args[1:]:
        if ':' in arg and not arg.startswith('http'):
            key, value = arg.split(':', 1)
            filters.append({key: value})
        else:
            filters.append(arg)
    
    urls[idx]['filter'] = filters
    save_urls(urls)
    
    await update.message.reply_text(
        f"✅ Updated filters for entry {idx+1}",
        parse_mode='Markdown'
    )

@auth_and_error_handler
@validate_args(1, """❌ Usage: `/editprop <index> [prop:value...]`
📝 Examples:
• `/editprop 1` - Show properties
• `/editprop 1 timeout:30`
• `/editprop 1 user_agent:MyBot headers.Accept:text/html`""")
async def edit_property(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edit properties."""
    urls = load_urls()
    if not urls:
        await update.message.reply_text("📭 No URLs to edit.")
        return
    
    idx = validate_index(context.args[0], urls)
    if idx is None:
        await update.message.reply_text(f"❌ Invalid index. Use 1-{len(urls)}.")
        return
    
    if len(context.args) == 1:
        props = {k: v for k, v in urls[idx].items() if k not in ['name', 'url', 'filter']}
        if not props:
            await update.message.reply_text(f"📋 Entry {idx+1} has no properties.")
            return
        prop_text = "\n".join([f"   {k}: `{v}`" for k, v in props.items()])
        await update.message.reply_text(f"📋 Properties for entry {idx+1}:\n{prop_text}", parse_mode='Markdown')
        return
    
    for arg in context.args[1:]:
        if ':' not in arg:
            continue
        key, value = arg.split(':', 1)
        # Handle nested properties
        if '.' in key:
            main_key, sub_key = key.split('.', 1)
            if main_key not in urls[idx]:
                urls[idx][main_key] = {}
            urls[idx][main_key][sub_key] = value
        else:
            # Auto-convert types
            if value.lower() in ('true', 'false'):
                value = value.lower() == 'true'
            elif value.isdigit():
                value = int(value)
            elif value.replace('.', '', 1).isdigit():
                value = float(value)
            urls[idx][key] = value
    
    save_urls(urls)
    await update.message.reply_text(f"✅ Updated properties for entry {idx+1}")

@auth_and_error_handler
@validate_args(1, "❌ Usage: `/delete <index>`")
async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete URL entry."""
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
