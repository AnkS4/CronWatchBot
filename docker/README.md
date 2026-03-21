# Docker Configuration

This directory contains all Docker-related files for CronWatchBot.

## Files

- **Dockerfile** - Multi-stage build configuration using Alpine Linux
- **entrypoint.sh** - Container initialization script that:
  - Validates environment variables
  - Initializes URLWatch configuration
  - Creates empty crontab for the cronwatchbot user
  - Starts crond as root (required for BusyBox)
  - Runs the bot as non-root cronwatchbot user
  - Handles graceful shutdown of both processes

## Building

From the project root:

```bash
docker build -f docker/Dockerfile -t cronwatchbot:latest .
```

## Running

```bash
docker run -d \
  --name cronwatchbot \
  --env-file .env \
  --restart unless-stopped \
  cronwatchbot:latest
```

## Environment Variables

Required:
- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token
- `ALLOWED_USER_IDS` - Comma-separated list of allowed Telegram user IDs

## Architecture

- **Base Image**: `python:3.14.2-alpine3.23` (uses BusyBox utilities)
- **Build Tool**: `uv` for fast Python dependency installation
- **Cron**: BusyBox crond (runs as root)
- **Bot Process**: Runs as non-root `cronwatchbot` user (UID 1000)
- **Security**: SUID crontab binary allows non-root user to manage cron jobs

## Process Structure

```
PID 1: entrypoint.sh (root)
  ├─ crond -f (root) - Required for BusyBox to execute user crontabs
  └─ python main.py (cronwatchbot) - Bot process as non-root user
```
