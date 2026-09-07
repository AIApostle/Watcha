"""Dashboard response schemas."""

from pydantic import BaseModel
from datetime import datetime


class PriceResponse(BaseModel):
    symbol: str
    current_price: float
    open_price: float | None = None
    high_price: float | None = None
    low_price: float | None = None
    previous_close: float | None = None
    change: float | None = None
    change_percent: float | None = None
    timestamp: datetime | None = None


class AlertResponse(BaseModel):
    id: str
    user_id: str
    asset_symbol: str | None = None
    alert_type: str
    severity: str
    title: str
    body: str | None = None
    ai_analysis: str | None = None
    impact_score: int | None = None
    sentiment: str | None = None
    telegram_sent: bool = False
    created_at: datetime | None = None


class NewsItemResponse(BaseModel):
    id: str
    source: str
    source_type: str
    title: str
    url: str | None = None
    summary: str | None = None
    sentiment_score: float | None = None
    published_at: datetime | None = None
    fetched_at: datetime | None = None


class DashboardResponse(BaseModel):
    prices: list[PriceResponse]
    recent_alerts: list[AlertResponse]
    market_mood: str | None = None
    mood_summary: str | None = None
    agent_running: bool = False
    total_alerts_today: int = 0
    watched_assets_count: int = 0
