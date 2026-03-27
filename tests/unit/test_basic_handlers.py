"""Tests for basic bot handlers."""

from unittest.mock import AsyncMock, Mock

import pytest
from telegram import Update, User

from handlers.basic import edited_message, help_command, start, unknown

# Comprehensive tests for help_command


@pytest.mark.asyncio
async def test_help_command_sends_help_text(mock_update, mock_context):
    """Test that help command sends comprehensive help text."""
    await help_command(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    help_text = call_args[0][0]

    # Verify key sections are present
    assert "CronWatchBot" in help_text
    assert "Help" in help_text or "help" in help_text
    assert "/add" in help_text
    assert "/list" in help_text
    assert "/crontab" in help_text
    assert "HTML" in str(call_args[1])


@pytest.mark.asyncio
async def test_help_command_with_no_message(mock_context):
    """Test help command when update has no message."""
    update = Mock(spec=Update)
    update.effective_user = Mock(spec=User)
    update.effective_user.id = 123456789
    update.message = None

    # Should not raise an error
    await help_command(update, mock_context)


# Comprehensive tests for start


@pytest.mark.asyncio
async def test_start_command_sends_welcome(mock_update, mock_context):
    """Test that start command sends welcome message."""
    await start(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    welcome_text = call_args[0][0]

    # Verify key sections are present
    assert "Welcome" in welcome_text or "welcome" in welcome_text
    assert "CronWatchBot" in welcome_text
    assert "/add" in welcome_text
    assert "/help" in welcome_text
    assert "HTML" in str(call_args[1])


@pytest.mark.asyncio
async def test_start_command_with_no_message(mock_context):
    """Test start command when update has no message."""
    update = Mock(spec=Update)
    update.effective_user = Mock(spec=User)
    update.effective_user.id = 123456789
    update.message = None

    # Should not raise an error
    await start(update, mock_context)


# Comprehensive tests for unknown


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message_text",
    [
        "/unknowncommand",
        "/randomcmd",
        "/test123",
        "/",
    ],
)
async def test_unknown_handles_unknown_commands(mock_update, mock_context, message_text):
    """Test unknown handler for various unknown commands."""
    mock_update.message.text = message_text

    await unknown(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    response_text = mock_update.message.reply_text.call_args[0][0]
    assert "Unknown command" in response_text or "unknown" in response_text.lower()
    assert "/help" in response_text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message_text",
    [
        "Hello",
        "How are you?",
        "Random text",
        "123",
        "test message",
    ],
)
async def test_unknown_handles_non_command_messages(mock_update, mock_context, message_text):
    """Test unknown handler for non-command messages."""
    mock_update.message.text = message_text

    await unknown(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    response_text = mock_update.message.reply_text.call_args[0][0]
    assert "only respond to commands" in response_text or "commands" in response_text
    assert "/help" in response_text or "/start" in response_text


@pytest.mark.asyncio
async def test_unknown_with_no_message():
    """Test unknown handler when update has no message."""
    update = Mock(spec=Update)
    update.effective_user = Mock(spec=User)
    update.effective_user.id = 123456789
    update.message = None

    context = Mock()

    # Should not raise an error and should return early
    await unknown(update, context)


@pytest.mark.asyncio
async def test_unknown_with_no_text(mock_context):
    """Test unknown handler when message has no text."""
    update = Mock(spec=Update)
    update.effective_user = Mock(spec=User)
    update.effective_user.id = 123456789
    update.message = AsyncMock()
    update.message.text = None

    # Should not raise an error and should return early
    await unknown(update, mock_context)


@pytest.mark.asyncio
async def test_unknown_with_empty_text(mock_update, mock_context):
    """Test unknown handler with empty text."""
    mock_update.message.text = ""

    await unknown(mock_update, mock_context)

    # Empty string after strip() returns early
    # No reply is sent


@pytest.mark.asyncio
async def test_unknown_with_whitespace_only(mock_update, mock_context):
    """Test unknown handler with whitespace-only text."""
    mock_update.message.text = "   "

    await unknown(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_edited_message_sends_info_response(mock_context):
    """Test edited_message handler sends simple info response."""
    update = Mock(spec=Update)
    update.edited_message = AsyncMock()

    await edited_message(update, mock_context)

    update.edited_message.reply_text.assert_called_once_with("ℹ️ Message edits are not considered.")


@pytest.mark.asyncio
async def test_edited_message_with_no_edited_message(mock_context):
    """Test edited_message handler when there's no edited message."""
    update = Mock(spec=Update)
    update.edited_message = None

    await edited_message(update, mock_context)
