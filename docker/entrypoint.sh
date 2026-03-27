#!/bin/sh
set -e

# Fail fast: prints to stderr and exits if either variable is unset/empty
: "${TELEGRAM_BOT_TOKEN:?TELEGRAM_BOT_TOKEN not set}"
: "${ALLOWED_USER_IDS:?ALLOWED_USER_IDS not set}"

URLWATCH_DIR="/home/cronwatchbot/.config/urlwatch"

# Setup URLWatch directory and files
su-exec cronwatchbot mkdir -p "$URLWATCH_DIR"
su-exec cronwatchbot touch "$URLWATCH_DIR/urls.yaml"

if [ ! -f "$URLWATCH_DIR/urlwatch.yaml" ]; then
    # SECURITY NOTE: Bot token is written to disk here because urlwatch does not
    # support environment variable interpolation. Mitigations: chmod 600, non-root
    # user ownership, container isolation. See README.md for security considerations.
    #
    # tee opens the *output* file as cronwatchbot (correct ownership from birth).
    # The heredoc's stdin is the root shell's fd 0 — su-exec never touches it,
    # so there is no /dev/stdin permission issue.
    su-exec cronwatchbot tee "$URLWATCH_DIR/urlwatch.yaml" > /dev/null << EOF
display:
  empty-diff: false
  error: true
  new: false
  unchanged: false

report:
  telegram:
    bot_token: '${TELEGRAM_BOT_TOKEN}'
    chat_id: '${ALLOWED_USER_IDS%%,*}'
    enabled: true
EOF
    su-exec cronwatchbot chmod 600 "$URLWATCH_DIR/urlwatch.yaml"
fi

# Setup crontab directory and permissions
mkdir -p /var/spool/cron/crontabs
chown root:cronwatchbot /var/spool/cron/crontabs
chmod 775 /var/spool/cron/crontabs
touch /var/spool/cron/crontabs/cronwatchbot
chown cronwatchbot:cronwatchbot /var/spool/cron/crontabs/cronwatchbot
chmod 600 /var/spool/cron/crontabs/cronwatchbot

# Fix cache file ownership if exists
if [ -f "$URLWATCH_DIR/cache.db" ]; then
    chown cronwatchbot:cronwatchbot "$URLWATCH_DIR/cache.db"
fi

# Start cron daemon (root required for BusyBox crond)
# -f: foreground, -l 8: debug logging, -L: log to stdout for docker logs
crond -f -l 8 -L /dev/stdout &
CROND_PID=$!

# Process management
cleanup() {
    kill "$BOT_PID" "$CROND_PID" 2>/dev/null
    wait 2>/dev/null; exit 0
}
trap cleanup TERM INT

# Start bot and cron
su-exec cronwatchbot python main.py &
BOT_PID=$!

# Wait for bot and propagate exit code
wait "$BOT_PID" && BOT_EXIT=0 || BOT_EXIT=$?
kill "$CROND_PID" 2>/dev/null
wait "$CROND_PID" 2>/dev/null || true
exit "$BOT_EXIT"
