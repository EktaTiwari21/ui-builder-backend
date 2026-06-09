from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.db.supabase import get_supabase_client
from supabase_auth.errors import AuthApiError

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """FastAPI dependency to extract and verify the bearer token against Supabase Auth.
    
    Args:
        credentials: The HTTP bearer credentials.
        
    Returns:
        User: The verified user details object returned by Supabase Auth.
        
    Raises:
        HTTPException: 401 Unauthorized if verification fails or token is missing.
    """
    token = credentials.credentials
    try:
        client = await get_supabase_client()
        # Verify the session token directly with Supabase Auth server
        response = await client.auth.get_user(token)
        if response and response.user:
            return response.user
            
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token."
        )
    except AuthApiError as ae:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(ae)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )
