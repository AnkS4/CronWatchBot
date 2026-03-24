import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from telegram import Update
from telegram.ext import ContextTypes

from config.logging import logger
from helpers.crontab_helpers import (
    get_job_index_from_comment,
    list_urlwatch_jobs,
    update_crontab_indices_after_deletion,
)
from helpers.urlwatch_helpers import (
    format_url_summary,
    get_display_name,
    load_urls,
    save_urls,
    validate_index,
    validate_url,
)
from .shared import auth_and_error_handler, send_error, validate_args

def _auto_convert_type(value: str) -> Union[bool, int, float, str]:
    """Auto-convert string value to appropriate type."""
    if value.lower() in ('true', 'false'):
        return value.lower() == 'true'
    if value.isdigit():
        return int(value)
    if value.replace('.', '', 1).isdigit():
        return float(value)
    return value

async def check_urls_exist(update: Update) -> Optional[List[Dict[str, Any]]]:
    """Check if URLs exist and send error if not."""
    urls = load_urls()
    if not urls:
        await send_error(update, 'no_urls')
        return None
    return urls

async def validate_and_get_index(update: Update, idx_str: str, urls: List[Dict[str, Any]]) -> Optional[int]:
    """Validate index and send error if invalid."""
    idx = validate_index(idx_str, urls)
    if idx is None:
        await send_error(update, 'invalid_index', len(urls))
        return None
    return idx

@auth_and_error_handler
async def view_urls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display all URLs."""
    logger.info("View command requested by %s", update.effective_user.id)
    urls = await check_urls_exist(update)
    if urls is None:
        return

    msg = ["📋 *URLs:*\n"]
    for i, entry in enumerate(urls, 1):
        name = get_display_name(entry)
        msg.append(f"*{i}. {name}*\n   🌐 `{entry.get('url', 'No URL')}`")

        if filters := entry.get('filter'):
            filters_str = ', '.join(str(f) for f in filters) if isinstance(filters, list) else str(filters)
            msg.append(f"   🔎 `{filters_str}`")

        if props := [f"{k}: {v}" for k, v in entry.items() if k not in ('name', 'url', 'filter')]:
            msg.append(f"   ⚙️ `{'; '.join(props)}`")

    if update.message:
        await update.message.reply_text("\n".join(msg), parse_mode='Markdown')

@auth_and_error_handler
@validate_args(1, "❌ Usage: `/add <url> [name]`\n📝 Example: `/add https://github.com/user/repo My Repo`")
async def add_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add new URL."""
    logger.info("Add command requested by %s", update.effective_user.id)
    new_url = context.args[0]
    if not new_url.startswith(('http://', 'https://')):
        new_url = 'https://' + new_url

    if not validate_url(new_url):
        await send_error(update, 'invalid_url')
        return

    urls = load_urls()
    if any(entry.get('url') == new_url for entry in urls):
        await send_error(update, 'url_exists')
        return

    name = " ".join(context.args[1:]) if len(context.args) > 1 else new_url
    new_entry = {"name": name, "url": new_url}
    urls.append(new_entry)

    if not save_urls(urls):
        if update.message:
            await update.message.reply_text("❌ Failed to save changes. Please try again.")
        return

    logger.info("Added URL: %s", new_url)
    if update.message:
        # Provide detailed feedback about the added URL
        summary = f"✅ Added new URL entry:\n\n{format_url_summary(new_entry, len(urls))}\n\n📋 Entry #{len(urls)} created."
        await update.message.reply_text(summary, parse_mode='Markdown')

