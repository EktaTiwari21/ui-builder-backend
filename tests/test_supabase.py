import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.db.supabase import ensure_profile_exists

@pytest.mark.asyncio
@patch("app.db.supabase.get_supabase_client")
async def test_ensure_profile_exists_creates_new_row(mock_get_client):
    """Test ensure_profile_exists calls upsert and returns the new row."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    
    # Simulate upsert returning the new row
    expected_profile = {
        "id": "user-uuid-123",
        "subscription_plan": "free",
        "generations_today": 0
    }
    mock_response.data = [expected_profile]
    
    mock_client.table.return_value.upsert.return_value.execute = AsyncMock(return_value=mock_response)
    mock_get_client.return_value = mock_client

    result = await ensure_profile_exists("user-uuid-123")
    
    assert result == expected_profile
    # Verify upsert was called with ignore_duplicates=True and correct payload
    mock_client.table.return_value.upsert.assert_called_once_with(
        expected_profile, 
        on_conflict="id", 
        ignore_duplicates=True
    )

@pytest.mark.asyncio
@patch("app.db.supabase.get_supabase_client")
async def test_ensure_profile_exists_idempotent(mock_get_client):
    """Test ensure_profile_exists handles the case where the row already exists (upsert still returns data or empty but doesn't crash)."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    
    # If ignore_duplicates=True and it exists, Supabase might return empty data depending on the exact PostgREST behavior
    mock_response.data = []
    mock_client.table.return_value.upsert.return_value.execute = AsyncMock(return_value=mock_response)
    mock_get_client.return_value = mock_client

    result = await ensure_profile_exists("user-uuid-456")
    
    assert result is None
    mock_client.table.return_value.upsert.assert_called_once()

@pytest.mark.asyncio
@patch("app.db.supabase.get_supabase_client")
async def test_ensure_profile_exists_exception(mock_get_client):
    """Test ensure_profile_exists handles exceptions gracefully returning None."""
    mock_client = MagicMock()
    mock_client.table.return_value.upsert.return_value.execute = AsyncMock(side_effect=Exception("DB Error"))
    mock_get_client.return_value = mock_client

    result = await ensure_profile_exists("user-uuid-789")
    
    assert result is None
