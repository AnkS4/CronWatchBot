import os
import shutil
import tempfile
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import yaml

from config.logging import logger

URLS_FILE = os.path.expanduser("~/.config/urlwatch/urls.yaml")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB maximum file size

def load_urls() -> List[Dict[str, Any]]:
    """Load URL entries from YAML file."""
    if not os.path.exists(URLS_FILE):
        logger.warning("URLs file not found at %s", URLS_FILE)
        return []
    
    try:
        file_size = os.path.getsize(URLS_FILE)
        if file_size > MAX_FILE_SIZE:
            logger.error("URLs file exceeds maximum size: %d bytes", file_size)
            return []
        
        with open(URLS_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load_all(f)
            return [entry for entry in (data or []) if entry]
    except (yaml.YAMLError, OSError) as e:
        logger.error("Error loading URLs file: %s", e)
        return []

def save_urls(urls: List[Dict[str, Any]]) -> bool:
    """Write URL entries to YAML file atomically. Returns success status."""
    try:
        os.makedirs(os.path.dirname(URLS_FILE), exist_ok=True)
        with tempfile.NamedTemporaryFile("w", delete=False, dir=os.path.dirname(URLS_FILE), encoding="utf-8") as tmp:
            yaml.safe_dump_all(urls, tmp, sort_keys=False, default_flow_style=False)
            temp_name = tmp.name
        shutil.move(temp_name, URLS_FILE)
        logger.info("Successfully saved %d URLs to %s", len(urls), URLS_FILE)
        return True
    except (OSError, yaml.YAMLError) as e:
        logger.error("Failed to save URLs: %s", e)
        return False

def validate_url(url: str) -> bool:
    """Validate URL format."""
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme in ("http", "https") and parsed.netloc)
    except (ValueError, TypeError, AttributeError):
        return False

def get_display_name(entry: Dict[str, Any]) -> str:
    """Get display name for URL entry."""
    return entry.get('name', entry.get('url', 'Unnamed entry'))

def validate_index(idx_str: str, urls: List[Dict[str, Any]]) -> Optional[int]:
    """Validate and convert index string to integer."""
    try:
        idx = int(idx_str) - 1
        return idx if 0 <= idx < len(urls) else None
    except ValueError:
        return None
