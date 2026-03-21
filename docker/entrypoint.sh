#!/bin/sh
set -e

# Fail fast: prints to stderr and exits if either variable is unset/empty
: "${TELEGRAM_BOT_TOKEN:?TELEGRAM_BOT_TOKEN not set}"
: "${ALLOWED_USER_IDS:?ALLOWED_USER_IDS not set}"

URLWATCH_DIR="/home/cronwatchbot/.config/urlwatch"

# Ensure config directory exists (safety net for volume-mount scenarios where
# the build-time directory may be shadowed)
su-exec cronwatchbot mkdir -p "$URLWATCH_DIR"
[ -f "$URLWATCH_DIR/urls.yaml" ] || su-exec cronwatchbot touch "$URLWATCH_DIR/urls.yaml"

if [ ! -f "$URLWATCH_DIR/urlwatch.yaml" ]; then
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

# -f keeps crond in the foreground so & captures its real PID for clean teardown.
# (Without -f BusyBox crond self-daemonises and $! would be the wrong PID.)
# Root is required: BusyBox crond reads /var/spool/cron/crontabs/<user>.
crond -f &
CROND_PID=$!

# Tear down both processes cleanly on SIGTERM / SIGINT
cleanup() {
    kill "$BOT_PID"   2>/dev/null
    kill "$CROND_PID" 2>/dev/null
    wait              2>/dev/null
    exit 0
}
trap cleanup TERM INT

# Background the bot so the trap above stays reachable.
# (exec would replace this shell, making the trap unreachable and leaking crond.)
su-exec cronwatchbot python main.py &
BOT_PID=$!

# Capture the bot's exit code without triggering set -e on a non-zero return.
# If set -e fires on wait, a bot crash would skip cleanup and leak crond.
wait "$BOT_PID" && BOT_EXIT=0 || BOT_EXIT=$?

# Bot exited on its own (crash or clean shutdown): tear down crond and surface
# the exit code so container restart policies work correctly.
kill "$CROND_PID" 2>/dev/null
wait "$CROND_PID" 2>/dev/null || true
exit "$BOT_EXIT"
