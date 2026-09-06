"""Auth request/response schemas."""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


# ── Requests ─────────────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ── Responses ────────────────────────────────────────────────────────────────


class UserProfile(BaseModel):
    id: str
    email: str
    telegram_chat_id: str | None = None
    telegram_verified: bool = False
    polling_interval: int = 15  # minutes
    alert_sensitivity: str = "medium"  # high | medium | low
    created_at: datetime | None = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfile


class MessageResponse(BaseModel):
    message: str
