"""Integration tests for crontab management workflow."""

from unittest.mock import Mock, patch

import pytest

from handlers.crontab_manage import crontab_add, crontab_delete, crontab_edit, crontab_view
from helpers.crontab_helpers import CRONWATCH_COMMENT_PREFIX


@pytest.mark.asyncio
@patch("handlers.crontab_manage.load_urls")
@patch("handlers.crontab_manage.get_cron")
@patch("handlers.crontab_manage.list_urlwatch_jobs")
async def test_crontab_add_view_delete_workflow(
    mock_list_jobs, mock_get_cron, mock_load_urls, mock_update, mock_context
):
    """Test complete crontab workflow: add -> view -> delete."""
    # Setup
    mock_load_urls.return_value = [{"url": "https://example.com", "name": "Example"}]
    mock_cron = Mock()
    mock_job = Mock()
    mock_job.slices = "*/30 * * * *"
    mock_job.command = "urlwatch 1"
    mock_job.comment = f"{CRONWATCH_COMMENT_PREFIX}1"
    mock_cron.new.return_value = mock_job
    mock_get_cron.return_value = mock_cron
    mock_cron.__iter__ = Mock(return_value=iter([]))

    # Step 1: Add cron job
    mock_context.args = ["1", "30"]
    mock_list_jobs.return_value = []
    await crontab_add(mock_update, mock_context)

    # Verify job was created
    mock_cron.new.assert_called_once()
    mock_job.setall.assert_called_once_with("*/30 * * * *")
    mock_cron.write.assert_called()

    # Step 2: View cron jobs
    mock_list_jobs.return_value = [mock_job]
    await crontab_view(mock_update, mock_context)

    # Verify view shows the job
    view_call = [
        call
        for call in mock_update.message.reply_text.call_args_list
        if "Scheduled Jobs" in str(call)
    ]
    assert len(view_call) > 0

    # Step 3: Delete cron job
    mock_context.args = ["1"]
    await crontab_delete(mock_update, mock_context)

    # Verify job was removed
    mock_cron.remove.assert_called_once_with(mock_job)


@pytest.mark.asyncio
@patch("handlers.crontab_manage.load_urls")
@patch("handlers.crontab_manage.get_cron")
@patch("handlers.crontab_manage.list_urlwatch_jobs")
async def test_crontab_add_edit_workflow(
    mock_list_jobs, mock_get_cron, mock_load_urls, mock_update, mock_context
):
    """Test workflow: add cron job -> edit schedule."""
    # Setup
    mock_load_urls.return_value = [{"url": "https://example.com", "name": "Example"}]
    mock_cron = Mock()
    mock_job = Mock()
    mock_job.slices = "*/30 * * * *"
    mock_job.command = "urlwatch 1"
    mock_job.comment = f"{CRONWATCH_COMMENT_PREFIX}1"
    mock_cron.new.return_value = mock_job
    mock_get_cron.return_value = mock_cron
    mock_cron.__iter__ = Mock(return_value=iter([]))

    # Step 1: Add cron job (every 30 minutes)
    mock_context.args = ["1", "30"]
    mock_list_jobs.return_value = []
    await crontab_add(mock_update, mock_context)

    # Verify job was created with 30 minute schedule
    mock_job.setall.assert_called_with("*/30 * * * *")

    # Step 2: Edit to run every 15 minutes
    mock_context.args = ["1", "15"]
    # For edit, we need to return the job from the cron instance iterator
    mock_cron.__iter__ = Mock(return_value=iter([mock_job]))
    mock_list_jobs.return_value = [mock_job]

    await crontab_edit(mock_update, mock_context)

    # Verify schedule was updated (setall called twice total: once for add, once for edit)
    assert mock_job.setall.call_count == 2
    assert mock_cron.write.call_count >= 2


@pytest.mark.asyncio
@patch("handlers.crontab_manage.load_urls")
@patch("handlers.crontab_manage.get_cron")
@patch("handlers.crontab_manage.list_urlwatch_jobs")
async def test_multiple_cron_jobs_workflow(
    mock_list_jobs, mock_get_cron, mock_load_urls, mock_update, mock_context
):
    """Test workflow with multiple cron jobs."""
    # Setup
    mock_load_urls.return_value = [
        {"url": "https://site1.com", "name": "Site 1"},
        {"url": "https://site2.com", "name": "Site 2"},
        {"url": "https://site3.com", "name": "Site 3"},
    ]
    mock_cron = Mock()
    mock_get_cron.return_value = mock_cron

    jobs = []
    for i in range(1, 4):
        job = Mock()
        job.slices = f"*/{i * 15} * * * *"
        job.command = f"urlwatch {i}"
        job.comment = f"{CRONWATCH_COMMENT_PREFIX}{i}"
        jobs.append(job)

    # Add three cron jobs
    for i, job in enumerate(jobs, 1):
        mock_cron.new.return_value = job
        mock_cron.__iter__ = Mock(return_value=iter(jobs[: i - 1]))
        mock_list_jobs.return_value = jobs[: i - 1]
        mock_context.args = [str(i), str(i * 15)]
        await crontab_add(mock_update, mock_context)

    # Verify all jobs were created
    assert mock_cron.new.call_count == 3

    # View all jobs
    mock_list_jobs.return_value = jobs
    await crontab_view(mock_update, mock_context)

    # Verify view shows all jobs
    last_call = mock_update.message.reply_text.call_args_list[-1]
    assert "Scheduled Jobs" in str(last_call)


@pytest.mark.asyncio
@patch("handlers.crontab_manage.load_urls")
@patch("handlers.crontab_manage.get_cron")
async def test_crontab_empty_state(mock_get_cron, mock_load_urls, mock_update, mock_context):
    """Test viewing crontab when no jobs exist."""
    mock_cron = Mock()
    mock_cron.__iter__ = Mock(return_value=iter([]))
    mock_get_cron.return_value = mock_cron

    with patch("handlers.crontab_manage.list_urlwatch_jobs") as mock_list_jobs:
        mock_list_jobs.return_value = []
        await crontab_view(mock_update, mock_context)

    # Verify empty state message
    mock_update.message.reply_text.assert_called_once()
    assert "No scheduled jobs" in str(mock_update.message.reply_text.call_args)


@pytest.mark.asyncio
@patch("handlers.crontab_manage.load_urls")
@patch("handlers.crontab_manage.get_cron")
@patch("handlers.crontab_manage.list_urlwatch_jobs")
async def test_crontab_duplicate_prevention(
    mock_list_jobs, mock_get_cron, mock_load_urls, mock_update, mock_context
):
    """Test that duplicate cron jobs for same URL are prevented."""
    # Setup
    mock_load_urls.return_value = [{"url": "https://example.com", "name": "Example"}]
    mock_cron = Mock()
    mock_job = Mock()
    mock_job.comment = f"{CRONWATCH_COMMENT_PREFIX}1"
    mock_cron.new.return_value = mock_job
    mock_get_cron.return_value = mock_cron

    # First add succeeds
    mock_cron.__iter__ = Mock(return_value=iter([]))
    mock_list_jobs.return_value = []
    mock_context.args = ["1", "30"]
    await crontab_add(mock_update, mock_context)

    # Second add for same URL should fail
    mock_cron.__iter__ = Mock(return_value=iter([mock_job]))
    mock_context.args = ["1", "15"]
    await crontab_add(mock_update, mock_context)

    # Verify error message about existing job
    calls = [str(call) for call in mock_update.message.reply_text.call_args_list]
    assert any("already exists" in str(call) for call in calls)
