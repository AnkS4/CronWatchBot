# CronWatchBot

A Telegram bot for managing and monitoring urlwatch jobs, including crontab integration, via chat commands.

## Features
- View, add, edit, and delete urlwatch jobs from Telegram
- Manage filters and properties for each job
- Secure access via allowed user IDs
- Crontab integration: view, add, edit, and delete scheduled urlwatch jobs from Telegram
- Detailed help and usage instructions via `/start`

## Requirements

### System
- urlwatch (installed and configured)
- crontab (cron service enabled)
- conda (recommended, for environment management, `miniforge` works)

### Python (Managed by `conda`)
- Python (3.12 recommended)

### Python Libraries (Managed by `requirements.txt`)
- python-telegram-bot
- python-crontab
- pyyaml

### Other
- Telegram bot token (create via @BotFather and keep it secret)

## Installation
1. **Clone the repository:**
    ```bash
    git clone <repo-url>
    cd CronWatchBot
    ```
2. **Create and activate a conda environment (recommended):**
    ```bash
    conda create -n cronwatchbot python=3.12
    conda activate cronwatchbot
    ```
3. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4. **Configure your bot:**
    - Copy `config.py.example` to `config.py` (or create manually).
    - Add your Telegram bot token and allowed user IDs:
      ```python
      TOKEN = "your-telegram-bot-token"
      ALLOWED_USER_IDS = [123456789, ...]
      ```
    - `config.py` is excluded from git for security.

4. **Ensure urlwatch is set up:**
    - The bot expects your urlwatch jobs file at `~/.config/urlwatch/urls.yaml` by default.

## Usage
- Run the bot:
    ```bash
    python app.py
    ```
- Interact with your bot on Telegram. Use `/start` to see available commands.

### Urlwatch Management Commands
- `/view` — View all urlwatch jobs
- `/add <url> [name]` — Add a new job
- `/edit <index> <url> [name]` — Edit a job's URL and name
- `/editfilter <index> [filters...]` — Edit filters for a job
- `/editprop <index> [props...]` — Edit properties for a job
- `/delete <index>` — Delete a job

### Crontab Management Commands
- `/crontab_view` — View all urlwatch jobs in crontab
- `/crontab_add <min> <hour> <dom> <month> <dow> <job_index>` — Add a scheduled job
- `/crontab_edit <index> <min> <hour> <dom> <month> <dow> <job_index>` — Edit a scheduled job
- `/crontab_delete <index>` — Delete a scheduled job

### Examples

Start the bot and use `/start` to see available commands.

#### Urlwatch Commands

Shows all urlwatch jobs and their indices.

```
/view
```

Add a new job for https://github.com/AnkS4/CronWatchBot with the name "CronWatchBot Repo" to watch this repository.
```
/add https://github.com/AnkS4/CronWatchBot CronWatchBot Repo
```

Edit the job to get the number of stars for this repository.
```
/editfilter 1 xpath://span[@id="repo-stars-counter-star"] html2text strip
```

#### Crontab Commands
Lists all urlwatch jobs currently scheduled in crontab.
```
/crontab_view
```

Add a job to run urlwatch job 2 every 15 minutes.
```
/crontab_add 15 2
```

Delete the first crontab job.
```
/crontab_delete 2
```

## Security
- Only user IDs listed in `ALLOWED_USER_IDS` can use the bot.
- Never commit your `config.py` to version control.
