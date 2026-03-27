from typing import Any

from crontab import CronTab

from config.logging import logger

# Configuration
CRONWATCH_COMMENT_PREFIX = "cronwatch-bot-"


def get_cron() -> CronTab:
    """Get crontab instance using user mode.

    Uses the crontab command internally for both reading and writing,
    which automatically notifies BusyBox crond to reload. Creates a new
    empty crontab if one doesn't exist.

    Returns:
        CronTab: Crontab instance for the current user.

    Raises:
        IOError: If crontab cannot be accessed (logged and handled).
        OSError: If crontab cannot be created (logged and handled).
    """
    try:
        return CronTab(user=True)
    except OSError as e:
        logger.warning("Crontab doesn't exist, creating: %s", e)
        cron = CronTab(user=True, tab="")
        cron.write()
        return cron


def list_urlwatch_jobs() -> list[Any]:
    """List all urlwatch jobs managed by CronWatchBot.

    Filters cron jobs to only include those with comments starting with
    the CRONWATCH_COMMENT_PREFIX.

    Returns:
        List: List of CronItem objects for urlwatch jobs managed by this bot.
    """
    cron = get_cron()
    return [job for job in cron if job.comment and job.comment.startswith(CRONWATCH_COMMENT_PREFIX)]


def build_urlwatch_command(job_index: int) -> str:
    """Build urlwatch command for specific job index.

    Uses simple command since urlwatch is symlinked to /usr/local/bin
    which is in the default cron PATH.

    Args:
        job_index: 1-based index of the URL entry to monitor.

    Returns:
        str: Command string to execute urlwatch for the specified job.

    Raises:
        ValueError: If job_index is not a positive integer.

    Examples:
        >>> build_urlwatch_command(1)
        'urlwatch 1'
        >>> build_urlwatch_command(5)
        'urlwatch 5'
    """
    if not isinstance(job_index, int) or job_index < 1:
        raise ValueError(f"Invalid job_index: must be a positive integer, got {job_index}")
    return f"urlwatch {job_index}"


def get_job_index_from_comment(comment: str) -> int:
    """Extract job index from crontab comment.

    Parses the comment string to extract the numeric job index that follows
    the CRONWATCH_COMMENT_PREFIX.

    Args:
        comment: Comment string from a cron job.

    Returns:
        int: Job index if valid comment, -1 otherwise.

    Examples:
        >>> get_job_index_from_comment("cronwatch-bot-1")
        1
        >>> get_job_index_from_comment("cronwatch-bot-42")
        42
        >>> get_job_index_from_comment("other-comment")
        -1
    """
    if comment and comment.startswith(CRONWATCH_COMMENT_PREFIX):
        try:
            return int(comment[len(CRONWATCH_COMMENT_PREFIX) :])
        except ValueError:
            return -1
    return -1


def update_crontab_indices_after_deletion(deleted_index: int) -> tuple[bool, list[int]]:
    """Update crontab job indices after a URL entry is deleted.

    When a URL entry is deleted, this function:
    1. Removes the cron job associated with the deleted entry
    2. Decrements indices for all jobs pointing to entries after the deleted one
    3. Updates both the command and comment for affected jobs

    Args:
        deleted_index: 1-based index of the deleted URL entry.

    Returns:
        Tuple[bool, List[int]]: (job_removed, updated_indices)
        - job_removed: True if a job for the deleted entry was found and removed
        - updated_indices: List of updated job indices (1-based). Empty list on error.

    Examples:
        If URL #2 is deleted and jobs exist for URLs #1, #2, #3:
        - Job for URL #2 is removed
        - Job for URL #3 is updated to point to URL #2
        - Returns (True, [2])
    """
    cron = get_cron()
    jobs = [job for job in cron if job.comment and job.comment.startswith(CRONWATCH_COMMENT_PREFIX)]
    updated_indices = []
    job_removed = False

    for job in jobs:
        job_index = get_job_index_from_comment(job.comment)
        if job_index == -1:
            continue

        # If job points to deleted entry, remove it
        if job_index == deleted_index:
            cron.remove(job)
            job_removed = True
            continue

        # If job points to entry after deleted one, decrement index
        if job_index > deleted_index:
            new_index = job_index - 1
            # Validate new_index for crontab safety (defense in depth)
            if not isinstance(new_index, int) or new_index < 1:
                logger.error("Invalid new_index for crontab: %s", new_index)
                continue
            job.set_command(build_urlwatch_command(new_index))
            job.set_comment(f"{CRONWATCH_COMMENT_PREFIX}{new_index}")
            updated_indices.append(new_index)

    try:
        cron.write()
    except Exception as e:
        logger.error("Failed to write crontab during index update: %s", e)
        return False, []

    return job_removed, updated_indices
