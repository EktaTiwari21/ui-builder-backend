from unittest.mock import MagicMock, AsyncMock, patch
import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from app.middleware.auth import get_current_user
from app.middleware.rate_limit import check_rate_limit
from supabase_auth.errors import AuthApiError

@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = "user-uuid-12345"
    user.email = "test@example.com"
    return user

@pytest.fixture
def mock_credentials():
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid-token-xyz")

# ----------------- Auth Dependency Tests -----------------

@pytest.mark.asyncio
@patch("app.middleware.auth.get_supabase_client")
async def test_get_current_user_success(mock_get_db, mock_credentials, mock_user):
    """Test get_current_user succeeds when token is verified successfully by Supabase Auth."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.user = mock_user
    mock_client.auth.get_user = AsyncMock(return_value=mock_response)
    mock_get_db.return_value = mock_client

    user = await get_current_user(mock_credentials)
    assert user == mock_user
    mock_client.auth.get_user.assert_called_once_with("valid-token-xyz")

@pytest.mark.asyncio
@patch("app.middleware.auth.get_supabase_client")
async def test_get_current_user_invalid_token(mock_get_db, mock_credentials):
    """Test get_current_user raises 401 when token is invalid or expired."""
    mock_client = MagicMock()
    mock_client.auth.get_user = AsyncMock(return_value=None)
    mock_get_db.return_value = mock_client

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(mock_credentials)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid authentication token" in exc_info.value.detail

@pytest.mark.asyncio
@patch("app.middleware.auth.get_supabase_client")
async def test_get_current_user_api_error(mock_get_db, mock_credentials):
    """Test get_current_user raises 401 when Supabase Auth raises an API error."""
    mock_client = MagicMock()
    # Mocking AuthApiError instantiation
    error_mock = AuthApiError("Token expired", 401, "invalid_credentials")
    mock_client.auth.get_user = AsyncMock(side_effect=error_mock)
    mock_get_db.return_value = mock_client

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(mock_credentials)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Authentication failed" in exc_info.value.detail

# ----------------- Rate Limit Dependency Tests -----------------

@pytest.mark.asyncio
@patch("app.middleware.rate_limit.get_supabase_client")
async def test_rate_limit_free_user_success(mock_get_db, mock_user):
    """Test that a free user with less than 10 generations today is permitted."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [{"subscription_plan": "free", "generations_today": 5}]
    mock_client.table.return_value.select.return_value.eq.return_value.execute = AsyncMock(return_value=mock_response)
    mock_get_db.return_value = mock_client

    result = await check_rate_limit(mock_user)
    assert result == mock_user

@pytest.mark.asyncio
@patch("app.middleware.rate_limit.get_supabase_client")
async def test_rate_limit_free_user_exceeded(mock_get_db, mock_user):
    """Test that a free user with 10 daily generations is blocked (429)."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [{"subscription_plan": "free", "generations_today": 10}]
    mock_client.table.return_value.select.return_value.eq.return_value.execute = AsyncMock(return_value=mock_response)
    mock_get_db.return_value = mock_client

    with pytest.raises(HTTPException) as exc_info:
        await check_rate_limit(mock_user)
    assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert "Daily generation limit reached" in exc_info.value.detail

@pytest.mark.asyncio
@patch("app.middleware.rate_limit.get_supabase_client")
async def test_rate_limit_premium_user_success(mock_get_db, mock_user):
    """Test that a premium user with less than 100 generations today is permitted."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [{"subscription_plan": "premium", "generations_today": 99}]
    mock_client.table.return_value.select.return_value.eq.return_value.execute = AsyncMock(return_value=mock_response)
    mock_get_db.return_value = mock_client

    result = await check_rate_limit(mock_user)
    assert result == mock_user

@pytest.mark.asyncio
@patch("app.middleware.rate_limit.get_supabase_client")
async def test_rate_limit_premium_user_exceeded(mock_get_db, mock_user):
    """Test that a premium user with 100 daily generations is blocked (429)."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [{"subscription_plan": "premium", "generations_today": 100}]
    mock_client.table.return_value.select.return_value.eq.return_value.execute = AsyncMock(return_value=mock_response)
    mock_get_db.return_value = mock_client

    with pytest.raises(HTTPException) as exc_info:
        await check_rate_limit(mock_user)
    assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert "Daily generation limit reached" in exc_info.value.detail
