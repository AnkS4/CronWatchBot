from crontab import CronTab
from typing import List

CRONWATCH_COMMENT_PREFIX = 'cronwatch-bot-'

def get_cron() -> CronTab:
    """Get user's crontab instance. Creates crontab if it doesn't exist."""
    try:
        return CronTab(user=True)
    except (IOError, OSError):
        # Crontab doesn't exist yet, create it
        cron = CronTab(user=True, tab='')
        cron.write()
        return cron

def list_urlwatch_jobs() -> List:
    """List all urlwatch jobs managed by CronWatchBot."""
    cron = get_cron()
    return [job for job in cron if job.comment and job.comment.startswith(CRONWATCH_COMMENT_PREFIX)]

def build_urlwatch_command(job_index: int) -> str:
    """Build urlwatch command for specific job index."""
    if not isinstance(job_index, int) or job_index < 1:
        raise ValueError(f"Invalid job_index: must be a positive integer, got {job_index}")
    return f"urlwatch {job_index}"

def get_job_index_from_comment(comment: str) -> int:
    """Extract job index from crontab comment."""
    if comment and comment.startswith(CRONWATCH_COMMENT_PREFIX):
        try:
            return int(comment[len(CRONWATCH_COMMENT_PREFIX):])
        except ValueError:
            return -1
    return -1

def update_crontab_indices_after_deletion(deleted_index: int) -> List[int]:
    """
    Update crontab job indices after a URL entry is deleted.
    Returns list of updated job indices (1-based).
    """
    cron = get_cron()
    jobs = list_urlwatch_jobs()
    updated_indices = []
    
    for job in jobs:
        job_index = get_job_index_from_comment(job.comment)
        if job_index == -1:
            continue
            
        # If job points to deleted entry, remove it
        if job_index == deleted_index:
            cron.remove(job)
            continue
        
        # If job points to entry after deleted one, decrement index
        if job_index > deleted_index:
            new_index = job_index - 1
            job.set_command(build_urlwatch_command(new_index))
            job.set_comment(f"{CRONWATCH_COMMENT_PREFIX}{new_index}")
            updated_indices.append(new_index)
    
    try:
        cron.write()
    except Exception:
        return []
    
    return updated_indices
