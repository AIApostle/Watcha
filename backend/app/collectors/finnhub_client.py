"""
Finnhub data collector — market prices and news.

Free tier: 60 API calls/minute.
Docs: https://finnhub.io/docs/api
"""

import logging
from datetime import datetime, timezone

import httpx

from app.collectors.base import BaseCollector, CollectedItem, PriceData
from app.config import get_settings

logger = logging.getLogger(__name__)

FINNHUB_BASE = "https://finnhub.io/api/v1"

# Finnhub uses specific symbol formats.
# For forex: "OANDA:XAU_USD" for gold, "OANDA:EUR_USD" for euro, etc.
# For crypto: "BINANCE:BTCUSDT"
# For stocks: just the ticker, e.g. "AAPL"
SYMBOL_MAP = {
    "XAU/USD": "OANDA:XAU_USD",
    "XAG/USD": "OANDA:XAG_USD",
    "EUR/USD": "OANDA:EUR_USD",
    "GBP/USD": "OANDA:GBP_USD",
    "USD/JPY": "OANDA:USD_JPY",
    "AUD/USD": "OANDA:AUD_USD",
    "USD/CHF": "OANDA:USD_CHF",
    "USD/CAD": "OANDA:USD_CAD",
    "BTC/USD": "BINANCE:BTCUSDT",
    "ETH/USD": "BINANCE:ETHUSDT",
}


class FinnhubCollector(BaseCollector):
    """Collects market prices and news from Finnhub."""

    def __init__(self):
        self._api_key = get_settings().finnhub_api_key
        self._client = httpx.AsyncClient(timeout=15.0)

    @property
    def name(self) -> str:
        return "Finnhub"

    async def _request(self, endpoint: str, params: dict | None = None) -> dict | list:
        """Make an authenticated GET request to Finnhub."""
        params = params or {}
        params["token"] = self._api_key

        resp = await self._client.get(f"{FINNHUB_BASE}{endpoint}", params=params)
        resp.raise_for_status()
        return resp.json()

    async def get_quote(self, symbol: str) -> PriceData | None:
        """
        Fetch a real-time quote for a symbol.

        Returns PriceData or None if the symbol is unsupported.
        """
        finnhub_symbol = SYMBOL_MAP.get(symbol)
        if not finnhub_symbol:
            logger.warning(f"No Finnhub mapping for symbol: {symbol}")
            return None

        try:
            data = await self._request("/quote", {"symbol": finnhub_symbol})

            # Finnhub returns: c=current, o=open, h=high, l=low, pc=prev close, dp=% change, d=change
            if not data or data.get("c", 0) == 0:
                logger.warning(f"No price data for {symbol} ({finnhub_symbol})")
                return None

            return PriceData(
                symbol=symbol,
                current_price=data["c"],
                open_price=data.get("o"),
                high_price=data.get("h"),
                low_price=data.get("l"),
                previous_close=data.get("pc"),
                change=data.get("d"),
                change_percent=data.get("dp"),
                timestamp=datetime.fromtimestamp(data.get("t", 0), tz=timezone.utc)
                if data.get("t")
                else datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.error(f"Finnhub quote error for {symbol}: {e}")
            return None

    async def collect(self, **kwargs) -> list[CollectedItem]:
        """Fetch general market news from Finnhub."""
        category = kwargs.get("category", "general")

        try:
            data = await self._request("/news", {"category": category})
            items = []

            for article in data[:20]:  # Limit to 20 items
                items.append(
                    CollectedItem(
                        source="finnhub",
                        source_type="api",
                        title=article.get("headline", ""),
                        url=article.get("url"),
                        summary=article.get("summary"),
                        published_at=datetime.fromtimestamp(
                            article.get("datetime", 0), tz=timezone.utc
                        )
                        if article.get("datetime")
                        else None,
                        raw_data=article,
                    )
                )

            logger.info(f"Finnhub: collected {len(items)} news items")
            return items

        except Exception as e:
            logger.error(f"Finnhub news collection error: {e}")
            return []

    async def health_check(self) -> bool:
        """Check Finnhub connectivity."""
        try:
            await self._request("/news", {"category": "general"})
            return True
        except Exception:
            return False

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
