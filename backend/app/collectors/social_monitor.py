"""
Social / political news monitor.

Monitors political news RSS feeds that cover Trump statements,
tariff announcements, and other market-moving political events.

Uses free RSS feeds from major outlets' politics sections — no paid API required.
"""

import logging
from datetime import datetime, timezone
from time import mktime

import feedparser

from app.collectors.base import BaseCollector, CollectedItem

logger = logging.getLogger(__name__)

# Political / economic policy RSS feeds
POLITICAL_FEEDS: dict[str, str] = {
    "Reuters World": "https://www.reutersagency.com/feed/?best-topics=political-general&post_type=best",
    "AP Top Headlines": "https://rsshub.app/apnews/topics/apf-topnews",
    "BBC Business": "http://feeds.bbci.co.uk/news/business/rss.xml",
    "BBC World": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "CNBC Politics": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000113",
    "NYT Business": "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
}

# Keywords that signal market-moving political content
DEFAULT_KEYWORDS: list[str] = [
    "trump",
    "tariff",
    "tariffs",
    "trade war",
    "trade deal",
    "sanctions",
    "federal reserve",
    "interest rate",
    "rate cut",
    "rate hike",
    "inflation",
    "gdp",
    "employment",
    "jobs report",
    "treasury",
    "executive order",
    "trade policy",
    "import tax",
    "export ban",
    "currency",
    "dollar",
    "gold",
    "oil",
    "opec",
    "china",
    "eu",
    "nato",
    "biden",
    "congress",
    "debt ceiling",
    "government shutdown",
]


class SocialMonitor(BaseCollector):
    """
    Monitors political news feeds for market-moving statements and events.

    Filters by configurable keywords to surface only relevant political content.
    """

    def __init__(
        self,
        feeds: dict[str, str] | None = None,
        keywords: list[str] | None = None,
    ):
        self._feeds = feeds or POLITICAL_FEEDS
        self._keywords = [kw.lower() for kw in (keywords or DEFAULT_KEYWORDS)]
        self._seen_urls: set[str] = set()

    @property
    def name(self) -> str:
        return "Political Monitor"

    def _is_relevant(self, title: str, summary: str | None) -> bool:
        """Check if an article matches any of our keywords."""
        text = f"{title} {summary or ''}".lower()
        return any(kw in text for kw in self._keywords)

    async def collect(self, **kwargs) -> list[CollectedItem]:
        """
        Fetch political news and filter by relevance keywords.

        Keyword Args:
            max_per_feed: Max items per feed before filtering (default: 15)
            keywords: Override keywords for this call
        """
        max_per_feed = kwargs.get("max_per_feed", 15)
        keywords = kwargs.get("keywords")
        if keywords:
            self._keywords = [kw.lower() for kw in keywords]

        all_items: list[CollectedItem] = []

        for feed_name, feed_url in self._feeds.items():
            try:
                parsed = feedparser.parse(feed_url)

                if parsed.bozo and not parsed.entries:
                    logger.warning(f"Social feed {feed_name} error: {parsed.bozo_exception}")
                    continue

                for entry in parsed.entries[:max_per_feed]:
                    url = entry.get("link", "")
                    if url in self._seen_urls:
                        continue

                    title = entry.get("title", "")
                    summary = entry.get("summary", "")

                    # Strip HTML from summary
                    if summary:
                        import re
                        summary = re.sub(r"<[^>]+>", "", summary).strip()[:500]

                    # Only include relevant articles
                    if not self._is_relevant(title, summary):
                        continue

                    self._seen_urls.add(url)

                    # Parse date
                    published_at = None
                    if entry.get("published_parsed"):
                        try:
                            published_at = datetime.fromtimestamp(
                                mktime(entry.published_parsed), tz=timezone.utc
                            )
                        except (ValueError, OverflowError):
                            pass

                    # Determine which keywords matched
                    text = f"{title} {summary}".lower()
                    matched_keywords = [kw for kw in self._keywords if kw in text]

                    all_items.append(
                        CollectedItem(
                            source=feed_name,
                            source_type="social",
                            title=title,
                            url=url,
                            summary=summary or None,
                            published_at=published_at,
                            raw_data={
                                "feed": feed_name,
                                "matched_keywords": matched_keywords,
                                "author": entry.get("author"),
                            },
                        )
                    )

            except Exception as e:
                logger.error(f"Social monitor error for {feed_name}: {e}")

        logger.info(f"Social monitor: found {len(all_items)} relevant items")
        return all_items

    def clear_seen(self):
        """Clear seen URLs between scan cycles."""
        self._seen_urls.clear()

    async def health_check(self) -> bool:
        """Check if at least one political feed is reachable."""
        try:
            parsed = feedparser.parse("http://feeds.bbci.co.uk/news/business/rss.xml")
            return len(parsed.entries) > 0
        except Exception:
            return False
