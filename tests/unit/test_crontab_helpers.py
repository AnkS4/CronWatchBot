"""Tests for crontab helper functions."""

from unittest.mock import Mock, patch

import pytest

from helpers.crontab_helpers import (
    CRONWATCH_COMMENT_PREFIX,
    build_urlwatch_command,
    get_cron,
    get_job_index_from_comment,
    list_urlwatch_jobs,
    update_crontab_indices_after_deletion,
)


@patch("helpers.crontab_helpers.CronTab")
def test_get_cron_success(mock_crontab):
    """Test successful crontab retrieval."""
    mock_instance = Mock()
    mock_crontab.return_value = mock_instance

    result = get_cron()

    assert result == mock_instance
    mock_crontab.assert_called_once_with(user=True)


@patch("helpers.crontab_helpers.CronTab")
@patch("helpers.crontab_helpers.logger")
def test_get_cron_creates_if_not_exists(mock_logger, mock_crontab):
    """Test crontab creation when it doesn't exist."""
    mock_crontab.side_effect = [OSError("No crontab"), Mock()]

    get_cron()

    assert mock_crontab.call_count == 2
    mock_crontab.assert_any_call(user=True)
    mock_crontab.assert_any_call(user=True, tab="")
    mock_logger.warning.assert_called_once()


@patch("helpers.crontab_helpers.get_cron")
def test_list_urlwatch_jobs_empty(mock_get_cron):
    """Test listing jobs when crontab is empty."""
    mock_cron = Mock()
    mock_cron.__iter__ = Mock(return_value=iter([]))
    mock_get_cron.return_value = mock_cron

    result = list_urlwatch_jobs()

    assert result == []


@patch("helpers.crontab_helpers.get_cron")
def test_list_urlwatch_jobs_filters_correctly(mock_get_cron):
    """Test that only cronwatch-bot jobs are returned."""
    job1 = Mock(comment=f"{CRONWATCH_COMMENT_PREFIX}1")
    job2 = Mock(comment="other-job")
    job3 = Mock(comment=f"{CRONWATCH_COMMENT_PREFIX}2")
    job4 = Mock(comment=None)

    mock_cron = Mock()
    mock_cron.__iter__ = Mock(return_value=iter([job1, job2, job3, job4]))
    mock_get_cron.return_value = mock_cron

    result = list_urlwatch_jobs()

    assert len(result) == 2
    assert job1 in result
    assert job3 in result
    assert job2 not in result
    assert job4 not in result


def test_build_urlwatch_command_valid():
    """Test building valid urlwatch commands."""
    assert build_urlwatch_command(1) == "urlwatch 1"
    assert build_urlwatch_command(5) == "urlwatch 5"
    assert build_urlwatch_command(100) == "urlwatch 100"


@pytest.mark.parametrize(
    "invalid_input",
    ["1", 0, -1],
    ids=["string", "zero", "negative"],
)
def test_build_urlwatch_command_invalid(invalid_input):
    """Test that invalid inputs raise ValueError."""
    with pytest.raises(ValueError, match="Invalid job_index"):
        build_urlwatch_command(invalid_input)


@pytest.mark.parametrize(
    ("comment", "expected"),
    [
        (f"{CRONWATCH_COMMENT_PREFIX}1", 1),
        (f"{CRONWATCH_COMMENT_PREFIX}42", 42),
        (f"{CRONWATCH_COMMENT_PREFIX}999", 999),
    ],
)
def test_get_job_index_from_comment_valid(comment, expected):
    """Test extracting valid job indices from comments."""
    assert get_job_index_from_comment(comment) == expected


@pytest.mark.parametrize(
    "invalid_comment",
    [
        "other-prefix-1",
        "random-comment",
        f"{CRONWATCH_COMMENT_PREFIX}abc",
        CRONWATCH_COMMENT_PREFIX,
        None,
        "",
    ],
    ids=["wrong_prefix", "random", "non_numeric", "no_number", "none", "empty"],
)
def test_get_job_index_from_comment_invalid(invalid_comment):
    """Test that invalid comments return -1."""
    assert get_job_index_from_comment(invalid_comment) == -1


