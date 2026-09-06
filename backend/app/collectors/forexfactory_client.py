"""
ForexFactory collector for economic calendar events and news.

Monitors scheduled high/medium impact economic events (NFP, CPI, interest rates,
GDP, FOMC, etc.) that move currency pairs, gold, and financial markets.

Uses Fair Economy Media's official ForexFactory feed with in-memory caching
to prevent Cloudflare rate-limiting, and falls back to live forex calendar
and breaking news feeds (ForexLive, MyFxBook) if the primary endpoint is throttled.
"""

import csv
import io
import logging
import time
from datetime import datetime, timezone
from typing import Any

import feedparser
import httpx

from app.collectors.base import BaseCollector, CollectedItem

logger = logging.getLogger(__name__)

# Primary ForexFactory calendar endpoints (Fair Economy Media CDN)
PRIMARY_JSON_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
PRIMARY_CSV_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.csv"

# Fallback calendar and market event feeds
FALLBACK_FEEDS: dict[str, str] = {
    "ForexLive Breaking News": "https://www.forexlive.com/feed/news",
    "FXStreet Macro News": "https://www.fxstreet.com/rss/news",
    "MyFxBook Calendar": "https://www.myfxbook.com/rss/forex-economic-calendar-events",
}

# Cache duration in seconds (1 hour)
CACHE_TTL_SECONDS = 3600

# High and medium impact keywords indicating market-moving events
HIGH_IMPACT_KEYWORDS = [
    "interest rate",
    "rate decision",
    "fomc",
    "cpi",
    "inflation",
    "nfp",
    "non-farm",
    "employment",
    "unemployment",
    "gdp",
    "central bank",
    "powell",
    "lagarde",
    "ecb",
    "boe",
    "boj",
    "pce",
    "retail sales",
    "trade balance",
    "pmi",
]


