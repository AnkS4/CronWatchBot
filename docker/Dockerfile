# syntax=docker/dockerfile:1

# ── Build stage ───────────────────────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:0.11-python3.14-alpine3.23 AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

# Install dependencies first (changes less often than source code)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Install project (layer invalidated only when source changes)
COPY config/ ./config/
COPY handlers/ ./handlers/
COPY helpers/ ./helpers/
COPY utils/ ./utils/
COPY main.py ./
COPY README.md ./
COPY LICENSE ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.14-alpine3.23 AS runtime

LABEL org.opencontainers.image.title="cronwatchbot" \
      org.opencontainers.image.description="Telegram bot for managing urlwatch and crontab" \
      org.opencontainers.image.source="https://github.com/AnkS4/CronWatchBot" \
      org.opencontainers.image.licenses="GPL-3.0-or-later"

# PYTHONPYCACHEPREFIX: the builder already compiled .pyc files via UV_COMPILE_BYTECODE;
# this redirects any new writes (e.g. from third-party code at runtime) out of /app.
# PYTHONDONTWRITEBYTECODE is intentionally absent — suppressing .pyc conflicts with the
# pre-compiled bytecode copied from the builder stage.
ENV PYTHONUNBUFFERED=1 \
    PYTHONPYCACHEPREFIX=/tmp/.pycache \
    PATH="/app/.venv/bin:$PATH"

# Note: this stage runs as root so the entrypoint can start crond (which requires root
# for system crontab management). The entrypoint is responsible for dropping to the
# cronwatchbot user via su-exec before exec-ing the bot process. USER is not set here
# because setting it would prevent the entrypoint from starting crond at all.
RUN apk --no-cache upgrade && \
    apk add --no-cache su-exec busybox-suid \
    # Security: Remove pip to reduce attack surface - uv-managed venv doesn't need pip
    && python -m pip uninstall -y pip \
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

# Security: Tighten file permissions
RUN chmod 755 /app && \
    find /app -type f -name "*.py" -exec chmod 644 {} \; && \
    chmod 755 /app/main.py && \
    chmod -R 755 /app/.venv/bin && \
    ln -sf /app/.venv/bin/urlwatch /usr/bin/urlwatch

# Verify both the bot process and the cron daemon are alive.
# pgrep exits 1 on no match — no "|| exit 1" needed.
HEALTHCHECK --interval=60s --timeout=10s --start-period=15s --retries=3 \
    CMD pgrep -f "python.*main.py" && pgrep crond

ENTRYPOINT ["/entrypoint.sh"]
