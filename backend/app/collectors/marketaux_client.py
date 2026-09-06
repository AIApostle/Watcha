"""
Marketaux data collector — financial news with sentiment.

Free tier: 100 requests/day.
Docs: https://www.marketaux.com/documentation
"""

import logging
from datetime import datetime, timezone

import httpx

from app.collectors.base import BaseCollector, CollectedItem
from app.config import get_settings

logger = logging.getLogger(__name__)

MARKETAUX_BASE = "https://api.marketaux.com/v1"


class MarketauxCollector(BaseCollector):
    """Collects financial news with built-in sentiment scoring from Marketaux."""

    def __init__(self):
        self._api_key = get_settings().marketaux_api_key
        self._client = httpx.AsyncClient(timeout=15.0)

    @property
    def name(self) -> str:
        return "Marketaux"

    async def collect(self, **kwargs) -> list[CollectedItem]:
        """
        Fetch financial news articles.

        Keyword Args:
            query: Search query string (e.g., "gold tariff")
            language: Language code (default: "en")
            limit: Max articles to return (default: 10, max: 50 on free tier)
        """
        query = kwargs.get("query", "gold market forex")
        language = kwargs.get("language", "en")
        limit = min(kwargs.get("limit", 10), 50)

        try:
            params = {
                "api_token": self._api_key,
                "search": query,
                "language": language,
                "limit": limit,
                "sort": "published_desc",
            }

            resp = await self._client.get(f"{MARKETAUX_BASE}/news/all", params=params)
            resp.raise_for_status()
            data = resp.json()

            items = []
            for article in data.get("data", []):
                # Extract sentiment if available
                sentiment_score = None
                if article.get("entities"):
                    # Average sentiment across entities
                    sentiments = [
                        e.get("sentiment_score", 0)
                        for e in article["entities"]
                        if e.get("sentiment_score") is not None
                    ]
                    if sentiments:
                        sentiment_score = sum(sentiments) / len(sentiments)

                published_at = None
                if article.get("published_at"):
                    try:
                        published_at = datetime.fromisoformat(
                            article["published_at"].replace("Z", "+00:00")
                        )
                    except (ValueError, TypeError):
                        pass

                items.append(
                    CollectedItem(
                        source="marketaux",
                        source_type="api",
                        title=article.get("title", ""),
                        url=article.get("url"),
                        summary=article.get("description"),
                        sentiment_score=sentiment_score,
                        published_at=published_at,
                        raw_data=article,
                    )
                )

            logger.info(f"Marketaux: collected {len(items)} articles for query '{query}'")
            return items

        except Exception as e:
            logger.error(f"Marketaux collection error: {e}")
            return []

    async def health_check(self) -> bool:
        """Check Marketaux connectivity."""
        try:
            params = {"api_token": self._api_key, "limit": 1}
            resp = await self._client.get(f"{MARKETAUX_BASE}/news/all", params=params)
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
