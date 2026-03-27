"""Utility functions for escaping text in Telegram messages."""

import html


def escape_html(text: str) -> str:
    """Escape text for use in Telegram HTML parse mode.

    Args:
        text: The text to escape.

    Returns:
        HTML-escaped text safe for Telegram messages.
    """
    return html.escape(str(text))


def format_code(text: str) -> str:
    """Format text as inline code in HTML.

    Args:
        text: The text to format as code.

    Returns:
        HTML-formatted code text.
    """
    return f"<code>{escape_html(text)}</code>"


def format_bold(text: str) -> str:
    """Format text as bold in HTML.

    Args:
        text: The text to format as bold.

    Returns:
        HTML-formatted bold text.
    """
    return f"<b>{escape_html(text)}</b>"


def format_pre(text: str) -> str:
    """Format text as preformatted block in HTML.

    Args:
        text: The text to format as preformatted.

    Returns:
        HTML-formatted preformatted text.
    """
    return f"<pre>{escape_html(text)}</pre>"
