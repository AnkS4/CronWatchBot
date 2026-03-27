"""Integration tests for URL management workflow."""

from unittest.mock import patch

import pytest

from handlers.urlwatch_manage import add_url, delete_url, edit_url, view_urls
from helpers.urlwatch_helpers import load_urls


@pytest.fixture
def temp_urls_file(tmp_path, monkeypatch):
    """Create a temporary URLs file for testing."""
    urls_file = tmp_path / "urls.yaml"
    monkeypatch.setattr("helpers.urlwatch_helpers.URLS_FILE", str(urls_file))
    return urls_file


@pytest.mark.asyncio
async def test_add_list_delete_url_workflow(mock_update, mock_context, temp_urls_file):
    """Test complete workflow: add URL -> list URLs -> delete URL."""
    # Step 1: Add a URL
    mock_context.args = ["https://example.com", "Example", "Site"]
    await add_url(mock_update, mock_context)

    # Verify URL was added
    urls = load_urls()
    assert len(urls) == 1
    assert urls[0]["url"] == "https://example.com"
    assert urls[0]["name"] == "Example Site"

    # Step 2: List URLs
    mock_context.args = []
    await view_urls(mock_update, mock_context)

    # Verify list was called
    assert mock_update.message.reply_text.call_count >= 2

    # Step 3: Delete the URL
    mock_context.args = ["1"]
    with patch(
        "handlers.urlwatch_manage.update_crontab_indices_after_deletion"
    ) as mock_update_cron:
        mock_update_cron.return_value = (False, [])
        await delete_url(mock_update, mock_context)

    # Verify URL was deleted
    urls = load_urls()
    assert len(urls) == 0


@pytest.mark.asyncio
async def test_add_edit_url_workflow(mock_update, mock_context, temp_urls_file):
    """Test workflow: add URL -> edit URL."""
    # Step 1: Add a URL
    mock_context.args = ["https://example.com", "Example"]
    await add_url(mock_update, mock_context)

    urls = load_urls()
    assert len(urls) == 1
    assert urls[0]["name"] == "Example"

    # Step 2: Edit the URL
    mock_context.args = ["1", "https://newexample.com", "New", "Example"]
    await edit_url(mock_update, mock_context)

    # Verify URL was edited
    urls = load_urls()
    assert len(urls) == 1
    assert urls[0]["url"] == "https://newexample.com"
    assert urls[0]["name"] == "New Example"


@pytest.mark.asyncio
async def test_multiple_urls_workflow(mock_update, mock_context, temp_urls_file):
    """Test workflow with multiple URLs."""
    # Add multiple URLs
    urls_to_add = [
        ("https://site1.com", "Site 1"),
        ("https://site2.com", "Site 2"),
        ("https://site3.com", "Site 3"),
    ]

    for url, name in urls_to_add:
        mock_context.args = [url, name]
        await add_url(mock_update, mock_context)

    # Verify all URLs were added
    urls = load_urls()
    assert len(urls) == 3

    # Delete middle URL
    mock_context.args = ["2"]
    with patch(
        "handlers.urlwatch_manage.update_crontab_indices_after_deletion"
    ) as mock_update_cron:
        mock_update_cron.return_value = (True, [1])
        await delete_url(mock_update, mock_context)

    # Verify correct URL was deleted
    urls = load_urls()
    assert len(urls) == 2
    assert urls[0]["name"] == "Site 1"
    assert urls[1]["name"] == "Site 3"


@pytest.mark.asyncio
async def test_duplicate_url_prevention(mock_update, mock_context, temp_urls_file):
    """Test that duplicate URLs are prevented."""
    # Add first URL
    mock_context.args = ["https://example.com", "Example"]
    await add_url(mock_update, mock_context)

    # Try to add duplicate
    mock_context.args = ["https://example.com", "Duplicate"]
    await add_url(mock_update, mock_context)

    # Verify only one URL exists
    urls = load_urls()
    assert len(urls) == 1

    # Verify error message was sent
    calls = [str(call) for call in mock_update.message.reply_text.call_args_list]
    assert any("already exists" in str(call) for call in calls)


@pytest.mark.asyncio
async def test_url_validation_workflow(mock_update, mock_context, temp_urls_file):
    """Test URL validation during add operation."""
    # Add a valid URL with http scheme
    mock_context.args = ["http://example.com", "Valid"]
    await add_url(mock_update, mock_context)

    # Verify URL was added
    urls = load_urls()
    assert len(urls) == 1
    assert urls[0]["url"] == "http://example.com"

    # Add another valid URL with https scheme
    mock_context.args = ["https://secure.example.com", "Secure"]
    await add_url(mock_update, mock_context)

    # Verify second URL was added
    urls = load_urls()
    assert len(urls) == 2
    assert urls[1]["url"] == "https://secure.example.com"
