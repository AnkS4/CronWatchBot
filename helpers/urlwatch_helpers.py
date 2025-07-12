import os
import yaml
import tempfile
import shutil
from typing import List, Dict, Optional
from urllib.parse import urlparse
from config.logging import logger

# Dynamically resolve the user's urlwatch configuration file path
URLS_FILE = os.path.expanduser("~/.config/urlwatch/urls.yaml")

def load_urls() -> List[Dict]:
    """Load URL entries from YAML file."""
    if not os.path.exists(URLS_FILE):
        logger.warning("URLs file not found at %s", URLS_FILE)
        return []
    try:
        with open(URLS_FILE, "r") as f:
            data = list(yaml.safe_load_all(f))
            return [entry for entry in data if entry] if data else []
    except yaml.YAMLError as e:
        logger.error("YAML parsing error: %s", e)
        return []
    except Exception as e:
        logger.error("Error loading URLs file: %s", e)
        return []

def save_urls(urls: List[Dict]) -> None:
    """Write URL entries to YAML file atomically."""
    os.makedirs(os.path.dirname(URLS_FILE), exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=os.path.dirname(URLS_FILE)) as tmp:
        yaml.safe_dump_all(urls, tmp, sort_keys=False, default_flow_style=False)
        temp_name = tmp.name
    shutil.move(temp_name, URLS_FILE)
    logger.info("Successfully saved %d URLs to %s", len(urls), URLS_FILE)

def validate_url(url: str) -> bool:
    """Validate URL format."""
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme in ("http", "https") and parsed.netloc)
    except Exception:
        return False

def get_display_name(entry: Dict) -> str:
    """Get display name for URL entry."""
    return entry.get('name', entry.get('url', 'Unnamed entry'))

def validate_index(idx_str: str, urls: List[Dict]) -> Optional[int]:
    """Validate and convert index string to integer."""
    try:
        idx = int(idx_str) - 1
        if 0 <= idx < len(urls):
            return idx
        return None
    except ValueError:
        return None
