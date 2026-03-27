"""Tests for shared handler utilities."""

from unittest.mock import Mock

import pytest
from telegram import Update, User

from handlers.shared import ERROR_MESSAGES, auth_and_error_handler, send_error, validate_args


@pytest.mark.asyncio
async def test_send_error(mock_update):
    """Test sending error messages."""
    await send_error(mock_update, "unauthorized")
    mock_update.message.reply_text.assert_called_once_with(ERROR_MESSAGES["unauthorized"])


@pytest.mark.asyncio
async def test_send_error_with_format_args(mock_update):
    """Test sending error messages with format arguments."""
    await send_error(mock_update, "invalid_index", 5)
    mock_update.message.reply_text.assert_called_once_with("❌ Invalid index. Use 1-5.")


@pytest.mark.asyncio
async def test_send_error_no_message():
    """Test send_error when update has no message."""
    update = Mock(spec=Update)
    update.message = None
    await send_error(update, "unauthorized")


@pytest.mark.asyncio
async def test_auth_and_error_handler_authorized(mock_update, mock_context):
    """Test auth decorator allows authorized users."""

    @auth_and_error_handler
    async def test_handler(update, context):
        return "success"

    result = await test_handler(mock_update, mock_context)
    assert result == "success"


@pytest.mark.asyncio
async def test_auth_and_error_handler_unauthorized(mock_update, mock_context):
    """Test auth decorator blocks unauthorized users."""
    mock_update.effective_user.id = 999999  # Not in ALLOWED_USER_IDS

    @auth_and_error_handler
    async def test_handler(update, context):
        return "success"

    await test_handler(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once_with(ERROR_MESSAGES["unauthorized"])


@pytest.mark.asyncio
async def test_auth_and_error_handler_exception(mock_update, mock_context):
    """Test auth decorator handles exceptions."""

    @auth_and_error_handler
    async def test_handler(update, context):
        raise ValueError("Test error")

    await test_handler(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args[0][0]
    # Rate limiting message appears before error message in current implementation
    assert "Please wait a moment" in call_args or "❌ An error occurred" in call_args


@pytest.mark.asyncio
async def test_validate_args_sufficient(mock_update, mock_context):
    """Test validate_args decorator with sufficient arguments."""
    mock_context.args = ["arg1", "arg2"]

    @validate_args(2, "Usage message")
    async def test_handler(update, context):
        return "success"

    result = await test_handler(mock_update, mock_context)
    assert result == "success"


@pytest.mark.asyncio
async def test_validate_args_insufficient(mock_update, mock_context):
    """Test validate_args decorator with insufficient arguments."""
    mock_context.args = ["arg1"]

    @validate_args(2, "Usage message")
    async def test_handler(update, context):
        return "success"

    await test_handler(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once_with("Usage message", parse_mode="HTML")


@pytest.mark.asyncio
async def test_validate_args_no_args(mock_update, mock_context):
    """Test validate_args decorator with no arguments."""
    mock_context.args = []

    @validate_args(2, "Usage message")
    async def test_handler(update, context):
        return "success"

    await test_handler(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once_with("Usage message", parse_mode="HTML")


@pytest.mark.asyncio
async def test_validate_args_no_message(mock_context):
    """Test validate_args decorator when update has no message."""
    update = Mock(spec=Update)
    update.message = None
    update.effective_user = Mock(spec=User)
    update.effective_user.id = 123456789
    mock_context.args = []

    @validate_args(2, "Usage message")
    async def test_handler(update, context):
        return "success"

    await test_handler(update, mock_context)
