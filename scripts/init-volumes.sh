#!/bin/bash
set -e

# Simple initialization script for CronWatchBot
# Creates necessary directories and sets up environment

echo "Initializing CronWatchBot..."

# Create backups directory
echo "Creating backups directory..."
mkdir -p backups

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo ""
    echo "⚠️  Please edit .env and add your credentials:"
    echo "   - TELEGRAM_BOT_TOKEN (get from @BotFather)"
    echo "   - ALLOWED_USER_IDS (get from @userinfobot)"
    echo ""
else
    echo "✅ .env file already exists"
fi

# Check if Docker volumes exist
echo "Checking Docker volumes..."
if docker volume ls | grep -q docker_urlwatch-data; then
    echo "✅ URLWatch volume exists"
else
    echo "ℹ️  URLWatch volume will be created on first run"
fi

if docker volume ls | grep -q docker_crontab-data; then
    echo "✅ Crontab volume exists"
else
    echo "ℹ️  Crontab volume will be created on first run"
fi

echo ""
echo "✅ Initialization complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your credentials"
echo "  2. Run: docker compose -f docker/docker-compose.yml up -d"
echo "  3. Check logs: docker compose -f docker/docker-compose.yml logs -f"
