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
    """Load URL entries from YAML file.
    
    Reads and parses the urlwatch URLs YAML file. Validates file size
    to prevent loading excessively large files.
    
    Returns:
        List[Dict[str, Any]]: List of URL entry dictionaries. Empty list if
            file doesn't exist, is too large, or has parsing errors.
    
    Note:
        Maximum file size is limited to MAX_FILE_SIZE (10MB) for safety.
    """
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
    """Write URL entries to YAML file atomically.
    
    Uses atomic write operation (write to temp file, then move) to prevent
    data corruption if the write operation is interrupted.
    
    Args:
        urls: List of URL entry dictionaries to save.
    
    Returns:
        bool: True if save was successful, False otherwise.
    
    Note:
        Creates the parent directory if it doesn't exist.
    """
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
    """Validate URL format.
    
    Checks if the URL has a valid scheme (http/https) and network location.
    
    Args:
        url: URL string to validate.
    
    Returns:
        bool: True if URL is valid, False otherwise.
    
    Examples:
        >>> validate_url('https://example.com')
        True
        >>> validate_url('ftp://example.com')
        False
        >>> validate_url('not-a-url')
        False
    """
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme in ("http", "https") and parsed.netloc)
    except (ValueError, TypeError, AttributeError):
        return False

def get_display_name(entry: Dict[str, Any]) -> str:
    """Get display name for URL entry.
    
    Returns the 'name' field if present, otherwise falls back to 'url',
    or 'Unknown' if neither exists.
    
    Args:
        entry: URL entry dictionary.
    
    Returns:
        str: Display name for the entry.
    
    Examples:
        >>> get_display_name({'name': 'My Site', 'url': 'https://example.com'})
        'My Site'
        >>> get_display_name({'url': 'https://example.com'})
        'https://example.com'
    """
    return entry.get('name', entry.get('url', 'Unknown'))

def find_url_by_name(urls: List[Dict[str, Any]], name_or_index: str) -> Optional[int]:
    """Find URL index by name or index number.
    
    Attempts to find a URL entry by:
    1. First trying to parse as a 1-based numeric index
    2. Then searching by name (case-insensitive)
    
    Args:
        urls: List of URL entry dictionaries.
        name_or_index: Either a numeric index (1-based) or entry name.
    
    Returns:
        Optional[int]: Zero-based index if found, None otherwise.
    
    Examples:
        >>> urls = [{'name': 'Site 1'}, {'name': 'Site 2'}]
        >>> find_url_by_name(urls, '1')
        0
        >>> find_url_by_name(urls, 'site 2')
        1
    """
    # Try to find by index first
    try:
        idx = int(name_or_index) - 1
        if 0 <= idx < len(urls):
            return idx
    except ValueError:
        pass

    # Try to find by name
    for i, entry in enumerate(urls):
        if entry.get('name', '').lower() == name_or_index.lower():
            return i

    return None

def format_url_summary(entry: Dict[str, Any], index: int) -> str:
    """Format a summary of URL entry for display.
    
    Creates a formatted string with emoji icons showing the entry's name,
    URL, filters (if any), and additional properties.
    
    Args:
        entry: URL entry dictionary.
        index: 1-based index of the entry.
    
    Returns:
        str: Formatted summary string with Markdown formatting.
    
    Example output:
        📌 *Example Site*
           🔗 `https://example.com`
           🔎 `css:div.content, html2text`
           ⚙️ `timeout: 30`
    """
    name = get_display_name(entry)
    url = entry.get('url', '')
    summary = f"📌 *{name}*\n   🔗 `{url}`"

    if filters := entry.get('filter'):
        filters_str = ', '.join(str(f) for f in filters) if isinstance(filters, list) else str(filters)
        summary += f"\n   🔎 `{filters_str}`"

    if props := [f"{k}: {v}" for k, v in entry.items() if k not in ('name', 'url', 'filter')]:
        summary += f"\n   ⚙️ `{'; '.join(props)}`"

    return summary

def validate_index(idx_str: str, urls: List[Dict[str, Any]]) -> Optional[int]:
    """Validate and convert index string to integer.
    
    Converts a 1-based index string to a zero-based integer index,
    validating that it's within the valid range for the URLs list.
    
    Args:
        idx_str: Index string to validate (1-based).
        urls: List of URL entries to validate against.
    
    Returns:
        Optional[int]: Zero-based index if valid, None otherwise.
    
    Examples:
        >>> urls = [{'url': 'a'}, {'url': 'b'}]
        >>> validate_index('1', urls)
        0
        >>> validate_index('3', urls)
        None
        >>> validate_index('abc', urls)
        None
    """
    try:
        idx = int(idx_str) - 1
        return idx if 0 <= idx < len(urls) else None
    except ValueError:
        return None
