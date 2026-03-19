from crontab import CronTab
from typing import List

CRONWATCH_COMMENT_PREFIX = 'cronwatch-bot-'

def get_cron() -> CronTab:
    """Get user's crontab instance."""
    return CronTab(user=True)

def list_urlwatch_jobs() -> List:
    """List all urlwatch jobs managed by CronWatchBot."""
    cron = get_cron()
    return [job for job in cron if job.comment and job.comment.startswith(CRONWATCH_COMMENT_PREFIX)]

def build_urlwatch_command(job_index: int) -> str:
    """Build urlwatch command for specific job index."""
    if not isinstance(job_index, int) or job_index < 1:
        raise ValueError(f"Invalid job_index: must be a positive integer, got {job_index}")
    return f"urlwatch --jobs {job_index}"
