"""Tests for urlwatch helper functions."""

from pathlib import Path
from unittest.mock import patch

import pytest

from helpers.urlwatch_helpers import (
    MAX_FILE_SIZE,
    format_url_summary,
    get_display_name,
    load_urls,
    save_urls,
    validate_index,
    validate_url,
)


def test_load_urls_file_not_exists(tmp_path):
    """Test loading URLs when file doesn't exist."""
    non_existent = tmp_path / "does_not_exist.yaml"

    with patch("helpers.urlwatch_helpers.URLS_FILE", str(non_existent)):
        result = load_urls()

    assert result == []


def test_load_urls_success(tmp_path):
    """Test successful URL loading."""
    urls_file = tmp_path / "urls.yaml"
    urls_file.write_text("url: https://example.com\nname: Example")

    with patch("helpers.urlwatch_helpers.URLS_FILE", str(urls_file)):
        result = load_urls()

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["url"] == "https://example.com"


@patch("helpers.urlwatch_helpers.logger")
def test_load_urls_file_too_large(mock_logger, tmp_path):
    """Test that files exceeding MAX_FILE_SIZE are rejected."""
    urls_file = tmp_path / "urls.yaml"
    urls_file.write_text("x" * 100)  # Create small file

    with (
        patch("helpers.urlwatch_helpers.URLS_FILE", str(urls_file)),
        patch.object(Path, "stat") as mock_stat,
    ):
        mock_stat.return_value.st_size = MAX_FILE_SIZE + 1
        result = load_urls()

    assert result == []
    mock_logger.error.assert_called_once()


@patch("helpers.urlwatch_helpers.logger")
def test_load_urls_yaml_error(mock_logger, tmp_path):
    """Test error handling when YAML parsing fails."""
    urls_file = tmp_path / "urls.yaml"
    urls_file.write_text("invalid: yaml: content: [")

    with patch("helpers.urlwatch_helpers.URLS_FILE", str(urls_file)):
        result = load_urls()

    assert result == []
    mock_logger.error.assert_called_once()


@patch("helpers.urlwatch_helpers.logger")
def test_load_urls_read_error(mock_logger, tmp_path):
    """Test error handling when file read fails."""
    urls_file = tmp_path / "urls.yaml"
    urls_file.write_text("test")

    with (
        patch("helpers.urlwatch_helpers.URLS_FILE", str(urls_file)),
        patch.object(Path, "open", side_effect=OSError("Permission denied")),
    ):
        result = load_urls()

    assert result == []
    mock_logger.error.assert_called_once()


def test_save_urls_success(tmp_path):
    """Test successful URL saving."""
    urls_file = tmp_path / "urls.yaml"

    with patch("helpers.urlwatch_helpers.URLS_FILE", str(urls_file)):
        urls = [{"url": "https://example.com", "name": "Example"}]
        result = save_urls(urls)

    assert result is True
    assert urls_file.exists()
    content = urls_file.read_text()
    assert "https://example.com" in content


@patch("helpers.urlwatch_helpers.logger")
def test_save_urls_makedirs_error(mock_logger, tmp_path):
    """Test error handling when directory creation fails."""
    urls_file = tmp_path / "subdir" / "urls.yaml"

    with (
        patch("helpers.urlwatch_helpers.URLS_FILE", str(urls_file)),
        patch.object(Path, "mkdir", side_effect=OSError("Permission denied")),
    ):
        urls = [{"url": "https://example.com"}]
        result = save_urls(urls)

    assert result is False
    mock_logger.error.assert_called_once()


@patch("helpers.urlwatch_helpers.shutil.move", side_effect=OSError("Move failed"))
@patch("helpers.urlwatch_helpers.logger")
def test_save_urls_move_error(mock_logger, mock_move, tmp_path):
    """Test error handling when file move fails."""
    urls_file = tmp_path / "urls.yaml"

    with patch("helpers.urlwatch_helpers.URLS_FILE", str(urls_file)):
        urls = [{"url": "https://example.com"}]
        result = save_urls(urls)

    assert result is False
    mock_logger.error.assert_called_once()


