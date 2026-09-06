"""Auth dependency — extract and validate the current user from Supabase JWT."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.database import get_supabase_client
from app.auth.schemas import UserProfile

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserProfile:
    """
    FastAPI dependency that validates the Supabase access token
    and returns the authenticated user's profile.
    """
    token = credentials.credentials
    supabase = get_supabase_client()

    try:
        # Verify token with Supabase Auth
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        user_id = user_response.user.id
        email = user_response.user.email

        # Fetch profile from our profiles table
        profile_resp = (
            supabase.table("profiles")
            .select("*")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )

        if profile_resp.data:
            return UserProfile(
                id=user_id,
                email=email,
                telegram_chat_id=profile_resp.data.get("telegram_chat_id"),
                telegram_verified=profile_resp.data.get("telegram_verified", False),
                polling_interval=profile_resp.data.get("polling_interval", 15),
                alert_sensitivity=profile_resp.data.get("alert_sensitivity", "medium"),
                created_at=profile_resp.data.get("created_at"),
            )

        # Profile doesn't exist yet — return basic info
        return UserProfile(id=user_id, email=email)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        )
