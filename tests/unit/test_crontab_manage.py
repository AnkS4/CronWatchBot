"""Tests for crontab management handlers."""

from unittest.mock import Mock, patch

import pytest

from handlers.crontab_manage import (
    create_schedule_from_minutes,
    crontab_add,
    crontab_delete,
    crontab_edit,
    crontab_view,
    validate_job_index_and_minutes,
)
from helpers.crontab_helpers import CRONWATCH_COMMENT_PREFIX

# Comprehensive tests for create_schedule_from_minutes


@pytest.mark.parametrize(
    ("minutes", "expected_schedule", "expected_human"),
    [
        (1, "*/1 * * * *", "every 1 minute"),
        (5, "*/5 * * * *", "every 5 minutes"),
        (10, "*/10 * * * *", "every 10 minutes"),
        (15, "*/15 * * * *", "every 15 minutes"),
        (30, "*/30 * * * *", "every 30 minutes"),
        (45, "*/45 * * * *", "every 45 minutes"),
        (60, "0 */1 * * *", "every 1 hour"),
        (120, "0 */2 * * *", "every 2 hours"),
        (180, "0 */3 * * *", "every 3 hours"),
        (360, "0 */6 * * *", "every 6 hours"),
        (720, "0 */12 * * *", "every 12 hours"),
        (1440, "0 0 */1 * *", "every 1 day"),
        (2880, "0 0 */2 * *", "every 2 days"),
    ],
)
def test_create_schedule_from_minutes_all_valid(minutes, expected_schedule, expected_human):
    """Test all valid minute intervals."""
    schedule, human = create_schedule_from_minutes(minutes)
    assert schedule == expected_schedule
    assert human == expected_human


@pytest.mark.parametrize(
    "invalid_minutes",
    [61, 75, 90, 100, 125, 1500, 2000],
)
def test_create_schedule_from_minutes_all_invalid(invalid_minutes):
    """Test invalid minute intervals."""
    schedule, human = create_schedule_from_minutes(invalid_minutes)
    assert schedule is None
    assert human is None


# Comprehensive tests for validate_job_index_and_minutes


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("args", "expected_index", "expected_minutes"),
    [
        (["1", "30"], 1, 30),
        (["5", "60"], 5, 60),
        (["10", "1440"], 10, 1440),
    ],
)
async def test_validate_job_index_and_minutes_all_valid(
    mock_update, args, expected_index, expected_minutes
):
    """Test all valid job index and minutes combinations."""
    job_index, minutes = await validate_job_index_and_minutes(mock_update, args)
    assert job_index == expected_index
    assert minutes == expected_minutes


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_args",
    [
        ["abc", "30"],
        ["1", "abc"],
        ["1", "-30"],
        ["1", "0"],
        [],
        ["1"],
    ],
    ids=[
        "non_int_index",
        "non_int_minutes",
        "negative_minutes",
        "zero_minutes",
        "no_args",
        "missing_minutes",
    ],
)
async def test_validate_job_index_and_minutes_all_invalid(mock_update, invalid_args):
    """Test all invalid argument combinations."""
    job_index, minutes = await validate_job_index_and_minutes(mock_update, invalid_args)
    assert job_index is None
    assert minutes is None
    mock_update.message.reply_text.assert_called_once()


# Comprehensive tests for crontab_view


