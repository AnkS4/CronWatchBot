from crontab import CronTab

# === CRONTAB MANAGEMENT HELPERS ===
def get_cron():
    return CronTab(user=True)

def list_urlwatch_jobs():
    cron = get_cron()
    jobs = [job for job in cron if job.comment and job.comment.startswith('cronwatch-bot-')]
    return jobs

def build_urlwatch_command(job_index: int) -> str:
    # Adjust this command to match your urlwatch invocation
    return f"urlwatch --jobs {job_index}"
