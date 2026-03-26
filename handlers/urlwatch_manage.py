"""URL monitoring management handlers for the Telegram bot."""

import asyncio
from pathlib import Path
import shutil
import tempfile
from typing import TYPE_CHECKING, Any

from telegram import Update
from telegram.ext import ContextTypes
import yaml

from config.logging import logger
from handlers.shared import auth_and_error_handler, send_error, validate_args
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

MAX_OUTPUT_LENGTH = 3000
MIN_ARGS = 2

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes


async def _run_urlwatch_check(
    urlwatch_path: str, temp_file: str, entry: dict[str, Any], update: Update
) -> None:
    """Run urlwatch asynchronously and send results to user.

    Args:
        urlwatch_path: Path to urlwatch executable.
        temp_file: Path to temporary YAML file.
        entry: URL entry dictionary.
        update: Telegram update object.
    """
    process = await asyncio.create_subprocess_exec(
        urlwatch_path,
        "--test-filter",
        "1",
        "--urls",
        str(temp_file),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30.0)
        Path(temp_file).unlink(missing_ok=True)

        if process.returncode == 0 and stdout:
            output = stdout.decode().strip()
            if len(output) > MAX_OUTPUT_LENGTH:
                output = output[:MAX_OUTPUT_LENGTH] + "...\n\n*(output truncated)*"

            summary = f"✅ Current output for {get_display_name(entry)}:\n\n```\n{output}\n```"
            if update.message:
                await update.message.reply_text(summary, parse_mode="Markdown")
        else:
            error_msg = stderr.decode().strip() if stderr else "No output returned"
            if update.message:
                await update.message.reply_text(f"⚠️ {error_msg} for {get_display_name(entry)}")

    except TimeoutError:
        process.kill()
        await process.communicate()
        Path(temp_file).unlink(missing_ok=True)
        if update.message:
            await update.message.reply_text(
                f"⏰ Timeout checking output for {get_display_name(entry)}"
            )


def _auto_convert_type(value: str) -> bool | int | float | str:
    """Auto-convert string value to appropriate type.

    Attempts to convert string values to bool, int, or float if possible.
    Returns the original string if no conversion is applicable.

    Args:
        value: String value to convert.

    Returns:
        Converted value as bool, int, float, or original string.

    Examples:
        >>> _auto_convert_type("true")
        True
        >>> _auto_convert_type("42")
        42
        >>> _auto_convert_type("3.14")
        3.14
    """
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    if value.isdigit():
        return int(value)
    if value.replace(".", "", 1).isdigit():
        return float(value)
    return value


def _parse_filter_args(args: list[str]) -> list[Any]:
    """Parse filter arguments into urlwatch filter format."""
    filters: list[Any] = []
    for arg in args:
        if ":" in arg and not arg.startswith("http"):
            key, value = arg.split(":", 1)
            if "." in key:
                main_key, sub_key = key.split(".", 1)
                filters.append({main_key: {sub_key: value}})
            else:
                filters.append({key: value})
        else:
            filters.append(arg)
    return filters


def _parse_property_args(args: list[str]) -> dict[str, Any]:
    """Parse property arguments into a dictionary."""
    properties = {}
    for arg in args:
        if ":" not in arg:
            continue
        key, value = arg.split(":", 1)
        properties[key] = _auto_convert_type(value)
    return properties


async def _show_current_properties(update: Update, entry: dict[str, Any], idx: int) -> None:
    """Display current properties for a URL entry."""
    property_keys = ["timeout", "user_agent", "headers", "cookies", "ignore_connection_errors"]
    props_display = [f"• `{key}`: {entry[key]}" for key in property_keys if key in entry]

    if props_display and update.message:
        await update.message.reply_text(
            f"📋 Current properties for entry {idx + 1}:\n\n" + "\n".join(props_display),
            parse_mode="Markdown",
        )
    elif update.message:
        await update.message.reply_text(f"Entry {idx + 1} has no custom properties set.")


async def check_urls_exist(update: Update) -> list[dict[str, Any]] | None:
    """Check if URLs exist and send error message if not.

    Args:
        update: Telegram update object for sending error messages.

    Returns:
        List of URL entries if they exist, None otherwise.
    """
    urls = load_urls()
    if not urls:
        await send_error(update, "no_urls")
        return None
    return urls


async def validate_and_get_index(
    update: Update, idx_str: str, urls: list[dict[str, Any]]
) -> int | None:
    """Validate index string and send error message if invalid.

    Args:
        update: Telegram update object for sending error messages.
        idx_str: Index string to validate.
        urls: List of URL entries to validate against.

    Returns:
        Zero-based index if valid, None otherwise.
    """
    idx = validate_index(idx_str, urls)
    if idx is None:
        await send_error(update, "invalid_index", len(urls))
        return None
    return idx


