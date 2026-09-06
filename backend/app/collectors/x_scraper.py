"""
X (Twitter) scraper for Donald Trump (@realDonaldTrump) tweets.

Extracts presidential statements, economic declarations, trade remarks,
and policy announcements using Twitter's official syndication profile endpoint.

100% free — requires no paid Twitter API key or subscription.
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from bs4 import BeautifulSoup
import httpx

from app.collectors.base import BaseCollector, CollectedItem

logger = logging.getLogger(__name__)

# Official Twitter syndication timeline endpoint
X_SYNDICATION_URL = "https://syndication.twitter.com/srv/timeline-profile/screen-name/realDonaldTrump"

# Market-moving economic and policy keywords
MARKET_KEYWORDS = [
    "tariff",
    "tariffs",
    "trade",
    "trade war",
    "trade deal",
    "dollar",
    "currency",
    "china",
    "mexico",
    "canada",
    "europe",
    "eu",
    "fed",
    "federal reserve",
    "powell",
    "interest rate",
    "rates",
    "inflation",
    "economy",
    "jobs",
    "tax",
    "taxes",
    "oil",
    "energy",
    "opec",
    "gold",
    "stock market",
    "bonds",
    "sanction",
    "sanctions",
    "deficit",
    "debt",
]

TWITTER_DATE_FORMAT = "%a %b %d %H:%M:%S %z %Y"


class XScraper(BaseCollector):
    """
    Scraper for Donald Trump's posts on X (Twitter).

    Captures trade and macro statements that impact gold, currencies, and markets.
    """

    def __init__(self, keywords: list[str] | None = None):
        self._keywords = [kw.lower() for kw in (keywords or MARKET_KEYWORDS)]
        self._seen_ids: set[str] = set()
        self._headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

    @property
    def name(self) -> str:
        return "X (@realDonaldTrump)"

    def clear_seen(self) -> None:
        """Clear seen IDs if set becomes too large."""
        if len(self._seen_ids) > 500:
            self._seen_ids.clear()

    def _is_market_relevant(self, text: str) -> tuple[bool, list[str]]:
        """Check if tweet contains market-moving keywords."""
        lower_text = text.lower()
        matched = [kw for kw in self._keywords if kw in lower_text]
        return len(matched) > 0, matched

    def _extract_timeline_from_html(self, html: str) -> list[dict[str, Any]]:
        """Extract timeline entries from Next.js payload inside Twitter syndication HTML."""
        try:
            match = re.search(
                r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                html,
                re.DOTALL,
            )
            if not match:
                return []

            data = json.loads(match.group(1))
            props = data.get("props", {}).get("pageProps", {})
            timeline = props.get("timeline", {})
            return timeline.get("entries", [])
        except Exception as e:
            logger.warning(f"Error extracting X Next.js data: {e}")
            return []

    async def collect(self, **kwargs) -> list[CollectedItem]:
        """
        Collect recent tweets from @realDonaldTrump on X.

        Keyword Args:
            limit: maximum items to fetch (default: 20)
            filter_keywords: whether to filter only by market keywords (default: False)
        """
        limit = kwargs.get("limit", 20)
        filter_keywords = kwargs.get("filter_keywords", False)
        collected: list[CollectedItem] = []

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(X_SYNDICATION_URL, headers=self._headers)

                if response.status_code != 200:
                    logger.warning(
                        f"X Syndication returned status {response.status_code}: {response.text[:100]}"
                    )
                    return []

                entries = self._extract_timeline_from_html(response.text)

            for entry in entries:
                content = entry.get("content", {})
                tweet = content.get("tweet", {})
                if not tweet:
                    continue

                tweet_id = tweet.get("id_str")
                if not tweet_id or tweet_id in self._seen_ids:
                    continue

                full_text = tweet.get("full_text") or tweet.get("text") or ""
                # Clean up URL links from end of tweet
                cleaned_text = re.sub(r"https://t\.co/\w+", "", full_text).strip()

                if not cleaned_text:
                    continue

                is_relevant, matched_kws = self._is_market_relevant(cleaned_text)

                if filter_keywords and not is_relevant:
                    continue

                self._seen_ids.add(tweet_id)

                # Parse date
                raw_date = tweet.get("created_at")
                pub_date: datetime | None = None
                if raw_date:
                    try:
                        pub_date = datetime.strptime(raw_date, TWITTER_DATE_FORMAT)
                    except Exception:
                        pub_date = datetime.now(timezone.utc)

                tweet_url = f"https://x.com/realDonaldTrump/status/{tweet_id}"

                # Generate concise display title
                prefix = "[Trump on X]"
                if matched_kws:
                    prefix = f"[Trump on X | {matched_kws[0].title()}]"
                truncated = cleaned_text[:140] + ("..." if len(cleaned_text) > 140 else "")
                title = f"{prefix} {truncated}"

                collected.append(
                    CollectedItem(
                        source="X (@realDonaldTrump)",
                        source_type="social",
                        title=title,
                        url=tweet_url,
                        summary=cleaned_text,
                        published_at=pub_date,
                        raw_data={
                            "id": tweet_id,
                            "retweet_count": tweet.get("retweet_count", 0),
                            "favorite_count": tweet.get("favorite_count", 0),
                            "matched_keywords": matched_kws,
                            "is_market_relevant": is_relevant,
                        },
                    )
                )

                if len(collected) >= limit:
                    break

            logger.info(f"Collected {len(collected)} tweets from X (@realDonaldTrump)")

        except Exception as e:
            logger.error(f"Error collecting tweets from X: {e}", exc_info=True)

        return collected

    async def health_check(self) -> bool:
        """Check if X syndication endpoint is reachable."""
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(X_SYNDICATION_URL, headers=self._headers)
                return resp.status_code == 200
        except Exception:
            return False
