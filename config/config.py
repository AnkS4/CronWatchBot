from dataclasses import dataclass
from os import environ

from dotenv import load_dotenv

load_dotenv()

__all__ = ["ALLOWED_USER_IDS", "TOKEN", "Settings", "settings"]


def _parse_allowed_user_ids(ids_str: str | None) -> tuple[int, ...]:
    """Parse and validate comma-separated user IDs from an environment variable.

    Returns a tuple (immutable, consistent with the frozen dataclass) of
    positive integer Telegram user IDs.

    Raises:
        ValueError: if the value is absent, blank, contains non-integers, or
                    contains non-positive integers.
    """
    if not ids_str or not ids_str.strip():
        raise ValueError("ALLOWED_USER_IDS environment variable is required and cannot be empty")

    raw_tokens = [s.strip() for s in ids_str.split(",") if s.strip()]
    if not raw_tokens:
        raise ValueError("ALLOWED_USER_IDS must contain at least one valid integer ID")

    ids: list[int] = []
    for raw in raw_tokens:
        try:
            uid = int(raw)
        except ValueError:
            raise ValueError(
                f"Invalid entry {raw!r} in ALLOWED_USER_IDS — expected integers "
                f"separated by commas. Full value received: {ids_str!r}"
            ) from None  # suppress the chained "invalid literal for int()" noise
        if uid <= 0:
            raise ValueError(f"User ID {uid} in ALLOWED_USER_IDS must be a positive integer")
        ids.append(uid)

    return tuple(ids)


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable bot configuration loaded from environment variables.

    `frozen=True`  — prevents accidental mutation after startup.
    `slots=True`   — lowers per-instance memory and blocks dynamic attribute
                     creation, which pairs well with frozen semantics.
    """

    telegram_bot_token: str
    allowed_user_ids: tuple[int, ...]  # tuple, not list — mutable fields in a
    # frozen dataclass are a footgun


def _load_settings() -> Settings:
    """Load, validate, and return a Settings instance from the environment.

    Called once at import time.  Any misconfiguration raises immediately so the
    process fails fast rather than crashing mid-request.
    """
    token = environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required and cannot be empty")

    return Settings(
        telegram_bot_token=token,
        allowed_user_ids=_parse_allowed_user_ids(environ.get("ALLOWED_USER_IDS")),
    )


# Module-level singleton — constructed once, validated at import, then
# re-exported as typed aliases for ergonomic access throughout the codebase.
settings: Settings = _load_settings()
TOKEN: str = settings.telegram_bot_token
ALLOWED_USER_IDS: tuple[int, ...] = settings.allowed_user_ids
