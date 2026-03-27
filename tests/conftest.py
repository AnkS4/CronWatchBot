"""Pytest configuration and fixtures."""

import pytest
from pathlib import Path
import tempfile
from unittest.mock import AsyncMock, Mock

from _pytest.monkeypatch import MonkeyPatch
from telegram import Update, User
from telegram.ext import ContextTypes


def pytest_configure(config):
    """Set environment variables before test collection begins."""
    mp = MonkeyPatch()
    mp.setenv("TELEGRAM_BOT_TOKEN", "test_token")
    mp.setenv("URLS_FILE", str(Path(tempfile.gettempdir()) / "test_urls.yaml"))
    mp.setenv("ALLOWED_USER_IDS", "123456789")


@pytest.fixture
def mock_update():
    """Mock Telegram Update object for testing."""
    update = Mock(spec=Update)
    update.effective_user = Mock(spec=User)
    update.effective_user.id = 123456789
    update.message = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Mock Telegram Context object for testing."""
    context = Mock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []
    return context
