"""Tests for Telegram bot handlers."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from telegram import Update, User
from telegram.ext import ContextTypes

from handlers.basic import help_command, start, unknown
from handlers.crontab_manage import (
    create_schedule_from_minutes,
    crontab_add,
    crontab_delete,
    crontab_view,
    validate_job_index_and_minutes,
)
from handlers.shared import ERROR_MESSAGES, auth_and_error_handler, send_error, validate_args


@pytest.fixture
def mock_update():
    """Create a mock Telegram Update object."""
    update = Mock(spec=Update)
    update.effective_user = Mock(spec=User)
    update.effective_user.id = 123456789  # Matches ALLOWED_USER_IDS from conftest
    update.message = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Create a mock Telegram Context object."""
    context = Mock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []
    return context


# Tests for shared.py


@pytest.mark.asyncio
async def test_send_error(mock_update):
    """Test sending error messages."""
    await send_error(mock_update, "unauthorized")
    mock_update.message.reply_text.assert_called_once_with(ERROR_MESSAGES["unauthorized"])


@pytest.mark.asyncio
async def test_send_error_with_format_args(mock_update):
    """Test sending error messages with format arguments."""
    await send_error(mock_update, "invalid_index", 5)
    mock_update.message.reply_text.assert_called_once_with("❌ Invalid index. Use 1-5.")


@pytest.mark.asyncio
async def test_send_error_no_message():
    """Test send_error when update has no message."""
    update = Mock(spec=Update)
    update.message = None
    await send_error(update, "unauthorized")


@pytest.mark.asyncio
async def test_auth_and_error_handler_authorized(mock_update, mock_context):
    """Test auth decorator allows authorized users."""

    @auth_and_error_handler
    async def test_handler(update, context):
        return "success"

    result = await test_handler(mock_update, mock_context)
    assert result == "success"