@auth_and_error_handler
@validate_args(2, "❌ Usage: `/edit <index> <url> [name]`")
async def edit_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edit URL entry."""
    logger.info("Edit command requested by %s", update.effective_user.id)
    urls = await check_urls_exist(update)
    if urls is None:
        return

    idx = await validate_and_get_index(update, context.args[0], urls)
    if idx is None:
        return

    new_url = context.args[1]
    if not validate_url(new_url):
        await send_error(update, 'invalid_url')
        return

    name = " ".join(context.args[2:]) if len(context.args) > 2 else new_url
    old_name = get_display_name(urls[idx])
    urls[idx].update({"name": name, "url": new_url})

    if not save_urls(urls):
        if update.message:
            await update.message.reply_text("❌ Failed to save changes. Please try again.")
        return

    logger.info("Updated entry %s: %s → %s", idx+1, old_name, name)
    if update.message:
        await update.message.reply_text(
            f"✅ Updated URL entry {idx+1}:\n\n{format_url_summary(urls[idx], idx+1)}",
            parse_mode='Markdown'
        )

@auth_and_error_handler
@validate_args(1, """❌ Usage: `/editfilter <index> [filters...]`
📝 Examples:
• `/editfilter 1` - Remove filters
• `/editfilter 1 html2text strip`
• `/editfilter 1 xpath://*[@id="price"] html2text`
• `/editfilter 1 css.selector:span.titleline > a html2text` - Nested filters""")
async def edit_url_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edit filters."""
    logger.info("EditFilter command requested by %s", update.effective_user.id)
    urls = await check_urls_exist(update)
    if urls is None:
        return

    idx = await validate_and_get_index(update, context.args[0], urls)
    if idx is None:
        return

    if len(context.args) == 1:
        urls[idx].pop('filter', None)
        if not save_urls(urls):
            if update.message:
                await update.message.reply_text("❌ Failed to save changes. Please try again.")
            return
        if update.message:
            await update.message.reply_text(f"✅ Removed filters from entry {idx+1}:\n\n{format_url_summary(urls[idx], idx+1)}", parse_mode='Markdown')
        return

    filters = []
    for arg in context.args[1:]:
        if ':' in arg and not arg.startswith('http'):
            key, value = arg.split(':', 1)
            # Support nested filters using dot notation (e.g., css.selector:value)
            if '.' in key:
                main_key, sub_key = key.split('.', 1)
                filters.append({main_key: {sub_key: value}})
            else:
                filters.append({key: value})
        else:
            filters.append(arg)

    urls[idx]['filter'] = filters

    if not save_urls(urls):
        if update.message:
            await update.message.reply_text("❌ Failed to save changes. Please try again.")
        return

    if update.message:
        # Provide detailed feedback about the updated filters
        entry = urls[idx]
        summary = f"✅ Updated filters for entry {idx+1}:\n\n{format_url_summary(entry, idx+1)}"
        await update.message.reply_text(summary, parse_mode='Markdown')

