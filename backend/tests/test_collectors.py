"""Self-contained tests for all data collectors and prompt construction."""

import asyncio
import unittest
from app.collectors.forexfactory_client import ForexFactoryCollector
from app.collectors.truthsocial_scraper import TruthSocialScraper
from app.collectors.x_scraper import XScraper
from app.collectors.base import CollectedItem, PriceData
from app.agent.analyzer import _build_prompt


class TestCollectors(unittest.TestCase):
    """Test suite for data collection and analysis formatting."""

    def test_analyzer_prompt_construction(self):
        """Verify _build_prompt correctly formats economic calendar and Trump social posts."""
        prices = [
            PriceData(
                symbol="XAU/USD",
                current_price=2750.50,
                change=15.2,
                change_percent=0.55,
            ),
            PriceData(
                symbol="EUR/USD",
                current_price=1.0850,
                change=-0.002,
                change_percent=-0.18,
            ),
        ]

        calendar_items = [
            CollectedItem(
                source="ForexFactory",
                source_type="calendar",
                title="[High Impact] USD: Non-Farm Employment Change (Forecast: 160K, Prev: 142K)",
                summary="High impact release for USD.",
            ),
        ]

        news_items = [
            CollectedItem(
                source="Reuters",
                source_type="news",
                title="Gold rallies amid safe-haven demand",
                summary="Spot gold was up 0.5% at $2,750.",
            ),
        ]

        social_items = [
            CollectedItem(
                source="Truth Social (@realDonaldTrump)",
                source_type="social",
                title="[Trump Truth | Tariffs] 25% tariff on foreign auto imports.",
                summary="New executive order on auto tariffs announced.",
                raw_data={"matched_keywords": ["tariff", "auto"]},
            ),
        ]

        prompt = _build_prompt(
            prices=prices,
            news_items=news_items,
            social_items=social_items,
            calendar_items=calendar_items,
            user_assets=["XAU/USD", "EUR/USD"],
            sensitivity="high",
        )

        self.assertIn("XAU/USD", prompt)
        self.assertIn("EUR/USD", prompt)
        self.assertIn("ForexFactory Economic Calendar", prompt)
        self.assertIn("Non-Farm Employment Change", prompt)
        self.assertIn("Political Statements & Social Posts", prompt)
        self.assertIn("Truth Social (@realDonaldTrump)", prompt)
        self.assertIn("Tariffs", prompt)

    def test_forexfactory_collector_sync(self):
        """Run async ForexFactory test."""
        asyncio.run(self._async_forexfactory())

    async def _async_forexfactory(self):
        collector = ForexFactoryCollector()
        items = await collector.collect(limit=5)
        self.assertGreater(len(items), 0, "ForexFactory collector should return items")
        first = items[0]
        self.assertIsInstance(first, CollectedItem)
        self.assertEqual(first.source_type, "calendar")
        self.assertIn("ForexFactory", first.source)
        self.assertGreater(len(first.title), 5)

    def test_truthsocial_scraper_sync(self):
        """Run async Truth Social test."""
        asyncio.run(self._async_truthsocial())

    async def _async_truthsocial(self):
        scraper = TruthSocialScraper()
        items = await scraper.collect(limit=5)
        self.assertGreater(len(items), 0, "Truth Social scraper should return posts")
        first = items[0]
        self.assertIsInstance(first, CollectedItem)
        self.assertEqual(first.source_type, "social")
        self.assertIn("Truth Social", first.source)
        self.assertIsNotNone(first.url)
        self.assertNotIn("<p>", first.summary)

    def test_x_scraper_sync(self):
        """Run async X scraper test."""
        asyncio.run(self._async_x())

    async def _async_x(self):
        scraper = XScraper()
        items = await scraper.collect(limit=5)
        self.assertGreater(len(items), 0, "X scraper should return tweets")
        first = items[0]
        self.assertIsInstance(first, CollectedItem)
        self.assertEqual(first.source_type, "social")
        self.assertIn("X", first.source)
        self.assertIsNotNone(first.url)
        self.assertIn("x.com", first.url)


if __name__ == "__main__":
    unittest.main()
