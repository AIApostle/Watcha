"""Dashboard API routes — prices, alerts, news, aggregated dashboard."""

import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user
from app.auth.schemas import UserProfile
from app.database import get_supabase_client
from app.collectors.finnhub_client import FinnhubCollector
from app.agent.worker import agent_worker
from app.dashboard.schemas import (
    PriceResponse,
    AlertResponse,
    NewsItemResponse,
    DashboardResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()

_finnhub = FinnhubCollector()


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(user: UserProfile = Depends(get_current_user)):
    """Aggregated dashboard data — prices, recent alerts, agent status."""
    supabase = get_supabase_client()

    # Fetch user's watched assets
    assets_resp = (
        supabase.table("watched_assets")
        .select("asset_symbol")
        .eq("user_id", user.id)
        .eq("is_active", True)
        .execute()
    )
    asset_symbols = [a["asset_symbol"] for a in (assets_resp.data or [])]

    # Fetch prices
    prices = []
    for symbol in asset_symbols:
        price = await _finnhub.get_quote(symbol)
        if price:
            prices.append(
                PriceResponse(
                    symbol=price.symbol,
                    current_price=price.current_price,
                    open_price=price.open_price,
                    high_price=price.high_price,
                    low_price=price.low_price,
                    previous_close=price.previous_close,
                    change=price.change,
                    change_percent=price.change_percent,
                    timestamp=price.timestamp,
                )
            )

    # Recent alerts (last 5 critical/warning)
    alerts_resp = (
        supabase.table("alerts")
        .select("*")
        .eq("user_id", user.id)
        .in_("severity", ["critical", "warning"])
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )
    recent_alerts = [AlertResponse(**a) for a in (alerts_resp.data or [])]

    # Today's alert count
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    today_resp = (
        supabase.table("alerts")
        .select("id", count="exact")
        .eq("user_id", user.id)
        .gte("created_at", today_start.isoformat())
        .execute()
    )
    total_today = today_resp.count or 0

    return DashboardResponse(
        prices=prices,
        recent_alerts=recent_alerts,
        agent_running=agent_worker.is_running,
        total_alerts_today=total_today,
    )


@router.get("/prices/{symbol:path}", response_model=PriceResponse)
async def get_price(
    symbol: str,
    user: UserProfile = Depends(get_current_user),
):
    """Get current price for a specific symbol (e.g. XAU/USD)."""
    price = await _finnhub.get_quote(symbol)
    if not price:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No price data available for {symbol}",
        )

    return PriceResponse(
        symbol=price.symbol,
        current_price=price.current_price,
        open_price=price.open_price,
        high_price=price.high_price,
        low_price=price.low_price,
        previous_close=price.previous_close,
        change=price.change,
        change_percent=price.change_percent,
        timestamp=price.timestamp,
    )


@router.get("/alerts", response_model=list[AlertResponse])
async def list_alerts(
    user: UserProfile = Depends(get_current_user),
    severity: str | None = Query(default=None),
    asset: str | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Paginated alert history with optional filters."""
    supabase = get_supabase_client()

    query = (
        supabase.table("alerts")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
    )

    if severity:
        query = query.eq("severity", severity)
    if asset:
        query = query.ilike("asset_symbol", f"%{asset}%")

    resp = query.range(offset, offset + limit - 1).execute()
    return [AlertResponse(**a) for a in (resp.data or [])]


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    user: UserProfile = Depends(get_current_user),
):
    """Get a single alert by ID."""
    supabase = get_supabase_client()

    resp = (
        supabase.table("alerts")
        .select("*")
        .eq("id", alert_id)
        .eq("user_id", user.id)
        .maybe_single()
        .execute()
    )

    if not resp.data:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found.",
        )

    return AlertResponse(**resp.data)


@router.get("/news", response_model=list[NewsItemResponse])
async def list_news(
    user: UserProfile = Depends(get_current_user),
    source_type: str | None = Query(default=None),
    limit: int = Query(default=30, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Aggregated news feed from all sources."""
    supabase = get_supabase_client()

    query = (
        supabase.table("news_items")
        .select("*")
        .order("fetched_at", desc=True)
    )

    if source_type:
        query = query.eq("source_type", source_type)

    resp = query.range(offset, offset + limit - 1).execute()
    return [NewsItemResponse(**n) for n in (resp.data or [])]
