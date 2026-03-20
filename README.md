# CronWatchBot

A Telegram bot for managing and monitoring urlwatch jobs, including crontab integration, via chat commands.

## Features
- View, add, edit, and delete urlwatch jobs from Telegram
- Manage filters and properties for each job
- Secure access via allowed user IDs
- Crontab integration: view, add, edit, and delete scheduled urlwatch jobs from Telegram
- Detailed help and usage instructions via `/start`

## Project Structure

```
📁 CronWatchBot/
│
├── 📁 config/                    # Bot configuration and logging
│   ├── config.py                 # Environment variable loading (gitignored)
│   └── logging.py                # Logging setup & HTTP filter
├── 📄 .env.example               # Environment variables template
│
├── 📁 handlers/                  # Telegram command handlers
│   ├── basic.py                  # Core commands: /start, /help
│   ├── crontab_manage.py         # Crontab commands: /crontab_*
│   ├── shared.py                 # Auth & error handling utilities
│   └── urlwatch_manage.py        # URL commands: /add, /edit, /delete, /list
│
├── 📁 helpers/                   # Core utilities and business logic
│   ├── crontab_helpers.py        # Crontab operations
│   └── urlwatch_helpers.py       # URL file operations & validation
│
├── 🐍 main.py                    # Bot entry point
├── 📄 pyproject.toml             # Dependencies (uv managed)
├── 📄 README.md                  # Documentation
└── 📜 LICENSE                    # MIT License
```

**Architecture Overview:**
- **config/**: Application configuration and logging infrastructure
- **handlers/**: Telegram bot command handlers with authentication and error handling
- **helpers/**: Core business logic for crontab and urlwatch operations
- **main.py**: Bot initialization and command registration

## Requirements
- urlwatch (installed and configured)
- crontab (cron service enabled)
- uv (recommended, for environment management)
- Telegram bot token and User ID (create bot and get token from @BotFather from Telegram and keep it secret)

## Installation
1. **Clone the repository:**
    ```bash
    git clone https://github.com/AnkS4/CronWatchBot
    cd CronWatchBot
    ```
2. **Create and sync uv environment:**
    ```bash
    uv sync
    ```
3. **Configure your bot:**
    - Copy `.env.example` to `.env`:
      ```bash
      cp .env.example .env
      ```
    - Edit `.env` with your bot configuration:
      ```bash
      TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
      ALLOWED_USER_IDS=123456789,987654321
      ```
    - Replace the example values with your actual bot token and user IDs.
    - `.env` is excluded from git for security (see `.gitignore`).

4. **Ensure urlwatch is set up:**
    - The bot expects your urlwatch jobs file at `~/.config/urlwatch/urls.yaml` by default.

5. **Configure urlwatch Telegram notifications:**
    - Edit the urlwatch configuration file:
      ```bash
      nano ~/.config/urlwatch/urlwatch.yaml
      ```
    - Find the `telegram:` section and update it with your bot credentials:
      ```yaml
      telegram:
        bot_token: 'YOUR_BOT_TOKEN'  # Same as TELEGRAM_BOT_TOKEN in .env
        chat_id: 'YOUR_USER_ID'      # Your Telegram user ID
        enabled: true                # Must be true to receive notifications
        monospace: false
        silent: false
      ```
    - **Important**: Set `enabled: true` to receive Telegram notifications when urlwatch detects changes.
    - Without this configuration, urlwatch will only show changes in the terminal but won't send notifications.

## How to Use
- Run the bot:
    ```bash
    uv run python main.py
    ```
- Start chatting with your bot on Telegram. Use `/start` to get started.

### Quick Start for the Bot Interaction

Start the bot and use `/start` to see available commands.

1. Add a job to watch a website:
```
/add https://github.com/AnkS4/CronWatchBot CronWatchBot Repo
```

2. Edit the job to get specific information from the website:
```
/editfilter 1 xpath://span[@id="repo-stars-counter-star"] html2text strip
```

3. Add a job to run urlwatch job 1 every 30 minutes:
```
/crontab_add 1 30
```

### Full Bot Commands List

#### Bot Management Commands
- `/start` — Show quick start message
- `/help` — Show detailed help message

#### Urlwatch Management Commands
- `/view` — View all urlwatch jobs
- `/add <url> [name]` — Add a new job
- `/edit <index> <url> [name]` — Edit a job's URL and name
- `/editfilter <index> [filters...]` — Edit filters for a job
- `/editprop <index> [props...]` — Edit properties for a job
- `/delete <index>` — Delete a job

#### Crontab Management Commands
- `/crontab_view` — View all urlwatch jobs in crontab
- `/crontab_add <job_index> <minutes>` — Add a scheduled job (runs the selected urlwatch job every N minutes)
- `/crontab_edit <index> <minutes>` — Edit a scheduled job
- `/crontab_delete <index>` — Delete a scheduled job

## Troubleshooting

### Common Issues

**No notifications from urlwatch:**
- Ensure urlwatch Telegram reporter is enabled: `enabled: true` in `~/.config/urlwatch/urlwatch.yaml`
- Verify bot token and chat ID match your bot configuration
- Test manually: `urlwatch <job_index>` should send a Telegram notification

**Cron jobs not running:**
- Check cron service is enabled: `systemctl status cron`
- Verify crontab entries: `crontab -l` should show urlwatch commands
- Ensure urlwatch command syntax is correct: `urlwatch <index>` (not `urlwatch --jobs <index>`)
- If you created jobs before updating the bot code, recreate them: `/crontab_delete <index>` then `/crontab_add <job_index> <minutes>`

**Cron jobs continue running independently:**
- ⚠️ **Important**: Once cron jobs are added successfully, they run independently of the bot application
- You will continue to receive urlwatch notifications even after stopping `main.py`
- Cron jobs are managed by the system cron service, not the Python bot process
- **Requirements for notifications to work**:
  - System must be running (not shut down or suspended)
  - Internet connection must be active (to fetch URLs and send Telegram messages)
  - urlwatch Telegram reporter must remain configured in `~/.config/urlwatch/urlwatch.yaml`
- Use `/crontab_delete` to stop scheduled monitoring if needed

**Manual configuration conflicts:**
- ⚠️ **Important**: Do not manually edit `~/.config/urlwatch/urls.yaml` or crontab entries while using the bot
- Manual deletions or edits can cause index mismatches between URL entries and cron jobs
- If manual changes are made, use `/crontab_delete` and `/crontab_add` to recreate jobs with correct indices
- The bot automatically synchronizes crontab indices when URLs are deleted via `/delete` command

**Bot not responding:**
- Check bot token is valid and matches the bot you created
- Ensure your user ID is in `ALLOWED_USER_IDS`
- Check logs for error messages when running the bot

## Security
- **Authentication**: Only user IDs listed in `ALLOWED_USER_IDS` can use the bot
- **Configuration**: Never commit your `.env` file to version control (automatically gitignored)
- **Environment variables**: Sensitive data stored in environment variables, not code
- **Input validation**: All user inputs are validated before processing
- **Command injection protection**: Job indices and parameters are strictly validated
- **Reserved field protection**: Critical fields (url, name, filter) cannot be modified via property commands
- **File operations**: Atomic writes prevent data corruption during concurrent operations

## Environment Variables
The bot uses the following environment variables (defined in `.env`):

**Required:**
- `TELEGRAM_BOT_TOKEN` - Your bot token from @BotFather
- `ALLOWED_USER_IDS` - Comma-separated list of allowed Telegram user IDs