@auth_and_error_handler
@validate_args(1, """❌ Usage: `/editprop <index> [prop:value...]`
📝 Examples:
• `/editprop 1` - Show properties
• `/editprop 1 timeout:30`
• `/editprop 1 user_agent:MyBot headers.Accept:text/html`""")
async def edit_url_properties(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edit properties."""
    logger.info("EditProperty command requested by %s", update.effective_user.id)
    urls = await check_urls_exist(update)
    if urls is None:
        return

    idx = await validate_and_get_index(update, context.args[0], urls)
    if idx is None:
        return

    if len(context.args) == 1:
        if not (props := {k: v for k, v in urls[idx].items() if k not in ['name', 'url', 'filter']}):
            if update.message:
                await update.message.reply_text(f"📋 Entry {idx+1} has no properties.")
            return
        prop_text = "\n".join(f"   {k}: `{v}`" for k, v in props.items())
        if update.message:
            await update.message.reply_text(f"📋 Properties for entry {idx+1}:\n{prop_text}", parse_mode='Markdown')
        return

    reserved_keys = {'url', 'name', 'filter'}
    updated = False

    for arg in context.args[1:]:
        if ':' not in arg:
            continue
        key, value = arg.split(':', 1)

        if '.' in key:
            main_key, sub_key = key.split('.', 1)
            if main_key in reserved_keys:
                if update.message:
                    await update.message.reply_text(f"❌ Cannot modify reserved field: {main_key}")
                continue
            if main_key not in urls[idx]:
                urls[idx][main_key] = {}
            urls[idx][main_key][sub_key] = value
            updated = True
        else:
            if key in reserved_keys:
                if update.message:
                    await update.message.reply_text(f"❌ Cannot modify reserved field: {key}")
                continue
            urls[idx][key] = _auto_convert_type(value)
            updated = True

    if updated:
        if not save_urls(urls):
            if update.message:
                await update.message.reply_text("❌ Failed to save changes. Please try again.")
            return
        if update.message:
            await update.message.reply_text(f"✅ Updated properties for entry {idx+1}:\n\n{format_url_summary(urls[idx], idx+1)}", parse_mode='Markdown')
    elif update.message:
        await update.message.reply_text(f"⚠️ No valid properties were updated for entry {idx+1}")

@auth_and_error_handler
@validate_args(1, "❌ Usage: `/delete <index>`")
async def delete_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete URL entry."""
    logger.info("Delete command requested by %s", update.effective_user.id)
    urls = await check_urls_exist(update)
    if urls is None:
        return

    idx = await validate_and_get_index(update, context.args[0], urls)
    if idx is None:
        return

    removed = urls.pop(idx)

    if not save_urls(urls):
        if update.message:
            await update.message.reply_text("❌ Failed to save changes. Please try again.")
        return

    # Sync crontab indices after deletion
    # Check if deleted entry had a crontab job
    jobs = list_urlwatch_jobs()
    deleted_job_existed = any(get_job_index_from_comment(job.comment) == idx + 1 for job in jobs)

    # Update crontab indices
    updated_indices = update_crontab_indices_after_deletion(idx + 1)

    # Build notification message
    msg = f"🗑 Deleted URL entry:\n\n{format_url_summary(removed, idx+1)}"

    if deleted_job_existed:
        msg += f"\n\n⏰ Removed associated crontab job"

    if updated_indices:
        msg += f"\n🔄 Updated {len(updated_indices)} crontab job(s) to new indices"

    if update.message:
        await update.message.reply_text(msg, parse_mode='Markdown')

@auth_and_error_handler
@validate_args(1, "❌ Usage: `/check <index>`\n📝 Example: `/check 1`")
async def check_url_output(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check current output of a URL with its filters."""
    logger.info("Check command requested by %s", update.effective_user.id)
    urls = await check_urls_exist(update)
    if urls is None:
        return

    idx = await validate_and_get_index(update, context.args[0], urls)
    if idx is None:
        return

    entry = urls[idx]
    url = entry.get('url', '')
    filters = entry.get('filter', [])

    if update.message:
        await update.message.reply_text(f"🔍 Checking output for {get_display_name(entry)}...")

    try:
        temp_entry = {
            'name': get_display_name(entry),
            'url': url,
            'filter': filters
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.safe_dump(temp_entry, f, sort_keys=False)
            temp_file = f.name

        # Run urlwatch on this single entry
        result = subprocess.run(
            ['urlwatch', '--urls', temp_file, '--verbose'],
            capture_output=True,
            text=True,
            timeout=30
        )

        # Clean up
        Path(temp_file).unlink(missing_ok=True)

        if result.returncode == 0 and result.stdout:
            output = result.stdout.strip()
            # Limit output length to avoid Telegram message limits
            if len(output) > 3000:
                output = output[:3000] + "...\n\n*(output truncated)*"

            summary = f"✅ Current output for {get_display_name(entry)}:\n\n```\n{output}\n```"
            await update.message.reply_text(summary, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"⚠️ No output returned for {get_display_name(entry)}")

    except subprocess.TimeoutExpired:
        await update.message.reply_text(f"⏰ Timeout checking output for {get_display_name(entry)}")
    except Exception as e:
        logger.error("Error checking URL output: %s", e)
        await update.message.reply_text(f"❌ Failed to check output: {str(e)}")
