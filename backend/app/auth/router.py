"""Auth API routes — register, login, logout, me."""

import logging

from fastapi import APIRouter, HTTPException, Depends, status

from app.database import get_supabase_client
from app.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    AuthResponse,
    UserProfile,
    MessageResponse,
)
from app.auth.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest):
    """Register a new user via Supabase Auth and create their profile."""
    supabase = get_supabase_client()

    try:
        # Create user in Supabase Auth
        auth_response = supabase.auth.sign_up(
            {"email": payload.email, "password": payload.password}
        )

        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed. Email may already be in use.",
            )

        user_id = auth_response.user.id

        # Create profile row
        supabase.table("profiles").insert(
            {
                "id": user_id,
                "polling_interval": 15,
                "alert_sensitivity": "medium",
                "telegram_verified": False,
            }
        ).execute()

        logger.info(f"New user registered: {payload.email}")

        return AuthResponse(
            access_token=auth_response.session.access_token if auth_response.session else "",
            user=UserProfile(
                id=user_id,
                email=payload.email,
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest):
    """Authenticate a user and return an access token."""
    supabase = get_supabase_client()

    try:
        auth_response = supabase.auth.sign_in_with_password(
            {"email": payload.email, "password": payload.password}
        )

        if not auth_response.user or not auth_response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        user_id = auth_response.user.id

        # Fetch profile
        profile_resp = (
            supabase.table("profiles")
            .select("*")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )

        profile_data = profile_resp.data or {}

        return AuthResponse(
            access_token=auth_response.session.access_token,
            user=UserProfile(
                id=user_id,
                email=payload.email,
                telegram_chat_id=profile_data.get("telegram_chat_id"),
                telegram_verified=profile_data.get("telegram_verified", False),
                polling_interval=profile_data.get("polling_interval", 15),
                alert_sensitivity=profile_data.get("alert_sensitivity", "medium"),
                created_at=profile_data.get("created_at"),
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )


@router.post("/logout", response_model=MessageResponse)
async def logout(user: UserProfile = Depends(get_current_user)):
    """Log out the current user (client should discard the token)."""
    return MessageResponse(message="Logged out successfully.")


@router.get("/me", response_model=UserProfile)
async def get_me(user: UserProfile = Depends(get_current_user)):
    """Return the current authenticated user's profile."""
    return user
