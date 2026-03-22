#!/bin/bash
set -e

# Simple backup script for CronWatchBot
# Creates timestamped backup of Docker volumes

BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)
BACKUP_FILE="backup-${TIMESTAMP}.tar.gz"

echo "Creating backup directory..."
mkdir -p "$BACKUP_DIR"

echo "Backing up URLWatch data..."
docker run --rm \
  -v docker_urlwatch-data:/data \
  -v "$(pwd)/$BACKUP_DIR":/backup \
  alpine tar czf "/backup/urlwatch-${TIMESTAMP}.tar.gz" -C /data .

echo "Backing up crontab data..."
docker run --rm \
  -v docker_crontab-data:/data \
  -v "$(pwd)/$BACKUP_DIR":/backup \
  alpine tar czf "/backup/crontab-${TIMESTAMP}.tar.gz" -C /data .

echo "Backing up crontab entries (if container is running)..."
if docker ps -q -f name=cronwatchbot > /dev/null 2>&1; then
  docker exec cronwatchbot crontab -l -u cronwatchbot > "$BACKUP_DIR/crontab-entries-${TIMESTAMP}.txt" 2>/dev/null || echo "No crontab entries found"
fi

echo ""
echo "✅ Backup completed successfully!"
echo "Files created in $BACKUP_DIR/:"
ls -lh "$BACKUP_DIR"/*${TIMESTAMP}*
