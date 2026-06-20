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
@patch("app.middleware.auth.get_supabase_auth_client")
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
@patch("app.middleware.auth.get_supabase_auth_client")
async def test_get_current_user_invalid_token(mock_get_db, mock_credentials):
    """Test get_current_user raises 401 when token is invalid or expired."""
    mock_client = MagicMock()
    mock_client.auth.get_user = AsyncMock(return_value=None)
    mock_get_db.return_value = mock_client

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(mock_credentials)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail["code"] == "INVALID_TOKEN"

@pytest.mark.asyncio
@patch("app.middleware.auth.get_supabase_auth_client")
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
    assert exc_info.value.detail["code"] == "AUTH_FAILED"

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

@pytest.mark.asyncio
@patch("app.middleware.rate_limit.get_supabase_client")
async def test_check_rate_limit_creates_profile_if_missing(mock_get_db, mock_user):
    """Test rate limit passes if profile is missing (falls back to free/0)."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [] # empty data simulating missing profile row
    mock_client.table.return_value.select.return_value.eq.return_value.execute = AsyncMock(return_value=mock_response)
    mock_get_db.return_value = mock_client

    result = await check_rate_limit(mock_user)
    assert result == mock_user


# ─────────────────── TOKEN_EXPIRED structured error tests ───────────────────

@pytest.mark.asyncio
@patch("app.middleware.auth.get_supabase_auth_client")
async def test_get_current_user_expired_jwt_keyword(mock_get_db, mock_credentials):
    """Test 'JWT expired' in AuthApiError message → 401 with code=TOKEN_EXPIRED."""
    mock_client = MagicMock()
    mock_client.auth.get_user = AsyncMock(
        side_effect=AuthApiError("JWT expired", 401, "invalid_credentials")
    )
    mock_get_db.return_value = mock_client

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(mock_credentials)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail["code"] == "TOKEN_EXPIRED"


@pytest.mark.asyncio
@patch("app.middleware.auth.get_supabase_auth_client")
async def test_get_current_user_token_is_expired_keyword(mock_get_db, mock_credentials):
    """Test 'token is expired' variant in AuthApiError → 401 with code=TOKEN_EXPIRED."""
    mock_client = MagicMock()
    mock_client.auth.get_user = AsyncMock(
        side_effect=AuthApiError("invalid JWT: token is expired", 401, "invalid_credentials")
    )
    mock_get_db.return_value = mock_client

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(mock_credentials)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail["code"] == "TOKEN_EXPIRED"


# ─────────────────── /auth/refresh endpoint tests ───────────────────────────

@pytest.mark.asyncio
@patch("app.api.auth.get_supabase_auth_client")
async def test_refresh_session_success(mock_get_db):
    """Test POST /auth/refresh with valid refresh token returns new token pair."""
    from app.api.auth import refresh_session
    from app.models.requests import RefreshRequest

    mock_session = MagicMock()
    mock_session.access_token = "new-access-token-abc"
    mock_session.refresh_token = "new-refresh-token-xyz"
    mock_session.expires_in = 3600

    mock_user = MagicMock()
    mock_user.id = "user-uuid-12345"

    mock_response = MagicMock()
    mock_response.session = mock_session
    mock_response.user = mock_user

    mock_client = MagicMock()
    mock_client.auth.refresh_session = AsyncMock(return_value=mock_response)
    mock_get_db.return_value = mock_client

    result = await refresh_session(RefreshRequest(refresh_token="valid-refresh-token"))

    assert result["access_token"] == "new-access-token-abc"
    assert result["refresh_token"] == "new-refresh-token-xyz"
    assert result["expires_in"] == 3600
    assert result["token_type"] == "bearer"


@pytest.mark.asyncio
@patch("app.api.auth.get_supabase_auth_client")
async def test_refresh_session_invalid_token(mock_get_db):
    """Test POST /auth/refresh with invalid refresh token → 401 REFRESH_FAILED."""
    from app.api.auth import refresh_session
    from app.models.requests import RefreshRequest

    mock_client = MagicMock()
    mock_client.auth.refresh_session = AsyncMock(
        side_effect=AuthApiError("Invalid Refresh Token", 401, "invalid_grant")
    )
    mock_get_db.return_value = mock_client

    with pytest.raises(HTTPException) as exc_info:
        await refresh_session(RefreshRequest(refresh_token="bad-refresh-token"))

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail["code"] == "REFRESH_FAILED"
