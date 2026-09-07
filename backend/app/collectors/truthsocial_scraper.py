"""
Truth Social scraper for Donald Trump (@realDonaldTrump) posts.

Monitors real-time posts, executive announcements, tariff threats,
trade policy updates, and economic statements directly from Truth Social.

Uses Truth Social's public Mastodon API endpoint — 100% free, no API key required.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any

from bs4 import BeautifulSoup
import httpx

from app.collectors.base import BaseCollector, CollectedItem

logger = logging.getLogger(__name__)

# Trump's public account ID on Truth Social
TRUMP_ACCOUNT_ID = "107780257626128497"
TRUTH_STATUSES_URL = f"https://truthsocial.com/api/v1/accounts/{TRUMP_ACCOUNT_ID}/statuses"

# Market-moving economic and policy keywords
MARKET_KEYWORDS = [
    "tariff",
    "tariffs",
    "trade",
    "trade war",
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
    "executive order",
]


class TruthSocialScraper(BaseCollector):
    """
    Scraper for Donald Trump's Truth Social posts.

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
            "Accept": "application/json, text/plain, */*",
        }

    @property
    def name(self) -> str:
        return "Truth Social (@realDonaldTrump)"

    def clear_seen(self) -> None:
        """Clear seen IDs if set becomes too large."""
        if len(self._seen_ids) > 500:
            self._seen_ids.clear()

    def _clean_content(self, html_content: str) -> str:
        """Strip HTML tags and normalize text from Truth Social post."""
        if not html_content:
            return ""
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            # Replace breaks and paragraphs with newlines/spaces
            for br in soup.find_all(["br", "p"]):
                br.replace_with(f" {br.text} ")
            text = soup.get_text()
            # Collapse whitespace
            return re.sub(r"\s+", " ", text).strip()
        except Exception:
            return re.sub(r"<[^>]+>", "", html_content).strip()

    def _is_market_relevant(self, text: str) -> tuple[bool, list[str]]:
        """Check if post contains market-moving keywords."""
        lower_text = text.lower()
        matched = [kw for kw in self._keywords if kw in lower_text]
        return len(matched) > 0, matched

    async def collect(self, **kwargs) -> list[CollectedItem]:
        """
        Collect recent posts from Truth Social.

        Keyword Args:
            limit: maximum items to fetch (default: 20)
            filter_keywords: whether to filter only by market keywords (default: False,
                             returns all recent posts with market tagging)
        """
        limit = kwargs.get("limit", 20)
        filter_keywords = kwargs.get("filter_keywords", False)
        collected: list[CollectedItem] = []

        try:
            params = {
                "exclude_replies": "true",
                "limit": str(min(limit, 40)),
            }
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(
                    TRUTH_STATUSES_URL,
                    headers=self._headers,
                    params=params,
                )

                if response.status_code != 200:
                    if response.status_code == 403:
                        logger.debug(
                            "Truth Social blocked by Cloudflare challenge (403), falling back to political RSS & web feeds."
                        )
                    else:
                        logger.warning(
                            f"Truth Social returned status {response.status_code}: {response.text[:100]}"
                        )
                    return []

                statuses: list[dict[str, Any]] = response.json()

            for status in statuses:
                status_id = str(status.get("id"))
                if not status_id or status_id in self._seen_ids:
                    continue

                raw_html = status.get("content", "")
                clean_text = self._clean_content(raw_html)

                if not clean_text or len(clean_text) < 10:
                    continue

                is_relevant, matched_kws = self._is_market_relevant(clean_text)

                # If filtering is strictly requested and no keywords matched, skip
                if filter_keywords and not is_relevant:
                    continue

                self._seen_ids.add(status_id)

                # Parse publication time
                created_str = status.get("created_at")
                pub_date: datetime | None = None
                if created_str:
                    try:
                        pub_date = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                    except Exception:
                        pub_date = datetime.now(timezone.utc)

                post_url = status.get("url") or f"https://truthsocial.com/@realDonaldTrump/posts/{status_id}"

                # Generate concise display title
                prefix = "[Trump Truth]"
                if matched_kws:
                    prefix = f"[Trump Truth | {matched_kws[0].title()}]"
                truncated_text = clean_text[:140] + ("..." if len(clean_text) > 140 else "")
                title = f"{prefix} {truncated_text}"

                collected.append(
                    CollectedItem(
                        source="Truth Social (@realDonaldTrump)",
                        source_type="social",
                        title=title,
                        url=post_url,
                        summary=clean_text,
                        published_at=pub_date,
                        raw_data={
                            "id": status_id,
                            "reblogs_count": status.get("reblogs_count", 0),
                            "favourites_count": status.get("favourites_count", 0),
                            "matched_keywords": matched_kws,
                            "is_market_relevant": is_relevant,
                            "media_attachments": [
                                m.get("url") for m in status.get("media_attachments", [])
                            ],
                        },
                    )
                )

                if len(collected) >= limit:
                    break

            logger.info(f"Collected {len(collected)} posts from Truth Social")

        except Exception as e:
            logger.error(f"Error collecting Truth Social posts: {e}", exc_info=True)

        return collected

    async def health_check(self) -> bool:
        """Check if Truth Social endpoint is reachable."""
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(
                    f"https://truthsocial.com/api/v1/accounts/{TRUMP_ACCOUNT_ID}",
                    headers=self._headers,
                )
                return resp.status_code == 200
        except Exception:
            return False
