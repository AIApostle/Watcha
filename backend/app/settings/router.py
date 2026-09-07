"""User settings API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.auth.schemas import UserProfile, MessageResponse
from app.database import get_supabase_client
from app.settings.schemas import (
    UpdateSettingsRequest,
    WatchedAsset,
    AddAssetRequest,
    TelegramVerifyResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()

VALID_INTERVALS = {5, 15, 30, 60}
VALID_SENSITIVITIES = {"all", "high", "medium", "low"}


@router.get("", response_model=UserProfile)
async def get_settings(user: UserProfile = Depends(get_current_user)):
    """Return the current user's settings (same as /auth/me profile)."""
    return user


@router.put("", response_model=MessageResponse)
async def update_settings(
    payload: UpdateSettingsRequest,
    user: UserProfile = Depends(get_current_user),
):
    """Update the current user's settings."""
    supabase = get_supabase_client()
    updates = {}

    if payload.telegram_chat_id is not None:
        if payload.telegram_chat_id != user.telegram_chat_id:
            updates["telegram_chat_id"] = payload.telegram_chat_id
            updates["telegram_verified"] = False  # Reset verification only when chat ID changed
        else:
            updates["telegram_chat_id"] = payload.telegram_chat_id

    if payload.polling_interval is not None:
        if payload.polling_interval not in VALID_INTERVALS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid polling interval. Must be one of: {VALID_INTERVALS}",
            )
        updates["polling_interval"] = payload.polling_interval

    if payload.alert_sensitivity is not None:
        if payload.alert_sensitivity not in VALID_SENSITIVITIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sensitivity. Must be one of: {VALID_SENSITIVITIES}",
            )
        updates["alert_sensitivity"] = payload.alert_sensitivity

    if not updates:
        return MessageResponse(message="No changes provided.")

    try:
        supabase.table("profiles").update(updates).eq("id", user.id).execute()
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error updating settings: {error_msg}")
        if "profiles_alert_sensitivity_check" in error_msg and updates.get("alert_sensitivity") == "all":
            # If the database constraint hasn't been updated to allow 'all', fallback to 'high'
            # (which has the identical threshold of 1) so the save succeeds without crashing.
            logger.warning("Database rejected 'all' for alert_sensitivity. Falling back to 'high'.")
            updates["alert_sensitivity"] = "high"
            supabase.table("profiles").update(updates).eq("id", user.id).execute()
            return MessageResponse(message="Settings updated successfully.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update settings: {error_msg}",
        )

    return MessageResponse(message="Settings updated successfully.")


# ── Watched Assets ───────────────────────────────────────────────────────────


@router.get("/assets", response_model=list[WatchedAsset])
async def list_assets(user: UserProfile = Depends(get_current_user)):
    """List all watched assets, people, and organizations for the current user."""
    supabase = get_supabase_client()
    resp = (
        supabase.table("watched_assets")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", desc=False)
        .execute()
    )
    results = []
    for row in ((resp.data if resp else []) or []):
        sym = row.get("asset_symbol", "")
        if "entity_type" not in row or not row.get("entity_type"):
            if sym.startswith("PERSON:"):
                row["entity_type"] = "person"
            elif sym.startswith("ORG:"):
                row["entity_type"] = "organization"
            else:
                row["entity_type"] = "asset"
        results.append(WatchedAsset(**row))
    return results


@router.post("/assets", response_model=WatchedAsset, status_code=status.HTTP_201_CREATED)
async def add_asset(
    payload: AddAssetRequest,
    user: UserProfile = Depends(get_current_user),
):
    """Add a new watched asset, person, or organization."""
    supabase = get_supabase_client()

    symbol = payload.asset_symbol.strip()
    name = payload.asset_name.strip()
    entity_type = payload.entity_type or "asset"

    if entity_type == "person" and not symbol.startswith("PERSON:"):
        symbol = f"PERSON:{symbol}"
    elif entity_type == "organization" and not symbol.startswith("ORG:"):
        symbol = f"ORG:{symbol}"

    # Check for duplicate
    existing = (
        supabase.table("watched_assets")
        .select("id")
        .eq("user_id", user.id)
        .eq("asset_symbol", symbol)
        .maybe_single()
        .execute()
    )
    if existing and existing.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"'{name}' is already in your watchlist.",
        )

    resp = (
        supabase.table("watched_assets")
        .insert(
            {
                "user_id": user.id,
                "asset_symbol": symbol,
                "asset_name": name,
                "is_active": True,
            }
        )
        .execute()
    )

    data = resp.data[0]
    data["entity_type"] = entity_type
    return WatchedAsset(**data)


@router.delete("/assets/{asset_id}", response_model=MessageResponse)
async def remove_asset(
    asset_id: str,
    user: UserProfile = Depends(get_current_user),
):
    """Remove a watched asset."""
    supabase = get_supabase_client()

    # Verify ownership
    existing = (
        supabase.table("watched_assets")
        .select("id")
        .eq("id", asset_id)
        .eq("user_id", user.id)
        .maybe_single()
        .execute()
    )
    if not existing or not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found.",
        )

    supabase.table("watched_assets").delete().eq("id", asset_id).execute()
    return MessageResponse(message="Asset removed from watchlist.")


# ── Telegram Verification ────────────────────────────────────────────────────


@router.post("/telegram/verify", response_model=TelegramVerifyResponse)
async def verify_telegram(user: UserProfile = Depends(get_current_user)):
    """Send a test message to the user's configured Telegram chat ID."""
    if not user.telegram_chat_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Telegram chat ID configured. Update your settings first.",
        )

    try:
        from app.agent.dispatcher import send_test_message

        success = await send_test_message(user.telegram_chat_id)

        if success:
            # Mark as verified
            supabase = get_supabase_client()
            supabase.table("profiles").update(
                {"telegram_verified": True}
            ).eq("id", user.id).execute()

            return TelegramVerifyResponse(
                success=True,
                message="✅ Test message sent! Check your Telegram.",
            )
        else:
            return TelegramVerifyResponse(
                success=False,
                message="Failed to send test message. Please check your chat ID.",
            )

    except Exception as e:
        logger.error(f"Telegram verification error: {e}")
        return TelegramVerifyResponse(
            success=False,
            message=f"Error: {str(e)}",
        )
