"""
RSS feed collector — headlines from major financial outlets.

Uses feedparser to parse RSS/Atom feeds. No API key required.
"""

import logging
from datetime import datetime, timezone
from time import mktime

import feedparser

from app.collectors.base import BaseCollector, CollectedItem

logger = logging.getLogger(__name__)

# Pre-configured RSS feeds for financial news
DEFAULT_FEEDS: dict[str, str] = {
    "Reuters Markets": "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best",
    "Investing.com News": "https://www.investing.com/rss/news.rss",
    "Investing.com Commodities": "https://www.investing.com/rss/news_14.rss",
    "Investing.com Forex": "https://www.investing.com/rss/news_1.rss",
    "CNBC Top News": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
    "CNBC World": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100727362",
    "MarketWatch Top Stories": "https://feeds.marketwatch.com/marketwatch/topstories/",
    "MarketWatch Commodities": "https://feeds.marketwatch.com/marketwatch/marketpulse/",
}


class RSSCollector(BaseCollector):
    """Collects news headlines from RSS/Atom feeds."""

    def __init__(self, feeds: dict[str, str] | None = None):
        self._feeds = feeds or DEFAULT_FEEDS
        self._seen_urls: set[str] = set()

    @property
    def name(self) -> str:
        return "RSS Feeds"

    async def collect(self, **kwargs) -> list[CollectedItem]:
        """
        Parse all configured RSS feeds and return deduplicated items.

        Keyword Args:
            max_per_feed: Max items per feed (default: 10)
            max_age_hours: Max age of articles in hours (default: 24)
            feeds: Override feeds dict for this call
        """
        max_per_feed = kwargs.get("max_per_feed", 10)
        max_age_hours = kwargs.get("max_age_hours", 24)
        feeds = kwargs.get("feeds", self._feeds)

        all_items: list[CollectedItem] = []

        for feed_name, feed_url in feeds.items():
            try:
                items = await self._parse_feed(feed_name, feed_url, max_per_feed, max_age_hours)
                all_items.extend(items)
            except Exception as e:
                logger.error(f"RSS error parsing {feed_name}: {e}")

        # Sort by published_at descending (freshest first)
        all_items.sort(
            key=lambda x: x.published_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

        logger.info(f"RSS: collected {len(all_items)} items from {len(feeds)} feeds")
        return all_items

    async def _parse_feed(
        self, feed_name: str, feed_url: str, max_items: int, max_age_hours: int = 24
    ) -> list[CollectedItem]:
        """Parse a single RSS feed."""
        # feedparser is synchronous — it's fast enough for RSS
        parsed = feedparser.parse(feed_url)

        if parsed.bozo and not parsed.entries:
            logger.debug(f"RSS feed {feed_name} skipped (non-XML or unavailable): {parsed.bozo_exception}")
            return []

        now = datetime.now(timezone.utc)
        items = []
        for entry in parsed.entries[:max_items]:
            url = entry.get("link", "")

            # Deduplicate by URL
            if url in self._seen_urls:
                continue

            # Parse publish date
            published_at = None
            if entry.get("published_parsed"):
                try:
                    published_at = datetime.fromtimestamp(
                        mktime(entry.published_parsed), tz=timezone.utc
                    )
                except (ValueError, OverflowError):
                    pass

            # Filter out stale news older than max_age_hours
            if published_at:
                age_hours = (now - published_at).total_seconds() / 3600
                if age_hours > max_age_hours:
                    continue

            self._seen_urls.add(url)

            # Extract summary — strip HTML tags roughly
            summary = entry.get("summary", "")
            if summary:
                import re

                summary = re.sub(r"<[^>]+>", "", summary).strip()[:500]

            items.append(
                CollectedItem(
                    source=feed_name,
                    source_type="rss",
                    title=entry.get("title", "No title"),
                    url=url,
                    summary=summary or None,
                    published_at=published_at,
                    raw_data={
                        "feed": feed_name,
                        "author": entry.get("author"),
                        "tags": [t.get("term") for t in entry.get("tags", [])],
                    },
                )
            )

        return items

    def clear_seen(self):
        """Clear the seen URLs set (call between scan cycles)."""
        self._seen_urls.clear()

    async def health_check(self) -> bool:
        """Check if at least one RSS feed is reachable."""
        try:
            # Test with a reliable feed
            parsed = feedparser.parse(
                "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"
            )
            return len(parsed.entries) > 0
        except Exception:
            return False
