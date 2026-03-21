# syntax=docker/dockerfile:1

# ── Build stage ───────────────────────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:0.10.12-python3.14-alpine3.23 AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

# Install dependencies first (changes less often than source code)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# Install project (layer invalidated only when source changes)
COPY config/ ./config/
COPY handlers/ ./handlers/
COPY helpers/ ./helpers/
COPY main.py ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen


# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.14.2-alpine3.23 AS runtime

LABEL org.opencontainers.image.title="cronwatchbot" \
      org.opencontainers.image.description="Telegram bot for managing urlwatch and crontab" \
      org.opencontainers.image.source="https://github.com/AnkS4/CronWatchBot" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

RUN apk add --no-cache su-exec busybox-suid \
    && adduser -D -u 1000 -s /sbin/nologin cronwatchbot \
    && mkdir -p /home/cronwatchbot/.config/urlwatch \
    && chown -R cronwatchbot:cronwatchbot /home/cronwatchbot \
    # Pre-create the crontab file so python-crontab can write to it immediately
    # without the entrypoint having to probe and create it at every start.
    # /var/spool/cron/crontabs is root:root 0755 (BusyBox crond requirement);
    # individual crontab files must be owned by their user and chmod 600.
    && mkdir -p /var/spool/cron/crontabs \
    && touch /var/spool/cron/crontabs/cronwatchbot \
    && chown cronwatchbot:cronwatchbot /var/spool/cron/crontabs/cronwatchbot \
    && chmod 600 /var/spool/cron/crontabs/cronwatchbot

WORKDIR /app

COPY --from=builder --chown=cronwatchbot:cronwatchbot /app /app
COPY --chmod=755 docker/entrypoint.sh /entrypoint.sh

# Verify both the bot process and the cron daemon are alive.
# pgrep exits 1 on no match — no "|| exit 1" needed.
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD pgrep -f "python.*main.py" && pgrep crond

ENTRYPOINT ["/entrypoint.sh"]