@patch("helpers.crontab_helpers.list_urlwatch_jobs")
@patch("helpers.crontab_helpers.get_cron")
def test_update_crontab_indices_removes_deleted_job(mock_get_cron, mock_list_jobs):
    """Test that deleted job is removed and subsequent jobs are renumbered."""
    mock_cron = Mock()
    mock_get_cron.return_value = mock_cron

    job1 = Mock(comment=f"{CRONWATCH_COMMENT_PREFIX}1")
    job2 = Mock(comment=f"{CRONWATCH_COMMENT_PREFIX}2")
    job3 = Mock(comment=f"{CRONWATCH_COMMENT_PREFIX}3")

    mock_list_jobs.return_value = [job1, job2, job3]

    job_removed, updated_indices = update_crontab_indices_after_deletion(2)

    mock_cron.remove.assert_called_once_with(job2)
    assert job_removed is True
    assert 2 in updated_indices
    job3.set_command.assert_called_once_with("urlwatch 2")
    job3.set_comment.assert_called_once_with(f"{CRONWATCH_COMMENT_PREFIX}2")
    mock_cron.write.assert_called_once()


@patch("helpers.crontab_helpers.list_urlwatch_jobs")
@patch("helpers.crontab_helpers.get_cron")
def test_update_crontab_indices_updates_higher_indices(mock_get_cron, mock_list_jobs):
    """Test that only jobs with higher indices are updated."""
    mock_cron = Mock()
    mock_get_cron.return_value = mock_cron

    job1 = Mock(comment=f"{CRONWATCH_COMMENT_PREFIX}1")
    job3 = Mock(comment=f"{CRONWATCH_COMMENT_PREFIX}3")
    job5 = Mock(comment=f"{CRONWATCH_COMMENT_PREFIX}5")

    mock_list_jobs.return_value = [job1, job3, job5]

    job_removed, updated_indices = update_crontab_indices_after_deletion(2)

    job1.set_command.assert_not_called()
    job3.set_command.assert_called_once_with("urlwatch 2")
    job5.set_command.assert_called_once_with("urlwatch 4")
    mock_cron.write.assert_called_once()
    assert job_removed is False  # No job with index 2 exists to remove
    assert updated_indices == [2, 4]


@patch("helpers.crontab_helpers.list_urlwatch_jobs")
@patch("helpers.crontab_helpers.get_cron")
def test_update_crontab_indices_ignores_invalid_comments(mock_get_cron, mock_list_jobs):
    """Test that jobs with invalid comments are ignored."""
    mock_cron = Mock()
    mock_get_cron.return_value = mock_cron

    job_invalid = Mock(comment="invalid-comment")
    mock_list_jobs.return_value = [job_invalid]

    job_removed, updated_indices = update_crontab_indices_after_deletion(1)

    assert job_removed is False
    assert updated_indices == []
    mock_cron.remove.assert_not_called()
    mock_cron.write.assert_called_once()


@patch("helpers.crontab_helpers.list_urlwatch_jobs")
@patch("helpers.crontab_helpers.get_cron")
@patch("helpers.crontab_helpers.logger")
def test_update_crontab_indices_handles_write_error(mock_logger, mock_get_cron, mock_list_jobs):
    """Test error handling when crontab write fails."""
    mock_cron = Mock()
    mock_cron.write.side_effect = Exception("Write failed")
    mock_get_cron.return_value = mock_cron

    job1 = Mock(comment=f"{CRONWATCH_COMMENT_PREFIX}2")
    mock_list_jobs.return_value = [job1]

    job_removed, updated_indices = update_crontab_indices_after_deletion(1)

    assert job_removed is False
    assert updated_indices == []
    mock_logger.error.assert_called_once()
