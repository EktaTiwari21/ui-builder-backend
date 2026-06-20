import logging
from fastapi import APIRouter, HTTPException, status
from app.db.supabase import get_supabase_client, get_supabase_auth_client
from app.models.requests import RefreshRequest
from supabase_auth.errors import AuthApiError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/refresh")
async def refresh_session(body: RefreshRequest):
    """Exchange a valid Supabase refresh token for a new access token.

    This endpoint is intentionally unauthenticated — it is the recovery path
    when the client's JWT has expired.  The frontend should call this whenever
    it receives a 401 with ``code=TOKEN_EXPIRED``.

    Args:
        body: ``RefreshRequest`` containing the ``refresh_token`` string.

    Returns:
        dict: ``access_token``, ``refresh_token``, ``expires_in``, ``token_type``.

    Raises:
        HTTPException 401 with ``code=REFRESH_FAILED`` — token invalid or already used.
        HTTPException 500 with ``code=INTERNAL_REFRESH_ERROR`` — unexpected server error.
    """
    try:
        client = await get_supabase_auth_client()
        response = await client.auth.refresh_session(body.refresh_token)

        if not response or not response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "REFRESH_FAILED",
                    "message": "Refresh token is invalid or has expired. Please log in again.",
                },
            )

        session = response.session
        logger.info("Session refreshed successfully for user %s", response.user.id if response.user else "unknown")

        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "expires_in": session.expires_in,
            "token_type": "bearer",
        }

    except HTTPException:
        raise  # Re-raise structured exceptions unchanged

    except AuthApiError as ae:
        logger.warning(f"Supabase AuthApiError during token refresh: {ae}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "REFRESH_FAILED",
                "message": "Refresh token is invalid or has already been used. Please log in again.",
            },
        )

    except Exception as e:
        logger.exception("Unexpected error during session refresh")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "INTERNAL_REFRESH_ERROR",
                "message": "An unexpected error occurred during session refresh.",
            },
        )
