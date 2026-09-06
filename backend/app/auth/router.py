"""Auth API routes — register, login, logout, me."""

import logging

from fastapi import APIRouter, HTTPException, Depends, status

from app.database import get_supabase_client, get_supabase_anon_client
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
    admin_supabase = get_supabase_client()
    anon_supabase = get_supabase_anon_client()

    try:
        # Create user via Supabase Admin API (auto-confirms email and avoids session leakage)
        user_response = admin_supabase.auth.admin.create_user(
            {
                "email": payload.email,
                "password": payload.password,
                "email_confirm": True,
            }
        )

        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed. Please check your credentials.",
            )

        user_id = user_response.user.id

        # Create or update profile row using admin privileges (bypasses RLS)
        admin_supabase.table("profiles").upsert(
            {
                "id": user_id,
                "polling_interval": 15,
                "alert_sensitivity": "medium",
                "telegram_verified": False,
            }
        ).execute()

        # Sign in with the anon client to acquire an active access token
        auth_response = anon_supabase.auth.sign_in_with_password(
            {"email": payload.email, "password": payload.password}
        )

        logger.info(f"New user registered and authenticated: {payload.email}")

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
        error_msg = str(e)
        logger.error(f"Registration error: {error_msg}")
        if "already registered" in error_msg.lower() or "already exists" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already registered. Please log in.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest):
    """Authenticate a user and return an access token."""
    anon_supabase = get_supabase_anon_client()
    admin_supabase = get_supabase_client()

    try:
        auth_response = anon_supabase.auth.sign_in_with_password(
            {"email": payload.email, "password": payload.password}
        )

        if not auth_response.user or not auth_response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        user_id = auth_response.user.id

        # Fetch profile using admin client
        profile_resp = (
            admin_supabase.table("profiles")
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
