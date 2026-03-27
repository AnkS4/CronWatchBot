"""Tests for URL management handlers."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from telegram import Update, User
from telegram.ext import ContextTypes

from handlers.urlwatch_manage import (
    add_url,
    check_url_output,
    check_urls_exist,
    delete_url,
    edit_url,
    edit_url_filters,
    edit_url_properties,
    validate_and_get_index,
    view_urls,
)


@pytest.fixture
def temp_urls_file(tmp_path, monkeypatch):
    """Create a temporary URLs file for testing."""
    urls_file = tmp_path / "urls.yaml"
    monkeypatch.setattr("helpers.urlwatch_helpers.URLS_FILE", str(urls_file))
    return urls_file


# Tests for check_urls_exist


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.load_urls")
async def test_check_urls_exist_with_urls(mock_load_urls, mock_update):
    """Test check_urls_exist when URLs exist."""
    mock_load_urls.return_value = [{"url": "https://example.com"}]

    result = await check_urls_exist(mock_update)

    assert result == [{"url": "https://example.com"}]
    mock_update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.load_urls")
async def test_check_urls_exist_no_urls(mock_load_urls, mock_update):
    """Test check_urls_exist when no URLs exist."""
    mock_load_urls.return_value = []

    result = await check_urls_exist(mock_update)

    assert result is None
    mock_update.message.reply_text.assert_called_once()


# Tests for validate_and_get_index


@pytest.mark.asyncio
async def test_validate_and_get_index_valid(mock_update):
    """Test validating a valid index."""
    urls = [{"url": "https://example.com"}]

    result = await validate_and_get_index(mock_update, "1", urls)

    assert result == 0
    mock_update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_validate_and_get_index_invalid(mock_update):
    """Test validating an invalid index."""
    urls = [{"url": "https://example.com"}]

    result = await validate_and_get_index(mock_update, "99", urls)

    assert result is None
    mock_update.message.reply_text.assert_called_once()


# Tests for view_urls


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.load_urls")
async def test_view_urls_with_urls(mock_load_urls, mock_update, mock_context):
    """Test viewing URLs when URLs exist."""
    mock_load_urls.return_value = [
        {"url": "https://example.com", "name": "Example"},
        {"url": "https://test.com"},
    ]

    await view_urls(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    call_text = mock_update.message.reply_text.call_args[0][0]
    assert "Example" in call_text
    assert "https://example.com" in call_text


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.load_urls")
async def test_view_urls_empty(mock_load_urls, mock_update, mock_context):
    """Test viewing URLs when no URLs exist."""
    mock_load_urls.return_value = []

    await view_urls(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    assert "No URLs" in str(mock_update.message.reply_text.call_args)


# Tests for add_url


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.save_urls")
@patch("handlers.urlwatch_manage.load_urls")
async def test_add_url_success(mock_load_urls, mock_save_urls, mock_update, mock_context):
    """Test successfully adding a URL."""
    mock_load_urls.return_value = []
    mock_save_urls.return_value = True
    mock_context.args = ["https://example.com", "Example", "Site"]

    await add_url(mock_update, mock_context)

    mock_save_urls.assert_called_once()
    saved_urls = mock_save_urls.call_args[0][0]
    assert len(saved_urls) == 1
    assert saved_urls[0]["url"] == "https://example.com"
    assert saved_urls[0]["name"] == "Example Site"


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.load_urls")
async def test_add_url_no_scheme(mock_load_urls, mock_update, mock_context):
    """Test adding URL without scheme."""
    mock_load_urls.return_value = []
    mock_context.args = ["example.com"]

    await add_url(mock_update, mock_context)

    mock_update.message.reply_text.assert_called()
    # URL validation requires http:// or https://


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.load_urls")
async def test_add_url_duplicate(mock_load_urls, mock_update, mock_context):
    """Test adding a duplicate URL."""
    mock_load_urls.return_value = [{"url": "https://example.com"}]
    mock_context.args = ["https://example.com", "Duplicate"]

    await add_url(mock_update, mock_context)

    mock_update.message.reply_text.assert_called()
    assert "already exists" in str(mock_update.message.reply_text.call_args)


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.save_urls")
@patch("handlers.urlwatch_manage.load_urls")
async def test_add_url_save_failure(mock_load_urls, mock_save_urls, mock_update, mock_context):
    """Test handling save failure when adding URL."""
    mock_load_urls.return_value = []
    mock_save_urls.return_value = False
    mock_context.args = ["https://example.com"]

    await add_url(mock_update, mock_context)

    mock_update.message.reply_text.assert_called()
    assert "Failed" in str(mock_update.message.reply_text.call_args)


# Tests for edit_url


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.save_urls")
@patch("handlers.urlwatch_manage.load_urls")
async def test_edit_url_success(mock_load_urls, mock_save_urls, mock_update, mock_context):
    """Test successfully editing a URL."""
    mock_load_urls.return_value = [{"url": "https://old.com", "name": "Old"}]
    mock_save_urls.return_value = True
    mock_context.args = ["1", "https://new.com", "New", "Name"]

    await edit_url(mock_update, mock_context)

    mock_save_urls.assert_called_once()
    saved_urls = mock_save_urls.call_args[0][0]
    assert saved_urls[0]["url"] == "https://new.com"
    assert saved_urls[0]["name"] == "New Name"


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.load_urls")
async def test_edit_url_invalid_index(mock_load_urls, mock_update, mock_context):
    """Test editing with invalid index."""
    mock_load_urls.return_value = [{"url": "https://example.com"}]
    mock_context.args = ["99", "https://new.com"]

    await edit_url(mock_update, mock_context)

    mock_update.message.reply_text.assert_called()
    assert "Invalid index" in str(mock_update.message.reply_text.call_args)


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.load_urls")
async def test_edit_url_no_urls(mock_load_urls, mock_update, mock_context):
    """Test editing when no URLs exist."""
    mock_load_urls.return_value = []
    mock_context.args = ["1", "https://new.com"]

    await edit_url(mock_update, mock_context)

    mock_update.message.reply_text.assert_called()


# Tests for edit_url_filters


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.save_urls")
@patch("handlers.urlwatch_manage.load_urls")
async def test_edit_url_filters_show(mock_load_urls, mock_save_urls, mock_update, mock_context):
    """Test removing filters when only index provided."""
    mock_load_urls.return_value = [{"url": "https://example.com", "filter": ["html2text"]}]
    mock_save_urls.return_value = True
    mock_context.args = ["1"]

    await edit_url_filters(mock_update, mock_context)

    # With only index, filters are removed
    mock_save_urls.assert_called_once()


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.save_urls")
@patch("handlers.urlwatch_manage.load_urls")
async def test_edit_url_filters_set(mock_load_urls, mock_save_urls, mock_update, mock_context):
    """Test setting filters."""
    mock_load_urls.return_value = [{"url": "https://example.com"}]
    mock_save_urls.return_value = True
    mock_context.args = ["1", "html2text"]

    await edit_url_filters(mock_update, mock_context)

    mock_save_urls.assert_called_once()
    saved_urls = mock_save_urls.call_args[0][0]
    assert "filter" in saved_urls[0]
    assert "html2text" in str(saved_urls[0]["filter"])


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.save_urls")
@patch("handlers.urlwatch_manage.load_urls")
async def test_edit_url_filters_clear(mock_load_urls, mock_save_urls, mock_update, mock_context):
    """Test clearing filters with just index."""
    mock_load_urls.return_value = [{"url": "https://example.com", "filter": ["html2text"]}]
    mock_save_urls.return_value = True
    mock_context.args = ["1"]  # Just index removes filters

    await edit_url_filters(mock_update, mock_context)

    mock_save_urls.assert_called_once()
    saved_urls = mock_save_urls.call_args[0][0]
    assert "filter" not in saved_urls[0]


# Tests for edit_url_properties


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.load_urls")
async def test_edit_url_properties_show(mock_load_urls, mock_update, mock_context):
    """Test showing current properties."""
    mock_load_urls.return_value = [{"url": "https://example.com", "timeout": 30}]
    mock_context.args = ["1"]

    await edit_url_properties(mock_update, mock_context)

    mock_update.message.reply_text.assert_called()
    call_text = str(mock_update.message.reply_text.call_args)
    assert "timeout" in call_text


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.save_urls")
@patch("handlers.urlwatch_manage.load_urls")
async def test_edit_url_properties_set(mock_load_urls, mock_save_urls, mock_update, mock_context):
    """Test setting properties."""
    mock_load_urls.return_value = [{"url": "https://example.com"}]
    mock_save_urls.return_value = True
    mock_context.args = ["1", "timeout:30", "user_agent:MyBot"]

    await edit_url_properties(mock_update, mock_context)

    mock_save_urls.assert_called_once()
    saved_urls = mock_save_urls.call_args[0][0]
    assert saved_urls[0]["timeout"] == 30
    assert saved_urls[0]["user_agent"] == "MyBot"


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.save_urls")
@patch("handlers.urlwatch_manage.load_urls")
async def test_edit_url_properties_nested(
    mock_load_urls, mock_save_urls, mock_update, mock_context
):
    """Test setting nested properties."""
    mock_load_urls.return_value = [{"url": "https://example.com"}]
    mock_save_urls.return_value = True
    mock_context.args = ["1", "headers.Accept:text/html"]

    await edit_url_properties(mock_update, mock_context)

    mock_save_urls.assert_called_once()
    saved_urls = mock_save_urls.call_args[0][0]
    assert "headers" in saved_urls[0]
    assert saved_urls[0]["headers"]["Accept"] == "text/html"


# Tests for delete_url


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.update_crontab_indices_after_deletion")
@patch("handlers.urlwatch_manage.save_urls")
@patch("handlers.urlwatch_manage.load_urls")
async def test_delete_url_success(
    mock_load_urls, mock_save_urls, mock_update_cron, mock_update, mock_context
):
    """Test successfully deleting a URL."""
    mock_load_urls.return_value = [{"url": "https://example.com", "name": "Example"}]
    mock_save_urls.return_value = True
    mock_update_cron.return_value = (False, [])
    mock_context.args = ["1"]

    await delete_url(mock_update, mock_context)

    mock_save_urls.assert_called_once()
    saved_urls = mock_save_urls.call_args[0][0]
    assert len(saved_urls) == 0
    mock_update_cron.assert_called_once_with(1)


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.update_crontab_indices_after_deletion")
@patch("handlers.urlwatch_manage.save_urls")
@patch("handlers.urlwatch_manage.load_urls")
async def test_delete_url_with_cron_updates(
    mock_load_urls, mock_save_urls, mock_update_cron, mock_update, mock_context
):
    """Test deleting URL with cron job updates."""
    mock_load_urls.return_value = [
        {"url": "https://site1.com"},
        {"url": "https://site2.com"},
        {"url": "https://site3.com"},
    ]
    mock_save_urls.return_value = True
    mock_update_cron.return_value = (True, [2])  # Job 3 became job 2
    mock_context.args = ["2"]

    await delete_url(mock_update, mock_context)

    mock_save_urls.assert_called_once()
    mock_update.message.reply_text.assert_called()
    call_text = str(mock_update.message.reply_text.call_args)
    assert "crontab" in call_text.lower() or "updated" in call_text.lower()


# Tests for check_url_output


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.asyncio.create_subprocess_exec")
@patch("handlers.urlwatch_manage.load_urls")
async def test_check_url_output_success(mock_load_urls, mock_subprocess, mock_update, mock_context):
    """Test checking URL output successfully."""
    mock_load_urls.return_value = [{"url": "https://example.com", "name": "Example"}]

    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate = AsyncMock(return_value=(b"Output content", b""))
    mock_subprocess.return_value = mock_process

    mock_context.args = ["1"]

    await check_url_output(mock_update, mock_context)

    mock_subprocess.assert_called_once()
    mock_update.message.reply_text.assert_called()
    call_text = str(mock_update.message.reply_text.call_args)
    assert "Output content" in call_text


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.asyncio.create_subprocess_exec")
@patch("handlers.urlwatch_manage.load_urls")
async def test_check_url_output_no_output(
    mock_load_urls, mock_subprocess, mock_update, mock_context
):
    """Test handling when urlwatch returns no output."""
    mock_load_urls.return_value = [{"url": "https://example.com"}]

    mock_process = AsyncMock()
    mock_process.returncode = 1
    mock_process.communicate = AsyncMock(return_value=(b"", b"Error message"))
    mock_subprocess.return_value = mock_process

    mock_context.args = ["1"]

    await check_url_output(mock_update, mock_context)

    mock_update.message.reply_text.assert_called()
    # Message about no output


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.asyncio.create_subprocess_exec")
@patch("handlers.urlwatch_manage.load_urls")
async def test_check_url_output_timeout(mock_load_urls, mock_subprocess, mock_update, mock_context):
    """Test handling timeout."""
    mock_load_urls.return_value = [{"url": "https://example.com"}]
    mock_subprocess.side_effect = Exception("Timeout")
    mock_context.args = ["1"]

    await check_url_output(mock_update, mock_context)

    mock_update.message.reply_text.assert_called()


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.save_urls")
@patch("handlers.urlwatch_manage.load_urls")
async def test_edit_url_properties_invalid_format(
    mock_load_urls, mock_save_urls, mock_update, mock_context
):
    """Test editing properties with invalid format."""
    mock_load_urls.return_value = [{"url": "https://example.com"}]
    mock_save_urls.return_value = True
    mock_context.args = ["1", "invalid_no_colon"]

    await edit_url_properties(mock_update, mock_context)

    # Should handle gracefully
    mock_update.message.reply_text.assert_called()


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.save_urls")
@patch("handlers.urlwatch_manage.load_urls")
async def test_edit_url_save_failure(mock_load_urls, mock_save_urls, mock_update, mock_context):
    """Test handling save failure during edit."""
    mock_load_urls.return_value = [{"url": "https://old.com"}]
    mock_save_urls.return_value = False
    mock_context.args = ["1", "https://new.com"]

    await edit_url(mock_update, mock_context)

    mock_update.message.reply_text.assert_called()


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.save_urls")
@patch("handlers.urlwatch_manage.load_urls")
async def test_delete_url_save_failure(mock_load_urls, mock_save_urls, mock_update, mock_context):
    """Test handling save failure during delete."""
    mock_load_urls.return_value = [{"url": "https://example.com"}]
    mock_save_urls.return_value = False
    mock_context.args = ["1"]

    with patch("handlers.urlwatch_manage.update_crontab_indices_after_deletion") as mock_cron:
        mock_cron.return_value = (False, [])
        await delete_url(mock_update, mock_context)

    mock_update.message.reply_text.assert_called()


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.shutil.which")
@patch("handlers.urlwatch_manage.load_urls")
async def test_check_url_output_urlwatch_not_found(
    mock_load_urls, mock_which, mock_update, mock_context
):
    """Test handling when urlwatch command is not found."""
    mock_load_urls.return_value = [{"url": "https://example.com"}]
    mock_which.return_value = None
    mock_context.args = ["1"]

    await check_url_output(mock_update, mock_context)

    mock_update.message.reply_text.assert_called()
    call_text = str(mock_update.message.reply_text.call_args)
    assert "not found" in call_text.lower()


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.save_urls")
@patch("handlers.urlwatch_manage.load_urls")
async def test_edit_url_preserves_custom_name(
    mock_load_urls, mock_save_urls, mock_update, mock_context
):
    """Test that edit_url preserves custom name when not provided."""
    mock_load_urls.return_value = [{"url": "https://old.com", "name": "My Custom Name"}]
    mock_save_urls.return_value = True
    mock_context.args = ["1", "https://new.com"]

    await edit_url(mock_update, mock_context)

    # Verify the name was preserved
    saved_urls = mock_save_urls.call_args[0][0]
    assert saved_urls[0]["name"] == "My Custom Name"
    assert saved_urls[0]["url"] == "https://new.com"


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.save_urls")
@patch("handlers.urlwatch_manage.load_urls")
async def test_edit_url_uses_url_as_name_when_no_custom_name(
    mock_load_urls, mock_save_urls, mock_update, mock_context
):
    """Test that edit_url uses URL as name when no custom name exists."""
    mock_load_urls.return_value = [{"url": "https://old.com"}]
    mock_save_urls.return_value = True
    mock_context.args = ["1", "https://new.com"]

    await edit_url(mock_update, mock_context)

    # Verify the URL is used as the name
    saved_urls = mock_save_urls.call_args[0][0]
    assert saved_urls[0]["name"] == "https://new.com"


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.save_urls")
@patch("handlers.urlwatch_manage.load_urls")
async def test_edit_url_properties_empty_properties(
    mock_load_urls, mock_save_urls, mock_update, mock_context
):
    """Test editing properties with no valid properties provided."""
    mock_load_urls.return_value = [{"url": "https://example.com"}]
    mock_context.args = ["1", "invalid", "also_invalid"]

    await edit_url_properties(mock_update, mock_context)

    # Should not save when no valid properties
    mock_save_urls.assert_not_called()
    mock_update.message.reply_text.assert_called()
    call_text = str(mock_update.message.reply_text.call_args)
    assert "no valid properties" in call_text.lower()


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.asyncio.create_subprocess_exec")
@patch("handlers.urlwatch_manage.load_urls")
async def test_check_url_output_long_output_truncation(
    mock_load_urls, mock_subprocess, mock_update, mock_context
):
    """Test that long output is truncated."""
    mock_load_urls.return_value = [{"url": "https://example.com"}]

    # Create output longer than 3000 characters
    long_output = "x" * 3500
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate = AsyncMock(return_value=(long_output.encode(), b""))
    mock_subprocess.return_value = mock_process

    mock_context.args = ["1"]

    await check_url_output(mock_update, mock_context)

    call_text = str(mock_update.message.reply_text.call_args)
    assert "truncated" in call_text.lower()


@pytest.mark.asyncio
@patch("handlers.urlwatch_manage.asyncio.wait_for")
@patch("handlers.urlwatch_manage.asyncio.create_subprocess_exec")
@patch("handlers.urlwatch_manage.load_urls")
async def test_check_url_output_actual_timeout(
    mock_load_urls, mock_subprocess, mock_wait_for, mock_update, mock_context
):
    """Test handling actual timeout from asyncio.wait_for."""

    mock_load_urls.return_value = [{"url": "https://example.com"}]

    mock_process = AsyncMock()
    mock_process.kill = Mock()
    mock_process.communicate = AsyncMock()
    mock_subprocess.return_value = mock_process

    # Make wait_for raise TimeoutError
    mock_wait_for.side_effect = TimeoutError()

    mock_context.args = ["1"]

    await check_url_output(mock_update, mock_context)

    # Verify process was killed
    mock_process.kill.assert_called_once()
    mock_update.message.reply_text.assert_called()
    call_text = str(mock_update.message.reply_text.call_args)
    assert "timeout" in call_text.lower()
