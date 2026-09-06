"""User settings schemas."""

from pydantic import BaseModel
from datetime import datetime


class UpdateSettingsRequest(BaseModel):
    telegram_chat_id: str | None = None
    polling_interval: int | None = None  # 5, 15, 30, 60
    alert_sensitivity: str | None = None  # high, medium, low


class WatchedAsset(BaseModel):
    id: str | None = None
    user_id: str | None = None
    asset_symbol: str  # e.g. "XAU/USD"
    asset_name: str  # e.g. "Gold / US Dollar"
    is_active: bool = True
    created_at: datetime | None = None


class AddAssetRequest(BaseModel):
    asset_symbol: str
    asset_name: str


class TelegramVerifyResponse(BaseModel):
    success: bool
    message: str
