"""
Agent Worker — background market monitoring engine.

Uses APScheduler to run periodic scan cycles in-process with FastAPI.
Each cycle: collect data → AI analysis → dispatch alerts.
"""

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database import get_supabase_client
from app.collectors.finnhub_client import FinnhubCollector
from app.collectors.marketaux_client import MarketauxCollector
from app.collectors.rss_collector import RSSCollector
from app.collectors.social_monitor import SocialMonitor
from app.collectors.forexfactory_client import ForexFactoryCollector
from app.collectors.truthsocial_scraper import TruthSocialScraper
from app.collectors.x_scraper import XScraper
from app.agent.analyzer import analyze_market_data
from app.agent.dispatcher import send_alert

logger = logging.getLogger(__name__)

# Severity thresholds per sensitivity level
SENSITIVITY_THRESHOLDS = {
    "all": 1,      # Send all alerts (low, medium, and high)
    "high": 1,     # Send all alerts
    "medium": 4,   # Send impact >= 4
    "low": 7,      # Send only critical (impact >= 7)
}


class AgentWorker:
    """Background worker that monitors markets and sends alerts."""

    def __init__(self):
        self._scheduler = AsyncIOScheduler()
        self._finnhub = FinnhubCollector()
        self._marketaux = MarketauxCollector()
        self._rss = RSSCollector()
        self._social = SocialMonitor()
        self._forexfactory = ForexFactoryCollector()
        self._truthsocial = TruthSocialScraper()
        self._x = XScraper()
        self._is_running = False
        self._last_run: datetime | None = None
        self._total_runs = 0

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def last_run(self) -> datetime | None:
        return self._last_run

    @property
    def total_runs(self) -> int:
        return self._total_runs

    async def start(self) -> None:
        """Start the scheduler and schedule scan jobs for all active users."""
        if self._is_running:
            logger.warning("Agent worker is already running.")
            return

        supabase = get_supabase_client()

        # Load all profiles with active assets
        profiles_resp = supabase.table("profiles").select("*").execute()
        profiles = profiles_resp.data or []

        if not profiles:
            logger.warning("No user profiles found. Agent started but no jobs scheduled.")

        for profile in profiles:
            user_id = profile["id"]
            interval = profile.get("polling_interval", 15)

            # Check if user has watched assets
            assets_resp = (
                supabase.table("watched_assets")
                .select("asset_symbol")
                .eq("user_id", user_id)
                .eq("is_active", True)
                .execute()
            )

            if not assets_resp.data:
                continue

            # Schedule a job for this user
            job_id = f"scan_{user_id}"
            self._scheduler.add_job(
                self._run_scan_cycle,
                "interval",
                minutes=interval,
                args=[user_id],
                id=job_id,
                replace_existing=True,
                next_run_time=datetime.now(timezone.utc),  # Run immediately on start
            )
            logger.info(f"Scheduled scan for user {user_id} every {interval}min")

        self._scheduler.start()
        self._is_running = True
        logger.info("🚀 Agent worker started.")

    async def stop(self) -> None:
        """Stop the scheduler and all jobs."""
        if not self._is_running:
            return

        self._scheduler.shutdown(wait=False)
        self._scheduler = AsyncIOScheduler()  # Reset for potential restart
        self._is_running = False
        logger.info("🛑 Agent worker stopped.")

    async def _run_scan_cycle(self, user_id: str) -> None:
        """
        Execute a single scan cycle for a user.

        1. Fetch user settings and watched assets
        2. Collect prices from Finnhub
        3. Collect news from Marketaux + RSS
        4. Collect political/social from Social Monitor
        5. Send to AI analyzer
        6. Dispatch alerts via Telegram
        7. Log the run
        """
        supabase = get_supabase_client()
        run_id = None

        try:
            # Create agent run record
            run_resp = supabase.table("agent_runs").insert({
                "user_id": user_id,
                "status": "running",
            }).execute()
            run_id = run_resp.data[0]["id"] if run_resp.data else None

            # Fetch user profile
            profile_resp = (
                supabase.table("profiles")
                .select("*")
                .eq("id", user_id)
                .maybe_single()
                .execute()
            )
            if not profile_resp or not profile_resp.data:
                logger.error(f"User {user_id} not found, skipping scan.")
                return

            profile = profile_resp.data
            sensitivity = profile.get("alert_sensitivity", "medium")
            chat_id = profile.get("telegram_chat_id")
            telegram_verified = profile.get("telegram_verified", False)

            # Fetch watched assets
            assets_resp = (
                supabase.table("watched_assets")
                .select("asset_symbol")
                .eq("user_id", user_id)
                .eq("is_active", True)
                .execute()
            )
            asset_symbols = [a["asset_symbol"] for a in (assets_resp.data or [])]

            if not asset_symbols:
                logger.info(f"User {user_id} has no active assets, skipping.")
                return

            # ── Step 1: Collect prices ──
            prices = []
            for symbol in asset_symbols:
                price = await self._finnhub.get_quote(symbol)
                if price:
                    prices.append(price)

            # ── Step 2: Collect ForexFactory economic calendar ──
            watched_currencies = set()
            for s in asset_symbols:
                for part in s.replace("-", "/").split("/"):
                    if len(part) == 3:
                        watched_currencies.add(part.upper())
            if not watched_currencies:
                watched_currencies = {"USD", "EUR", "GBP", "JPY"}

            calendar_items = await self._forexfactory.collect(
                currencies=list(watched_currencies),
                limit=15,
            )

            # ── Step 3: Collect financial news ──
            query_terms = " ".join(
                symbol.replace("/", " ") for symbol in asset_symbols[:3]
            )
            news_items = await self._marketaux.collect(query=query_terms, limit=10)
            rss_items = await self._rss.collect(max_per_feed=5)
            all_news = news_items + rss_items

            # ── Step 4: Collect social / political (Trump Truth, X, RSS) ──
            truth_items = await self._truthsocial.collect(limit=10)
            x_items = await self._x.collect(limit=10)
            rss_social = await self._social.collect(max_per_feed=8)
            all_social = truth_items + x_items + rss_social

            sources_checked = 6  # finnhub, forexfactory, marketaux, rss, truthsocial, x
            items_found = len(all_news) + len(calendar_items) + len(all_social)

            # ── Step 5: AI analysis ──
            analysis = await analyze_market_data(
                prices=prices,
                news_items=all_news,
                social_items=all_social,
                calendar_items=calendar_items,
                user_assets=asset_symbols,
                sensitivity=sensitivity,
            )

            alerts = analysis.get("alerts", [])
            threshold = SENSITIVITY_THRESHOLDS.get(sensitivity, 4)

            # Filter alerts by threshold
            actionable_alerts = [
                a for a in alerts
                if a.get("impact_score", 0) >= threshold
            ]

            alerts_generated = 0

            # ── Step 6: Store and dispatch alerts ──
            for alert_data in actionable_alerts:
                # Store in DB
                supabase.table("alerts").insert({
                    "user_id": user_id,
                    "asset_symbol": ", ".join(alert_data.get("affected_assets", [])),
                    "alert_type": alert_data.get("alert_type", "composite"),
                    "severity": alert_data.get("severity", "info"),
                    "title": alert_data.get("title", "Market Alert"),
                    "body": alert_data.get("summary", ""),
                    "ai_analysis": alert_data.get("summary", ""),
                    "source_data": {
                        "prices": [p.symbol for p in prices],
                        "news_count": len(all_news),
                        "calendar_count": len(calendar_items),
                        "social_count": len(all_social),
                    },
                    "impact_score": alert_data.get("impact_score"),
                    "sentiment": alert_data.get("sentiment"),
                    "telegram_sent": False,
                }).execute()

                # Send Telegram notification
                if chat_id and telegram_verified:
                    sent = await send_alert(chat_id, alert_data)
                    if sent:
                        alerts_generated += 1

            # Store news, calendar, and social items (deduplicate by URL)
            all_collected_feed_items = all_news + calendar_items + all_social
            for item in all_collected_feed_items[:50]:
                if item.url:
                    try:
                        supabase.table("news_items").upsert(
                            {
                                "source": item.source,
                                "source_type": item.source_type,
                                "title": item.title,
                                "url": item.url,
                                "summary": item.summary,
                                "sentiment_score": item.sentiment_score,
                                "published_at": item.published_at.isoformat() if item.published_at else None,
                            },
                            on_conflict="url",
                        ).execute()
                    except Exception:
                        pass  # Ignore duplicate insert errors

            # ── Step 7: Update run record ──
            self._last_run = datetime.now(timezone.utc)
            self._total_runs += 1

            if run_id:
                supabase.table("agent_runs").update({
                    "status": "completed",
                    "completed_at": self._last_run.isoformat(),
                    "sources_checked": sources_checked,
                    "items_found": items_found,
                    "alerts_generated": alerts_generated,
                }).eq("id", run_id).execute()

            # Clear seen caches for next cycle
            self._rss.clear_seen()
            self._social.clear_seen()
            self._truthsocial.clear_seen()
            self._x.clear_seen()

            logger.info(
                f"Scan complete for user {user_id}: "
                f"{items_found} items, {alerts_generated} alerts sent"
            )

        except Exception as e:
            logger.error(f"Scan cycle error for user {user_id}: {e}", exc_info=True)

            if run_id:
                try:
                    supabase.table("agent_runs").update({
                        "status": "failed",
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                        "error_log": str(e),
                    }).eq("id", run_id).execute()
                except Exception:
                    pass

    def get_status(self) -> dict:
        """Return current worker status."""
        next_run = None
        active_jobs = 0

        if self._is_running and self._scheduler.get_jobs():
            jobs = self._scheduler.get_jobs()
            active_jobs = len(jobs)
            if jobs:
                next_run = jobs[0].next_run_time

        return {
            "is_running": self._is_running,
            "last_run_at": self._last_run.isoformat() if self._last_run else None,
            "next_run_at": next_run.isoformat() if next_run else None,
            "total_runs": self._total_runs,
            "active_users": active_jobs,
        }


# Module-level singleton
agent_worker = AgentWorker()
