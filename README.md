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
- conda (optional, for environment management)

### Python
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

#### Urlwatch Commands
```
/view
```
Shows all urlwatch jobs and their indices.

```
/add https://example.com My Example Job
```
Adds a new job for https://example.com with the name "My Example Job".

```
/edit 2 https://another.com Another Name
```
Edits job 2 to use a new URL and name.

```
/editfilter 1 html2text strip
```
Sets filters for job 1 to "html2text" and "strip".

#### Crontab Commands
```
/crontab_add 0 * * * * 2
```
Adds a job to run urlwatch job 2 every hour.

```
/crontab_view
```
Lists all urlwatch jobs currently scheduled in crontab.

```
/crontab_edit 1 30 6 * * * 3
```
Edits the first crontab job to run job 3 every day at 6:30am.

```
/crontab_delete 1
```
Deletes the first crontab job.

## Security
- Only user IDs listed in `ALLOWED_USER_IDS` can use the bot.
- Never commit your `config.py` to version control.
