"""Pytest configuration and fixtures."""

from pathlib import Path
import tempfile

from _pytest.monkeypatch import MonkeyPatch


def pytest_configure(config):
    """Set environment variables before test collection begins."""
    mp = MonkeyPatch()
    mp.setenv("TELEGRAM_BOT_TOKEN", "test_token")
    mp.setenv("URLS_FILE", str(Path(tempfile.gettempdir()) / "test_urls.yaml"))
    mp.setenv("ALLOWED_USER_IDS", "123456789")