@pytest.mark.asyncio
async def test_auth_and_error_handler_unauthorized(mock_update, mock_context):
    """Test auth decorator blocks unauthorized users."""
    mock_update.effective_user.id = 999999  # Not in ALLOWED_USER_IDS

    @auth_and_error_handler
    async def test_handler(update, context):
        return "success"

    await test_handler(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once_with(ERROR_MESSAGES["unauthorized"])


@pytest.mark.asyncio
async def test_auth_and_error_handler_exception(mock_update, mock_context):
    """Test auth decorator handles exceptions."""

    @auth_and_error_handler
    async def test_handler(update, context):
        raise ValueError("Test error")

    await test_handler(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once_with(ERROR_MESSAGES["generic_error"])


@pytest.mark.asyncio
async def test_validate_args_sufficient(mock_update, mock_context):
    """Test validate_args decorator with sufficient arguments."""
    mock_context.args = ["arg1", "arg2"]

    @validate_args(2, "Usage message")
    async def test_handler(update, context):
        return "success"

    result = await test_handler(mock_update, mock_context)
    assert result == "success"


@pytest.mark.asyncio
async def test_validate_args_insufficient(mock_update, mock_context):
    """Test validate_args decorator with insufficient arguments."""
    mock_context.args = ["arg1"]

    @validate_args(2, "Usage message")
    async def test_handler(update, context):
        return "success"

    await test_handler(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once_with("Usage message", parse_mode="Markdown")


# Tests for basic.py


@pytest.mark.asyncio
async def test_help_command(mock_update, mock_context):
    """Test help command sends help message."""
    await help_command(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert "CronWatchBot" in call_args[0][0]
    assert call_args[1]["parse_mode"] == "Markdown"


@pytest.mark.asyncio
async def test_start_command(mock_update, mock_context):
    """Test start command sends welcome message."""
    await start(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert "Welcome to CronWatchBot" in call_args[0][0]
    assert call_args[1]["parse_mode"] == "Markdown"


@pytest.mark.asyncio
async def test_unknown_command(mock_update, mock_context):
    """Test unknown command handler for commands."""
    mock_update.message.text = "/unknowncommand"
    await unknown(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    assert "Unknown command" in mock_update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_unknown_non_command(mock_update, mock_context):
    """Test unknown handler for non-command messages."""
    mock_update.message.text = "Hello bot"
    await unknown(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    assert "only respond to commands" in mock_update.message.reply_text.call_args[0][0]


# Tests for crontab_manage.py


@pytest.mark.parametrize(
    ("minutes", "expected_schedule", "expected_human"),
    [
        (15, "*/15 * * * *", "every 15 minutes"),
        (30, "*/30 * * * *", "every 30 minutes"),
        (60, "0 */1 * * *", "every 1 hour(s)"),
        (120, "0 */2 * * *", "every 2 hour(s)"),
        (1440, "0 0 */1 * *", "every 1 day(s)"),
    ],
)
def test_create_schedule_from_minutes_valid(minutes, expected_schedule, expected_human):
    """Test creating valid cron schedules from minutes."""
    schedule, human = create_schedule_from_minutes(minutes)
    assert schedule == expected_schedule
    assert human == expected_human


@pytest.mark.parametrize(
    "invalid_minutes",
    [75, 90, 1500],
    ids=["not_divisible", "not_hour_multiple", "not_day_multiple"],
)
def test_create_schedule_from_minutes_invalid(invalid_minutes):
    """Test that invalid minute intervals return None."""
    schedule, human = create_schedule_from_minutes(invalid_minutes)
    assert schedule is None
    assert human is None


@pytest.mark.asyncio
async def test_validate_job_index_and_minutes_valid(mock_update):
    """Test validating valid job index and minutes."""
    args = ["1", "30"]
    job_index, minutes = await validate_job_index_and_minutes(mock_update, args)
    assert job_index == 1
    assert minutes == 30


@pytest.mark.asyncio
async def test_validate_job_index_and_minutes_invalid(mock_update):
    """Test validating invalid arguments."""
    args = ["abc", "30"]
    job_index, minutes = await validate_job_index_and_minutes(mock_update, args)
    assert job_index is None
    assert minutes is None
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_validate_job_index_and_minutes_negative(mock_update):
    """Test validating negative minutes."""
    args = ["1", "-30"]
    job_index, minutes = await validate_job_index_and_minutes(mock_update, args)
    assert job_index is None
    assert minutes is None


@pytest.mark.asyncio
@patch("handlers.crontab_manage.list_urlwatch_jobs")
async def test_crontab_view_empty(mock_list_jobs, mock_update, mock_context):
    """Test viewing crontab when no jobs exist."""
    mock_list_jobs.return_value = []
    await crontab_view(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    assert "No scheduled jobs" in mock_update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
@patch("handlers.crontab_manage.list_urlwatch_jobs")
async def test_crontab_view_with_jobs(mock_list_jobs, mock_update, mock_context):
    """Test viewing crontab with existing jobs."""
    mock_job = Mock()
    mock_job.slices = "*/15 * * * *"
    mock_job.command = "urlwatch 1"
    mock_list_jobs.return_value = [mock_job]

    await crontab_view(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    call_text = mock_update.message.reply_text.call_args[0][0]
    assert "Scheduled Jobs" in call_text
    assert "urlwatch 1" in call_text


@pytest.mark.asyncio
@patch("handlers.crontab_manage.load_urls")
@patch("handlers.crontab_manage.get_cron")
@patch("handlers.crontab_manage.list_urlwatch_jobs")
async def test_crontab_add_success(
    mock_list_jobs, mock_get_cron, mock_load_urls, mock_update, mock_context
):
    """Test successfully adding a cron job."""
    mock_context.args = ["1", "30"]
    mock_load_urls.return_value = [{"url": "https://example.com", "name": "Example"}]
    mock_cron = Mock()
    mock_job = Mock()
    mock_cron.new.return_value = mock_job
    mock_get_cron.return_value = mock_cron
    mock_cron.__iter__ = Mock(return_value=iter([]))
    mock_list_jobs.return_value = [mock_job]

    await crontab_add(mock_update, mock_context)

    mock_cron.new.assert_called_once()
    mock_job.setall.assert_called_once_with("*/30 * * * *")
    mock_cron.write.assert_called_once()
    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
@patch("handlers.crontab_manage.load_urls")
async def test_crontab_add_invalid_index(mock_load_urls, mock_update, mock_context):
    """Test adding cron job with invalid URL index."""
    mock_context.args = ["99", "30"]
    mock_load_urls.return_value = [{"url": "https://example.com"}]

    await crontab_add(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    assert "Invalid index" in mock_update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
@patch("handlers.crontab_manage.list_urlwatch_jobs")
@patch("handlers.crontab_manage.get_cron")
async def test_crontab_delete_success(mock_get_cron, mock_list_jobs, mock_update, mock_context):
    """Test successfully deleting a cron job."""
    mock_context.args = ["1"]
    mock_job = Mock()
    mock_job.comment = "cronwatch-bot-1"
    mock_list_jobs.return_value = [mock_job]
    mock_cron = Mock()
    mock_get_cron.return_value = mock_cron

    with patch("handlers.crontab_manage.load_urls") as mock_load_urls:
        mock_load_urls.return_value = [{"url": "https://example.com", "name": "Example"}]
        await crontab_delete(mock_update, mock_context)

    mock_cron.remove.assert_called_once_with(mock_job)
    mock_cron.write.assert_called_once()
    mock_update.message.reply_text.assert_called_once()
