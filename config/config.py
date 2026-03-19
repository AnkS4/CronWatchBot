import os
from typing import List, Optional

def _parse_allowed_user_ids(ids_str: str) -> List[int]:
    """Parse comma-separated user IDs from environment variable."""
    if not ids_str:
        return []
    try:
        return [int(id_str.strip()) for id_str in ids_str.split(',') if id_str.strip()]
    except ValueError as e:
        raise ValueError(f"Invalid ALLOWED_USER_IDS format: {ids_str}. Expected comma-separated integers.") from e

# Required configuration
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ALLOWED_USER_IDS = _parse_allowed_user_ids(os.getenv('ALLOWED_USER_IDS', ''))

# Validation
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

if not ALLOWED_USER_IDS:
    raise ValueError("ALLOWED_USER_IDS environment variable is required")

if not all(isinstance(user_id, int) and user_id > 0 for user_id in ALLOWED_USER_IDS):
    raise ValueError("All user IDs in ALLOWED_USER_IDS must be positive integers")
