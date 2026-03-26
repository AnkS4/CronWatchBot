"""Tests for configuration module."""

from unittest.mock import patch

import pytest

from config.config import Settings, _load_settings, _parse_allowed_user_ids


def test_parse_allowed_user_ids_valid():
    """Test parsing valid comma-separated user IDs."""
    result = _parse_allowed_user_ids("123,456,789")
    assert result == (123, 456, 789)


def test_parse_allowed_user_ids_with_spaces():
    """Test parsing user IDs with extra spaces."""
    result = _parse_allowed_user_ids("  123 ,  456  , 789  ")
    assert result == (123, 456, 789)


def test_parse_allowed_user_ids_single():
    """Test parsing single user ID."""
    result = _parse_allowed_user_ids("123456789")
    assert result == (123456789,)


def test_parse_allowed_user_ids_empty_string():
    """Test parsing empty string raises ValueError."""
    with pytest.raises(ValueError, match="required and cannot be empty"):
        _parse_allowed_user_ids("")


def test_parse_allowed_user_ids_none():
    """Test parsing None raises ValueError."""
    with pytest.raises(ValueError, match="required and cannot be empty"):
        _parse_allowed_user_ids(None)


def test_parse_allowed_user_ids_whitespace_only():
    """Test parsing whitespace-only string raises ValueError."""
    with pytest.raises(ValueError, match="required and cannot be empty"):
        _parse_allowed_user_ids("   ")


def test_parse_allowed_user_ids_invalid_integer():
    """Test parsing non-integer values raises ValueError."""
    with pytest.raises(ValueError, match="expected integers"):
        _parse_allowed_user_ids("123,abc,456")


def test_parse_allowed_user_ids_negative():
    """Test parsing negative user IDs raises ValueError."""
    with pytest.raises(ValueError, match="must be a positive integer"):
        _parse_allowed_user_ids("123,-456,789")


def test_parse_allowed_user_ids_zero():
    """Test parsing zero user ID raises ValueError."""
    with pytest.raises(ValueError, match="must be a positive integer"):
        _parse_allowed_user_ids("0,123")


def test_parse_allowed_user_ids_empty_after_split():
    """Test parsing string with only commas raises ValueError."""
    with pytest.raises(ValueError, match="at least one valid integer"):
        _parse_allowed_user_ids(",,,")


def test_settings_immutable():
    """Test that Settings is immutable (frozen)."""
    with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "test_token", "ALLOWED_USER_IDS": "123"}):
        settings = _load_settings()

        with pytest.raises(AttributeError):
            settings.telegram_bot_token = "new_token"


def test_settings_has_slots():
    """Test that Settings uses slots for memory efficiency."""
    with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "test_token", "ALLOWED_USER_IDS": "123"}):
        settings = _load_settings()

        # Frozen dataclass prevents setting any attributes
        with pytest.raises((AttributeError, TypeError)):
            settings.new_attribute = "value"


def test_load_settings_missing_token():
    """Test loading settings without TELEGRAM_BOT_TOKEN raises ValueError."""
    with (
        patch.dict("os.environ", {"ALLOWED_USER_IDS": "123"}, clear=True),
        pytest.raises(ValueError, match=r"TELEGRAM_BOT_TOKEN.*required"),
    ):
        _load_settings()


def test_load_settings_empty_token():
    """Test loading settings with empty token raises ValueError."""
    with (
        patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "   ", "ALLOWED_USER_IDS": "123"}),
        pytest.raises(ValueError, match=r"TELEGRAM_BOT_TOKEN.*required"),
    ):
        _load_settings()


def test_load_settings_missing_user_ids():
    """Test loading settings without ALLOWED_USER_IDS raises ValueError."""
    with (
        patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "test_token"}, clear=True),
        pytest.raises(ValueError, match="ALLOWED_USER_IDS"),
    ):
        _load_settings()


def test_load_settings_valid():
    """Test loading valid settings."""
    with patch.dict(
        "os.environ", {"TELEGRAM_BOT_TOKEN": "test_token_123", "ALLOWED_USER_IDS": "111,222"}
    ):
        settings = _load_settings()

        assert settings.telegram_bot_token == "test_token_123"
        assert settings.allowed_user_ids == (111, 222)


def test_settings_type_annotations():
    """Test that Settings has correct type annotations."""
    assert isinstance(Settings.__annotations__["telegram_bot_token"], type)
    assert Settings.__annotations__["telegram_bot_token"] is str
    assert Settings.__annotations__["allowed_user_ids"] == tuple[int, ...]
