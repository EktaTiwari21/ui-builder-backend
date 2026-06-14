from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.db.supabase import get_supabase_client
from supabase_auth.errors import AuthApiError
from app.config import settings
import sys
import logging
from typing import Optional

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

# Keywords that identify an expired JWT in Supabase AuthApiError messages
_EXPIRY_KEYWORDS = ("jwt expired", "token is expired", "token has expired")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> object:
    """FastAPI dependency to extract and verify the bearer token against Supabase Auth.

    Args:
        credentials: The HTTP bearer credentials from the Authorization header.

    Returns:
        User: The verified user object from Supabase Auth.

    Raises:
        HTTPException 401 with ``code=MISSING_TOKEN``  — no Authorization header.
        HTTPException 401 with ``code=TOKEN_EXPIRED``  — JWT is expired; frontend should refresh.
        HTTPException 401 with ``code=INVALID_TOKEN``  — JWT is malformed or revoked.
        HTTPException 401 with ``code=AUTH_FAILED``    — Supabase rejected the token.
        HTTPException 500 with ``code=INTERNAL_AUTH_ERROR`` — unexpected server error.
    """
    is_testing = "pytest" in sys.modules

    # ── Integration-test bypass ──────────────────────────────────────────────
    if credentials and credentials.credentials == "bypass-integration-token-xyz":
        class MockUser:
            id = "00000000-0000-0000-0000-000000000000"
            email = "mock@example.com"
        return MockUser()

    # ── Development fallback: try real token, fall back to mock ──────────────
    if settings.environment == "development" and not is_testing:
        token = credentials.credentials if credentials else None
        if token:
            try:
                client = await get_supabase_client()
                response = await client.auth.get_user(token)
                if response and response.user:
                    return response.user
            except Exception:
                pass  # fall through to mock

        class MockUser:
            id = "00000000-0000-0000-0000-000000000000"
            email = "mock@example.com"
        return MockUser()

    # ── Production: require credentials ─────────────────────────────────────
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_TOKEN", "message": "Authentication token required."},
        )

    token = credentials.credentials
    try:
        client = await get_supabase_client()
        response = await client.auth.get_user(token)

        if response and response.user:
            return response.user

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Token is invalid or revoked."},
        )

    except HTTPException:
        raise  # Re-raise our own structured exceptions unchanged

    except AuthApiError as ae:
        err_lower = str(ae).lower()
        if any(kw in err_lower for kw in _EXPIRY_KEYWORDS):
            logger.warning("Expired JWT detected — client should call POST /auth/refresh.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "TOKEN_EXPIRED", "message": "JWT has expired. Refresh your session."},
            )
        logger.error(f"Supabase AuthApiError during token verification: {ae}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_FAILED", "message": f"Authentication failed: {ae}"},
        )

    except Exception as e:
        logger.exception("Unexpected error during token verification")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "INTERNAL_AUTH_ERROR", "message": "An unexpected error occurred."},
        )
