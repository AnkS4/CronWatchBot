#!/bin/bash
set -e

# Simple restore script for CronWatchBot
# Restores data from backup files

if [ $# -eq 0 ]; then
    echo "Usage: $0 <timestamp>"
    echo "Example: $0 2026-03-22-161530"
    echo ""
    echo "Available backups:"
    ls -1 backups/urlwatch-*.tar.gz 2>/dev/null | sed 's/.*urlwatch-\(.*\)\.tar\.gz/  \1/' || echo "  No backups found"
    exit 1
fi

TIMESTAMP=$1
BACKUP_DIR="backups"

if [ ! -f "$BACKUP_DIR/urlwatch-${TIMESTAMP}.tar.gz" ]; then
    echo "❌ Error: Backup not found for timestamp $TIMESTAMP"
    exit 1
fi

echo "⚠️  This will restore data from backup: $TIMESTAMP"
echo "Current data will be replaced!"
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore cancelled"
    exit 0
fi

echo "Stopping container..."
docker compose -f docker/docker-compose.yml down

echo "Restoring URLWatch data..."
docker run --rm \
  -v docker_urlwatch-data:/data \
  -v "$(pwd)/$BACKUP_DIR":/backup \
  alpine sh -c "rm -rf /data/* && tar xzf /backup/urlwatch-${TIMESTAMP}.tar.gz -C /data"

echo "Restoring crontab data..."
docker run --rm \
  -v docker_crontab-data:/data \
  -v "$(pwd)/$BACKUP_DIR":/backup \
  alpine sh -c "rm -rf /data/* && tar xzf /backup/crontab-${TIMESTAMP}.tar.gz -C /data"

echo "Starting container..."
docker compose -f docker/docker-compose.yml up -d

echo ""
echo "✅ Restore completed successfully!"
echo "Container is starting up..."