@auth_and_error_handler
async def view_urls(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display all monitored URLs with their filters and properties.

    Args:
        update: Telegram update object containing the message.
        context: Telegram context for the command.

    Returns:
        None
    """
    if update.effective_user:
        logger.info("View command requested by %s", update.effective_user.id)
    urls = await check_urls_exist(update)
    if urls is None:
        return

    msg = ["📋 *URLs:*\n"]
    for i, entry in enumerate(urls, 1):
        name = get_display_name(entry)
        msg.append(f"*{i}. {name}*\n   🌐 `{entry.get('url', 'No URL')}`")

        if filters := entry.get("filter"):
            filters_str = (
                ", ".join(str(f) for f in filters) if isinstance(filters, list) else str(filters)
            )
            msg.append(f"   🔎 `{filters_str}`")

        if props := [f"{k}: {v}" for k, v in entry.items() if k not in ("name", "url", "filter")]:
            msg.append(f"   ⚙️ `{'; '.join(props)}`")

    if update.message:
        await update.message.reply_text("\n".join(msg), parse_mode="Markdown")


@auth_and_error_handler
@validate_args(
    1, "❌ Usage: `/add <url> [name]`\n📝 Example: `/add https://github.com/user/repo My Repo`"
)
async def add_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a new URL to monitor.

    Args:
        update: Telegram update object containing the message.
        context: Telegram context containing command arguments [url, optional_name...].

    Returns:
        None
    """
    if update.effective_user:
        logger.info("Add command requested by %s", update.effective_user.id)
    if not context.args:
        return
    new_url = context.args[0]
    if not new_url.startswith(("http://", "https://")):
        new_url = "https://" + new_url

    if not validate_url(new_url):
        await send_error(update, "invalid_url")
        return

    urls = load_urls()
    if any(entry.get("url") == new_url for entry in urls):
        await send_error(update, "url_exists")
        return

    name = " ".join(context.args[1:]) if context.args and len(context.args) > 1 else new_url
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
        await update.message.reply_text(summary, parse_mode="Markdown")


@auth_and_error_handler
@validate_args(2, "❌ Usage: `/edit <index> <url> [name]`")
async def edit_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Edit an existing URL entry.

    Args:
        update: Telegram update object containing the message.
        context: Telegram context containing command arguments [index, url, optional_name...].

    Returns:
        None
    """
    if update.effective_user:
        logger.info("Edit command requested by %s", update.effective_user.id)
    urls = await check_urls_exist(update)
    if urls is None:
        return

    if not context.args:
        return
    idx = await validate_and_get_index(update, context.args[0], urls)
    if idx is None:
        return

    if len(context.args) < MIN_ARGS:
        return
    new_url = context.args[1]
    if not validate_url(new_url):
        await send_error(update, "invalid_url")
        return

    name = (
        " ".join(context.args[2:])
        if context.args and len(context.args) > MIN_ARGS
        else urls[idx].get("name", new_url)
    )
    old_name = get_display_name(urls[idx])
    urls[idx].update({"name": name, "url": new_url})

    if not save_urls(urls):
        if update.message:
            await update.message.reply_text("❌ Failed to save changes. Please try again.")
        return

    logger.info("Updated entry %s: %s → %s", idx + 1, old_name, name)
    if update.message:
        await update.message.reply_text(
            f"✅ Updated URL entry {idx + 1}:\n\n{format_url_summary(urls[idx], idx + 1)}",
            parse_mode="Markdown",
        )


@auth_and_error_handler
@validate_args(
    1,
    """❌ Usage: `/editfilter <index> [filters...]`
📝 Examples:
• `/editfilter 1` - Remove filters
• `/editfilter 1 html2text strip`
• `/editfilter 1 xpath://*[@id="price"] html2text`
• `/editfilter 1 css.selector:span.titleline > a html2text` - Nested filters""",
)
async def edit_url_filters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Edit or remove filters for a URL entry.

    Args:
        update: Telegram update object containing the message.
        context: Telegram context containing command arguments [index, optional_filters...].

    Returns:
        None
    """
    if update.effective_user:
        logger.info("EditFilter command requested by %s", update.effective_user.id)
    urls = await check_urls_exist(update)
    if urls is None:
        return

    if not context.args:
        return
    idx = await validate_and_get_index(update, context.args[0], urls)
    if idx is None:
        return

    if len(context.args) == 1:
        urls[idx].pop("filter", None)
        if not save_urls(urls):
            if update.message:
                await update.message.reply_text("❌ Failed to save changes. Please try again.")
            return
        if update.message:
            await update.message.reply_text(
                f"✅ Removed filters from entry {idx + 1}:\n\n{format_url_summary(urls[idx], idx + 1)}",
                parse_mode="Markdown",
            )
        return

    if not context.args or len(context.args) < MIN_ARGS:
        return
    filters = _parse_filter_args(context.args[1:])

    urls[idx]["filter"] = filters

    if not save_urls(urls):
        if update.message:
            await update.message.reply_text("❌ Failed to save changes. Please try again.")
        return

    if update.message:
        # Provide detailed feedback about the updated filters
        entry = urls[idx]
        summary = f"✅ Updated filters for entry {idx + 1}:\n\n{format_url_summary(entry, idx + 1)}"
        await update.message.reply_text(summary, parse_mode="Markdown")


@auth_and_error_handler
@validate_args(
    1,
    """❌ Usage: `/editprop <index> [prop:value...]`
📝 Examples:
• `/editprop 1` - Show properties
• `/editprop 1 timeout:30`
• `/editprop 1 user_agent:MyBot headers.Accept:text/html`""",
)
async def edit_url_properties(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Edit or view properties for a URL entry.

    Args:
        update: Telegram update object containing the message.
        context: Telegram context containing command arguments [index, optional_properties...].

    Returns:
        None
    """
    if update.effective_user:
        logger.info("EditProperty command requested by %s", update.effective_user.id)
    urls = await check_urls_exist(update)
    if urls is None:
        return

    if not context.args:
        return
    idx = await validate_and_get_index(update, context.args[0], urls)
    if idx is None:
        return

    if context.args and len(context.args) == 1:
        await _show_current_properties(update, urls[idx], idx)
        return

    if not context.args or len(context.args) < MIN_ARGS:
        return
    properties = _parse_property_args(context.args[1:])

    if not properties:
        if update.message:
            await update.message.reply_text(
                f"⚠️ No valid properties were provided for entry {idx + 1}"
            )
        return

    for key, value in properties.items():
        if "." in key:
            keys = key.split(".")
            current = urls[idx]
            for k in keys[:-1]:
                current = current.setdefault(k, {})
            current[keys[-1]] = value
        else:
            urls[idx][key] = value

    if not save_urls(urls):
        if update.message:
            await update.message.reply_text("❌ Failed to save changes. Please try again.")
        return

    if update.message:
        await update.message.reply_text(
            f"✅ Updated properties for entry {idx + 1}:\n\n{format_url_summary(urls[idx], idx + 1)}",
            parse_mode="Markdown",
        )


@auth_and_error_handler
@validate_args(1, "❌ Usage: `/delete <index>`")
async def delete_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete a URL entry and update associated cron jobs.

    Args:
        update: Telegram update object containing the message.
        context: Telegram context containing command arguments [index].

    Returns:
        None
    """
    if update.effective_user:
        logger.info("Delete command requested by %s", update.effective_user.id)
    urls = await check_urls_exist(update)
    if urls is None:
        return

    if not context.args:
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
    msg = f"🗑 Deleted URL entry:\n\n{format_url_summary(removed, idx + 1)}"

    if deleted_job_existed:
        msg += "\n\n⏰ Removed associated crontab job"

    if updated_indices:
        msg += f"\n🔄 Updated {len(updated_indices)} crontab job(s) to new indices"

    if update.message:
        await update.message.reply_text(msg, parse_mode="Markdown")


@auth_and_error_handler
@validate_args(1, "❌ Usage: `/check <index>`\n📝 Example: `/check 1`")
async def check_url_output(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check and display current output of a URL with its filters applied.

    Args:
        update: Telegram update object containing the message.
        context: Telegram context containing command arguments [index].

    Returns:
        None
    """
    if update.effective_user:
        logger.info("Check command requested by %s", update.effective_user.id)
    urls = await check_urls_exist(update)
    if urls is None:
        return

    if not context.args:
        return
    idx = await validate_and_get_index(update, context.args[0], urls)
    if idx is None:
        return

    entry = urls[idx]
    if update.message:
        await update.message.reply_text(f"🔍 Checking output for {get_display_name(entry)}...")

    temp_file = None
    try:
        temp_entry = {
            "name": get_display_name(entry),
            "url": entry.get("url", ""),
            "filter": entry.get("filter", []),
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.safe_dump(temp_entry, f, sort_keys=False)
            temp_file = f.name

        urlwatch_path = shutil.which("urlwatch")
        if not urlwatch_path or not Path(urlwatch_path).is_file():
            if update.message:
                await update.message.reply_text("❌ urlwatch command not found in PATH")
            return

        await _run_urlwatch_check(urlwatch_path, temp_file, entry, update)

    except Exception as e:
        logger.error("Error checking URL output: %s", e)
        if temp_file:
            Path(temp_file).unlink(missing_ok=True)
        if update.message:
            await update.message.reply_text(f"❌ Failed to check output: {e!s}")
