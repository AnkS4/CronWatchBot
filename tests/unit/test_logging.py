"""Tests for logging configuration."""

import logging
from unittest.mock import Mock, patch

import pytest

from config.logging import TelegramHttpxFilter, install_telegram_http_filter


@pytest.fixture
def log_record():
    """Create a mock log record."""
    record = Mock(spec=logging.LogRecord)
    record.name = "test.logger"
    record.msg = "Test message"
    record.args = ()
    return record


def test_telegram_filter_blocks_httpx_logs(log_record):
    """Test that filter blocks httpx HTTP request logs."""
    log_record.name = "httpx"
    log_record.getMessage = Mock(
        return_value="HTTP Request: POST https://api.telegram.org/bot123/getUpdates"
    )

    filter_obj = TelegramHttpxFilter()
    result = filter_obj.filter(log_record)

    assert result is False


def test_telegram_filter_blocks_httpcore_logs(log_record):
    """Test that filter blocks httpcore HTTP request logs."""
    log_record.name = "httpcore.http11"
    log_record.getMessage = Mock(
        return_value="HTTP Request: POST https://api.telegram.org/bot123/sendMessage"
    )

    filter_obj = TelegramHttpxFilter()
    result = filter_obj.filter(log_record)

    assert result is False


def test_telegram_filter_simplifies_telegram_api_logs(log_record):
    """Test that filter simplifies Telegram API logs."""
    log_record.name = "telegram.request"
    log_record.getMessage = Mock(
        return_value='HTTP Request: POST https://api.telegram.org/bot1234567890:ABCDEF/sendMessage "HTTP/1.1 200 OK"'
    )

    filter_obj = TelegramHttpxFilter()
    result = filter_obj.filter(log_record)

    assert result is True
    assert log_record.msg == "Telegram API: /sendMessage - 200"
    assert log_record.args == ()


def test_telegram_filter_simplifies_get_updates(log_record):
    """Test that filter simplifies getUpdates logs."""
    log_record.name = "telegram.ext"
    log_record.getMessage = Mock(
        return_value='HTTP Request: POST https://api.telegram.org/bot9876543210:XYZABC/getUpdates "HTTP/1.1 200 OK"'
    )

    filter_obj = TelegramHttpxFilter()
    result = filter_obj.filter(log_record)

    assert result is True
    assert log_record.msg == "Telegram API: /getUpdates - 200"


def test_telegram_filter_handles_error_status(log_record):
    """Test that filter handles non-200 status codes."""
    log_record.name = "telegram"
    log_record.getMessage = Mock(
        return_value='HTTP Request: POST https://api.telegram.org/bot123/sendPhoto "HTTP/1.1 400 Bad Request"'
    )

    filter_obj = TelegramHttpxFilter()
    result = filter_obj.filter(log_record)

    assert result is True
    assert log_record.msg == "Telegram API: /sendPhoto - 400"


def test_telegram_filter_passes_non_http_logs(log_record):
    """Test that filter passes through non-HTTP logs unchanged."""
    log_record.name = "telegram"
    log_record.getMessage = Mock(return_value="Starting bot polling")

    filter_obj = TelegramHttpxFilter()
    result = filter_obj.filter(log_record)

    assert result is True
    assert log_record.msg == "Test message"  # Unchanged


def test_telegram_filter_passes_non_telegram_api_logs(log_record):
    """Test that filter passes non-Telegram API HTTP logs."""
    log_record.name = "requests"
    log_record.getMessage = Mock(
        return_value='HTTP Request: GET https://example.com/api "HTTP/1.1 200 OK"'
    )

    filter_obj = TelegramHttpxFilter()
    result = filter_obj.filter(log_record)

    assert result is True
    assert log_record.msg == "Test message"  # Unchanged


def test_telegram_filter_pattern_matching():
    """Test the regex pattern matching directly."""
    filter_obj = TelegramHttpxFilter()

    # Valid patterns
    assert filter_obj._pattern.search(
        'POST https://api.telegram.org/bot123/sendMessage "HTTP/1.1 200'
    )
    assert filter_obj._pattern.search(
        'POST https://api.telegram.org/botABC:DEF/getUpdates "HTTP/1.1 200'
    )

    # Invalid patterns
    assert not filter_obj._pattern.search('GET https://example.com/api "HTTP/1.1 200')
    assert not filter_obj._pattern.search("No HTTP request here")


def test_install_telegram_http_filter():
    """Test installing filter on target loggers."""
    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        install_telegram_http_filter()

        # Should be called for each target logger
        assert mock_get_logger.call_count == 3
        mock_get_logger.assert_any_call("httpx")
        mock_get_logger.assert_any_call("telegram.ext")
        mock_get_logger.assert_any_call("telegram")

        # Filter should be added to each logger
        assert mock_logger.addFilter.call_count == 3


def test_install_telegram_http_filter_creates_single_filter():
    """Test that install creates one filter instance for all loggers."""
    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        install_telegram_http_filter()

        # All addFilter calls should receive the same filter instance
        filter_instances = [call[0][0] for call in mock_logger.addFilter.call_args_list]
        assert len({id(f) for f in filter_instances}) == 1  # All same instance


def test_telegram_filter_preserves_other_record_attributes(log_record):
    """Test that filter doesn't modify unrelated record attributes."""
    log_record.name = "telegram"
    log_record.levelname = "INFO"
    log_record.levelno = logging.INFO
    log_record.getMessage = Mock(return_value="Normal log message")

    filter_obj = TelegramHttpxFilter()
    filter_obj.filter(log_record)

    assert log_record.levelname == "INFO"
    assert log_record.levelno == logging.INFO