class ForexFactoryCollector(BaseCollector):
    """
    Collector for ForexFactory economic calendar events.

    Tracks high-impact macroeconomic releases affecting currencies and commodities.
    """

    def __init__(self, cache_ttl: int = CACHE_TTL_SECONDS):
        self._cache_ttl = cache_ttl
        self._cached_events: list[dict[str, Any]] = []
        self._last_fetch_time: float = 0
        self._headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, text/csv, */*",
        }

    @property
    def name(self) -> str:
        return "ForexFactory"

    def _is_cache_valid(self) -> bool:
        """Check if cached calendar events are still fresh."""
        return (
            bool(self._cached_events)
            and (time.time() - self._last_fetch_time) < self._cache_ttl
        )

    async def _fetch_from_faireconomy(self) -> list[dict[str, Any]]:
        """Fetch economic calendar events from Fair Economy Media CDN."""
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            # Try JSON first
            try:
                response = await client.get(PRIMARY_JSON_URL, headers=self._headers)
                if response.status_code == 200 and response.text.strip().startswith("["):
                    events = response.json()
                    logger.info(f"Loaded {len(events)} events from ForexFactory JSON feed")
                    return events
                elif response.status_code == 429:
                    logger.warning("ForexFactory JSON feed returned 429 (rate limited)")
            except Exception as e:
                logger.warning(f"Error fetching ForexFactory JSON: {e}")

            # Try CSV fallback
            try:
                response = await client.get(PRIMARY_CSV_URL, headers=self._headers)
                if response.status_code == 200 and "Title,Country" in response.text:
                    reader = csv.DictReader(io.StringIO(response.text))
                    events = []
                    for row in reader:
                        events.append({
                            "title": row.get("Title", ""),
                            "country": row.get("Country", ""),
                            "date": row.get("Date", ""),
                            "time": row.get("Time", ""),
                            "impact": row.get("Impact", "Low"),
                            "forecast": row.get("Forecast", ""),
                            "previous": row.get("Previous", ""),
                            "url": row.get("URL", "https://www.forexfactory.com/calendar"),
                        })
                    logger.info(f"Loaded {len(events)} events from ForexFactory CSV feed")
                    return events
            except Exception as e:
                logger.warning(f"Error fetching ForexFactory CSV: {e}")

        return []

    async def _fetch_fallback_events(self) -> list[CollectedItem]:
        """Fetch calendar and breaking macro events from fallback RSS feeds."""
        fallback_items: list[CollectedItem] = []
        for feed_name, feed_url in FALLBACK_FEEDS.items():
            try:
                parsed = feedparser.parse(feed_url)
                for entry in parsed.entries[:10]:
                    title = entry.get("title", "")
                    summary = entry.get("summary", "")
                    link = entry.get("link", "https://www.forexfactory.com/calendar")

                    # Check for high-impact macro relevance
                    combined = f"{title} {summary}".lower()
                    matched = [kw for kw in HIGH_IMPACT_KEYWORDS if kw in combined]
                    impact = "High" if matched else "Medium"

                    fallback_items.append(
                        CollectedItem(
                            source=f"ForexFactory ({feed_name})",
                            source_type="calendar",
                            title=f"[{impact} Impact] {title}",
                            url=link,
                            summary=summary or title,
                            published_at=datetime.now(timezone.utc),
                            raw_data={
                                "feed": feed_name,
                                "matched_keywords": matched,
                                "impact": impact,
                            },
                        )
                    )
            except Exception as e:
                logger.warning(f"Error reading fallback feed {feed_name}: {e}")

        return fallback_items

    async def collect(self, **kwargs) -> list[CollectedItem]:
        """
        Collect economic calendar events from ForexFactory.

        Keyword Args:
            impact_levels: list of impacts to include, e.g. ["High", "Medium"] (default: ["High", "Medium"])
            currencies: list of country/currency codes to filter (e.g. ["USD", "EUR", "GBP"])
            limit: maximum items to return (default: 25)
        """
        impact_levels = kwargs.get("impact_levels", ["High", "Medium"])
        currencies = kwargs.get("currencies")
        limit = kwargs.get("limit", 25)

        # Refresh cache if expired
        if not self._is_cache_valid():
            fresh_events = await self._fetch_from_faireconomy()
            if fresh_events:
                self._cached_events = fresh_events
                self._last_fetch_time = time.time()

        items: list[CollectedItem] = []

        # Process cached events
        if self._cached_events:
            for event in self._cached_events:
                impact = event.get("impact", "Low")
                country = event.get("country", "").upper()
                title = event.get("title", "")

                # Filter by impact
                if impact_levels and impact not in impact_levels:
                    continue

                # Filter by currency if requested
                if currencies and country and country not in currencies:
                    continue

                forecast = event.get("forecast") or "N/A"
                previous = event.get("previous") or "N/A"
                raw_date = event.get("date")

                # Parse date if available
                dt: datetime | None = None
                if raw_date:
                    try:
                        dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                    except Exception:
                        pass

                display_title = (
                    f"[{impact} Impact] {country}: {title} (Forecast: {forecast}, Prev: {previous})"
                )
                summary = (
                    f"ForexFactory Economic Calendar — {country} {title}. "
                    f"Impact: {impact}. Scheduled: {raw_date or 'This week'}. "
                    f"Forecast: {forecast}. Previous: {previous}."
                )

                items.append(
                    CollectedItem(
                        source="ForexFactory",
                        source_type="calendar",
                        title=display_title,
                        url=event.get("url") or "https://www.forexfactory.com/calendar",
                        summary=summary,
                        published_at=dt or datetime.now(timezone.utc),
                        raw_data=event,
                    )
                )

                if len(items) >= limit:
                    break

        # If primary source produced no items, supplement with fallback macro feeds
        if not items:
            logger.info("Using fallback feeds for ForexFactory macro updates")
            fallback_items = await self._fetch_fallback_events()
            items.extend(fallback_items[:limit])

        return items

    async def health_check(self) -> bool:
        """Check if ForexFactory collector is operational."""
        if self._cached_events:
            return True
        try:
            items = await self.collect(limit=1)
            return len(items) > 0
        except Exception:
            return False
