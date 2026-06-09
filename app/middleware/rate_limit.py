from fastapi import Depends, HTTPException, status
import logging
from app.middleware.auth import get_current_user
from app.db.supabase import get_supabase_client

logger = logging.getLogger(__name__)

async def check_rate_limit(user = Depends(get_current_user)):
    """FastAPI dependency to verify if user has not exceeded their daily generation limits.
    
    Free users: max 10 generations per day.
    Premium users: max 100 generations per day.
    
    Args:
        user: The authenticated user object from get_current_user.
        
    Returns:
        User: The verified user details object.
        
    Raises:
        HTTPException: 429 Too Many Requests if daily limits are reached.
    """
    client = await get_supabase_client()
    user_id = user.id

    try:
        # Fetch subscription plan and daily generations count
        response = await client.table("profiles").select("subscription_plan, generations_today").eq("id", user_id).execute()
        if response.data:
            profile = response.data[0]
            plan = profile.get("subscription_plan", "free")
            generations_today = profile.get("generations_today", 0)
        else:
            plan = "free"
            generations_today = 0
            
    except Exception as e:
        logger.error(f"Failed to query rate limit profile for user {user_id}: {e}")
        # Fallback to conservative free limits in case of DB read error
        plan = "free"
        generations_today = 0

    # Determine daily allowance limit
    limit = 100 if plan == "premium" else 10

    if generations_today >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily generation limit reached"
        )

    return user