@pytest.mark.asyncio
@patch("handlers.crontab_manage.list_urlwatch_jobs")
async def test_crontab_view_no_jobs(mock_list_jobs, mock_update, mock_context):
    """Test viewing when no jobs exist."""
    mock_list_jobs.return_value = []

    await crontab_view(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    call_text = mock_update.message.reply_text.call_args[0][0]
    assert "No scheduled jobs" in call_text


@pytest.mark.asyncio
@patch("handlers.crontab_manage.list_urlwatch_jobs")
async def test_crontab_view_single_job(mock_list_jobs, mock_update, mock_context):
    """Test viewing with a single job."""
    mock_job = Mock()
    mock_job.slices = "*/30 * * * *"
    mock_job.command = "urlwatch 1"
    mock_list_jobs.return_value = [mock_job]

    await crontab_view(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    call_text = mock_update.message.reply_text.call_args[0][0]
    assert "Scheduled Jobs" in call_text
    assert "*/30 * * * *" in call_text
    assert "urlwatch 1" in call_text


@pytest.mark.asyncio
@patch("handlers.crontab_manage.list_urlwatch_jobs")
async def test_crontab_view_multiple_jobs(mock_list_jobs, mock_update, mock_context):
    """Test viewing with multiple jobs."""
    jobs = []
    for i in range(1, 4):
        job = Mock()
        job.slices = f"*/{i * 15} * * * *"
        job.command = f"urlwatch {i}"
        jobs.append(job)

    mock_list_jobs.return_value = jobs

    await crontab_view(mock_update, mock_context)

    call_text = mock_update.message.reply_text.call_args[0][0]
    assert "1." in call_text
    assert "2." in call_text
    assert "3." in call_text


# Comprehensive tests for crontab_add


@pytest.mark.asyncio
@patch("handlers.crontab_manage.load_urls")
@patch("handlers.crontab_manage.get_cron")
@patch("handlers.crontab_manage.list_urlwatch_jobs")
async def test_crontab_add_valid_job(
    mock_list_jobs, mock_get_cron, mock_load_urls, mock_update, mock_context
):
    """Test adding a valid cron job."""
    mock_load_urls.return_value = [{"url": "https://example.com", "name": "Example"}]
    mock_cron = Mock()
    mock_job = Mock()
    mock_cron.new.return_value = mock_job
    mock_get_cron.return_value = mock_cron
    mock_cron.__iter__ = Mock(return_value=iter([]))
    mock_list_jobs.return_value = [mock_job]
    mock_context.args = ["1", "30"]

    await crontab_add(mock_update, mock_context)

    mock_cron.new.assert_called_once()
    mock_job.setall.assert_called_once_with("*/30 * * * *")
    mock_cron.write.assert_called_once()


@pytest.mark.asyncio
@patch("handlers.crontab_manage.load_urls")
async def test_crontab_add_invalid_url_index(mock_load_urls, mock_update, mock_context):
    """Test adding job with invalid URL index."""
    mock_load_urls.return_value = [{"url": "https://example.com"}]
    mock_context.args = ["99", "30"]

    await crontab_add(mock_update, mock_context)

    mock_update.message.reply_text.assert_called()
    assert "Invalid index" in str(mock_update.message.reply_text.call_args)


@pytest.mark.asyncio
@patch("handlers.crontab_manage.load_urls")
async def test_crontab_add_no_urls(mock_load_urls, mock_update, mock_context):
    """Test adding job when no URLs exist."""
    mock_load_urls.return_value = []
    mock_context.args = ["1", "30"]

    await crontab_add(mock_update, mock_context)

    mock_update.message.reply_text.assert_called()


@pytest.mark.asyncio
@patch("handlers.crontab_manage.load_urls")
@patch("handlers.crontab_manage.get_cron")
async def test_crontab_add_duplicate_job(mock_get_cron, mock_load_urls, mock_update, mock_context):
    """Test adding duplicate job for same URL."""
    mock_load_urls.return_value = [{"url": "https://example.com"}]
    mock_cron = Mock()
    existing_job = Mock()
    existing_job.comment = f"{CRONWATCH_COMMENT_PREFIX}1"
    mock_cron.__iter__ = Mock(return_value=iter([existing_job]))
    mock_get_cron.return_value = mock_cron
    mock_context.args = ["1", "30"]

    await crontab_add(mock_update, mock_context)

    mock_update.message.reply_text.assert_called()
    assert "already exists" in str(mock_update.message.reply_text.call_args)


@pytest.mark.asyncio
@patch("handlers.crontab_manage.load_urls")
@patch("handlers.crontab_manage.get_cron")
@patch("handlers.crontab_manage.list_urlwatch_jobs")
async def test_crontab_add_invalid_schedule(
    mock_list_jobs, mock_get_cron, mock_load_urls, mock_update, mock_context
):
    """Test adding job with invalid schedule."""
    mock_load_urls.return_value = [{"url": "https://example.com"}]
    mock_cron = Mock()
    mock_get_cron.return_value = mock_cron
    mock_cron.__iter__ = Mock(return_value=iter([]))
    mock_context.args = ["1", "75"]  # Invalid interval

    await crontab_add(mock_update, mock_context)

    mock_update.message.reply_text.assert_called()
    assert "Invalid interval" in str(mock_update.message.reply_text.call_args)


@pytest.mark.asyncio
@patch("handlers.crontab_manage.load_urls")
@patch("handlers.crontab_manage.get_cron")
@patch("handlers.crontab_manage.list_urlwatch_jobs")
async def test_crontab_add_write_failure(
    mock_list_jobs, mock_get_cron, mock_load_urls, mock_update, mock_context
):
    """Test handling write failure."""
    mock_load_urls.return_value = [{"url": "https://example.com"}]
    mock_cron = Mock()
    mock_job = Mock()
    mock_cron.new.return_value = mock_job
    mock_cron.write.side_effect = Exception("Write failed")
    mock_get_cron.return_value = mock_cron
    mock_cron.__iter__ = Mock(return_value=iter([]))
    mock_context.args = ["1", "30"]

    await crontab_add(mock_update, mock_context)

    mock_update.message.reply_text.assert_called()
    assert "Failed" in str(mock_update.message.reply_text.call_args)


# Comprehensive tests for crontab_edit


@pytest.mark.asyncio
@patch("handlers.crontab_manage.load_urls")
@patch("handlers.crontab_manage.get_cron")
@patch("handlers.crontab_manage.list_urlwatch_jobs")
async def test_crontab_edit_success(
    mock_list_jobs, mock_get_cron, mock_load_urls, mock_update, mock_context
):
    """Test successfully editing a cron job."""
    mock_load_urls.return_value = [{"url": "https://example.com", "name": "Example"}]
    mock_cron = Mock()
    mock_job = Mock()
    mock_job.comment = f"{CRONWATCH_COMMENT_PREFIX}1"
    mock_get_cron.return_value = mock_cron
    mock_cron.__iter__ = Mock(return_value=iter([mock_job]))
    mock_list_jobs.return_value = [mock_job]
    mock_context.args = ["1", "15"]

    await crontab_edit(mock_update, mock_context)

    mock_job.setall.assert_called_once_with("*/15 * * * *")
    mock_cron.write.assert_called_once()


@pytest.mark.asyncio
@patch("handlers.crontab_manage.get_cron")
@patch("handlers.crontab_manage.list_urlwatch_jobs")
async def test_crontab_edit_invalid_index(mock_list_jobs, mock_get_cron, mock_update, mock_context):
    """Test editing with invalid job index."""
    mock_cron = Mock()
    mock_get_cron.return_value = mock_cron
    mock_list_jobs.return_value = []
    mock_context.args = ["99", "30"]

    await crontab_edit(mock_update, mock_context)

    mock_update.message.reply_text.assert_called()
    # Error comes from send_error helper


@pytest.mark.asyncio
@patch("handlers.crontab_manage.get_cron")
@patch("handlers.crontab_manage.list_urlwatch_jobs")
async def test_crontab_edit_invalid_schedule(
    mock_list_jobs, mock_get_cron, mock_update, mock_context
):
    """Test editing with invalid schedule."""
    mock_cron = Mock()
    mock_job = Mock()
    mock_get_cron.return_value = mock_cron
    mock_list_jobs.return_value = [mock_job]
    mock_context.args = ["1", "75"]  # Invalid

    await crontab_edit(mock_update, mock_context)

    mock_update.message.reply_text.assert_called()
    # Message sent about invalid interval


@pytest.mark.asyncio
@patch("handlers.crontab_manage.load_urls")
@patch("handlers.crontab_manage.get_cron")
@patch("handlers.crontab_manage.list_urlwatch_jobs")
async def test_crontab_edit_write_failure(
    mock_list_jobs, mock_get_cron, mock_load_urls, mock_update, mock_context
):
    """Test handling write failure during edit."""
    mock_load_urls.return_value = [{"url": "https://example.com"}]
    mock_cron = Mock()
    mock_job = Mock()
    mock_job.comment = f"{CRONWATCH_COMMENT_PREFIX}1"
    mock_cron.write.side_effect = Exception("Write failed")
    mock_get_cron.return_value = mock_cron
    mock_list_jobs.return_value = [mock_job]
    mock_context.args = ["1", "30"]

    await crontab_edit(mock_update, mock_context)

    mock_update.message.reply_text.assert_called()
    # Error message sent


# Comprehensive tests for crontab_delete


@pytest.mark.asyncio
@patch("handlers.crontab_manage.load_urls")
@patch("handlers.crontab_manage.list_urlwatch_jobs")
@patch("handlers.crontab_manage.get_cron")
async def test_crontab_delete_success(
    mock_get_cron, mock_list_jobs, mock_load_urls, mock_update, mock_context
):
    """Test successfully deleting a cron job."""
    mock_load_urls.return_value = [{"url": "https://example.com", "name": "Example"}]
    mock_cron = Mock()
    mock_job = Mock()
    mock_job.comment = f"{CRONWATCH_COMMENT_PREFIX}1"
    mock_get_cron.return_value = mock_cron
    mock_list_jobs.return_value = [mock_job]
    mock_context.args = ["1"]

    await crontab_delete(mock_update, mock_context)

    mock_cron.remove.assert_called_once_with(mock_job)
    mock_cron.write.assert_called_once()


@pytest.mark.asyncio
@patch("handlers.crontab_manage.list_urlwatch_jobs")
async def test_crontab_delete_invalid_index(mock_list_jobs, mock_update, mock_context):
    """Test deleting with invalid index."""
    mock_list_jobs.return_value = []
    mock_context.args = ["99"]

    await crontab_delete(mock_update, mock_context)

    mock_update.message.reply_text.assert_called()
    assert "Invalid index" in str(mock_update.message.reply_text.call_args)


@pytest.mark.asyncio
async def test_crontab_delete_invalid_args(mock_update, mock_context):
    """Test deleting with invalid arguments."""
    mock_context.args = ["abc"]

    await crontab_delete(mock_update, mock_context)

    mock_update.message.reply_text.assert_called()


@pytest.mark.asyncio
@patch("handlers.crontab_manage.load_urls")
@patch("handlers.crontab_manage.list_urlwatch_jobs")
@patch("handlers.crontab_manage.get_cron")
async def test_crontab_delete_write_failure(
    mock_get_cron, mock_list_jobs, mock_load_urls, mock_update, mock_context
):
    """Test handling write failure during delete."""
    mock_load_urls.return_value = [{"url": "https://example.com"}]
    mock_cron = Mock()
    mock_job = Mock()
    mock_job.comment = f"{CRONWATCH_COMMENT_PREFIX}1"
    mock_cron.write.side_effect = Exception("Write failed")
    mock_get_cron.return_value = mock_cron
    mock_list_jobs.return_value = [mock_job]
    mock_context.args = ["1"]

    await crontab_delete(mock_update, mock_context)

    mock_update.message.reply_text.assert_called()
    assert "Failed" in str(mock_update.message.reply_text.call_args)
