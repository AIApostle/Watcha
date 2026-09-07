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

    def _is_relevant(self, title: str, summary: str | None, keywords: list[str] | None = None) -> bool:
        """Check if an article matches any of our keywords."""
        kws = keywords if keywords is not None else self._keywords
        text = f"{title} {summary or ''}".lower()
        return any(kw in text for kw in kws)

    async def collect(self, **kwargs) -> list[CollectedItem]:
        """
        Fetch political news and filter by relevance keywords.

        Keyword Args:
            max_per_feed: Max items per feed before filtering (default: 15)
            max_age_hours: Max age of items in hours (default: 24)
            keywords: Override keywords for this call
            extra_keywords: Additional entity keywords to match (e.g. watched people or orgs)
        """
        max_per_feed = kwargs.get("max_per_feed", 15)
        max_age_hours = kwargs.get("max_age_hours", 24)
        keywords = kwargs.get("keywords")
        extra_keywords = kwargs.get("extra_keywords") or []

        active_keywords = [kw.lower() for kw in (keywords or self._keywords)]
        if extra_keywords:
            active_keywords = list(set(active_keywords + [k.lower().strip() for k in extra_keywords if k.strip()]))

        all_items: list[CollectedItem] = []
        now = datetime.now(timezone.utc)

        for feed_name, feed_url in self._feeds.items():
            try:
                parsed = feedparser.parse(feed_url)

                if parsed.bozo and not parsed.entries:
                    logger.debug(f"Social feed {feed_name} skipped (non-XML or unavailable): {parsed.bozo_exception}")
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
                    if not self._is_relevant(title, summary, active_keywords):
                        continue

                    # Parse date
                    published_at = None
                    if entry.get("published_parsed"):
                        try:
                            published_at = datetime.fromtimestamp(
                                mktime(entry.published_parsed), tz=timezone.utc
                            )
                        except (ValueError, OverflowError):
                            pass

                    # Filter out stale items older than max_age_hours
                    if published_at:
                        age_hours = (now - published_at).total_seconds() / 3600
                        if age_hours > max_age_hours:
                            continue

                    self._seen_urls.add(url)

                    # Determine which keywords matched
                    text = f"{title} {summary}".lower()
                    matched_keywords = [kw for kw in active_keywords if kw in text]

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
                logger.error(f"Error parsing social feed {feed_name}: {e}")

        # Sort by published_at descending (freshest first)
        all_items.sort(
            key=lambda x: x.published_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

        logger.info(f"Political Monitor: collected {len(all_items)} relevant items")
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