@pytest.mark.parametrize(
    "valid_url",
    [
        "http://example.com",
        "http://example.com/path",
        "http://example.com:8080",
        "https://example.com",
        "https://example.com/path?query=1",
        "https://subdomain.example.com",
    ],
)
def test_validate_url_valid(valid_url):
    """Test validation of valid URLs."""
    assert validate_url(valid_url) is True


@pytest.mark.parametrize(
    "invalid_url",
    [
        "ftp://example.com",
        "file:///path/to/file",
        "javascript:alert(1)",
        "example.com",
        "www.example.com",
        "http://",
        "https://",
        "",
        None,
        123,
    ],
    ids=[
        "ftp_scheme",
        "file_scheme",
        "javascript_scheme",
        "no_scheme",
        "no_scheme_www",
        "no_netloc_http",
        "no_netloc_https",
        "empty",
        "none",
        "integer",
    ],
)
def test_validate_url_invalid(invalid_url):
    """Test validation of invalid URLs."""
    assert validate_url(invalid_url) is False


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        ({"name": "My Site", "url": "https://example.com"}, "My Site"),
        ({"url": "https://example.com"}, "https://example.com"),
        ({}, "Unknown"),
        (
            {"name": "", "url": "https://example.com"},
            "https://example.com",
        ),  # Fixed: empty name falls back to URL
        (
            {"name": None, "url": "https://example.com"},
            "https://example.com",
        ),  # Added: None name falls back to URL
    ],
    ids=["with_name", "without_name", "no_fields", "empty_name", "none_name"],
)
def test_get_display_name(entry, expected):
    """Test display name extraction from URL entries."""
    assert get_display_name(entry) == expected


def test_format_url_summary_basic():
    """Test basic URL summary formatting."""
    entry = {"name": "Example", "url": "https://example.com"}
    result = format_url_summary(entry, 1)

    assert "📌 *Example*" in result
    assert "🔗 `https://example.com`" in result


def test_format_url_summary_with_filters():
    """Test summary formatting with multiple filters."""
    entry = {
        "name": "Example",
        "url": "https://example.com",
        "filter": ["css:div.content", "html2text"],
    }
    result = format_url_summary(entry, 1)

    assert "🔎" in result
    assert "css:div.content" in result
    assert "html2text" in result


def test_format_url_summary_with_single_filter():
    """Test summary formatting with a single filter."""
    entry = {"name": "Example", "url": "https://example.com", "filter": "html2text"}
    result = format_url_summary(entry, 1)

    assert "🔎" in result
    assert "html2text" in result


def test_format_url_summary_with_properties():
    """Test summary formatting with additional properties."""
    entry = {
        "name": "Example",
        "url": "https://example.com",
        "timeout": 30,
        "user_agent": "CustomBot",
    }
    result = format_url_summary(entry, 1)

    assert "⚙️" in result
    assert "timeout: 30" in result or "user_agent: CustomBot" in result


def test_format_url_summary_no_name():
    """Test summary formatting when entry has no name."""
    entry = {"url": "https://example.com"}
    result = format_url_summary(entry, 1)

    assert "https://example.com" in result


def test_validate_index_valid():
    """Test validation of valid indices."""
    urls = [{"url": "https://example1.com"}, {"url": "https://example2.com"}]

    assert validate_index("1", urls) == 0
    assert validate_index("2", urls) == 1


@pytest.mark.parametrize(
    ("idx_str", "urls"),
    [
        ("0", [{"url": "https://example1.com"}]),
        ("2", [{"url": "https://example1.com"}]),
        ("99", [{"url": "https://example1.com"}]),
        ("abc", [{"url": "https://example1.com"}]),
        ("1.5", [{"url": "https://example1.com"}]),
        ("", [{"url": "https://example1.com"}]),
        ("-1", [{"url": "https://example1.com"}]),
        ("1", []),
    ],
    ids=[
        "zero",
        "out_of_range",
        "way_out_of_range",
        "non_numeric",
        "float",
        "empty",
        "negative",
        "empty_list",
    ],
)
def test_validate_index_invalid(idx_str, urls):
    """Test validation of invalid indices."""
    assert validate_index(idx_str, urls) is None
