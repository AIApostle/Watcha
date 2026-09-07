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
        self._unsupported_symbols: set[str] = set()

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
        if symbol in self._unsupported_symbols:
            return await self._fallback_quote(symbol)

        finnhub_symbol = SYMBOL_MAP.get(symbol)
        if not finnhub_symbol:
            return await self._fallback_quote(symbol)

        try:
            data = await self._request("/quote", {"symbol": finnhub_symbol})

            # Finnhub returns: c=current, o=open, h=high, l=low, pc=prev close, dp=% change, d=change
            if not data or data.get("c", 0) == 0:
                return await self._fallback_quote(symbol)

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
            if "403" in str(e):
                self._unsupported_symbols.add(symbol)
                logger.debug(f"Finnhub free tier does not support {symbol} (403), using live fallback.")
            else:
                logger.warning(f"Finnhub quote unavailable for {symbol} ({e}), using live fallback quotes.")
            return await self._fallback_quote(symbol)

    async def _fallback_quote(self, symbol: str) -> PriceData | None:
        """Fetch fallback market price from free public APIs if Finnhub key is invalid."""
        try:
            # Crypto fallback via Binance
            if symbol in ("BTC/USD", "ETH/USD"):
                pair = symbol.replace("/", "").replace("USD", "USDT")
                resp = await self._client.get(
                    f"https://api.binance.com/api/v3/ticker/24hr?symbol={pair}",
                    timeout=5.0,
                )
                if resp.status_code == 200:
                    d = resp.json()
                    curr = float(d.get("lastPrice", 0))
                    prev = float(d.get("prevClosePrice", 0))
                    chg = float(d.get("priceChange", 0))
                    pct = float(d.get("priceChangePercent", 0))
                    return PriceData(
                        symbol=symbol,
                        current_price=curr,
                        previous_close=prev,
                        change=chg,
                        change_percent=pct,
                        timestamp=datetime.now(timezone.utc),
                    )

            # Forex & Commodities fallback via Open Exchange Rates
            resp = await self._client.get(
                "https://open.er-api.com/v6/latest/USD",
                timeout=5.0,
            )
            if resp.status_code == 200:
                rates = resp.json().get("rates", {})
                curr = None
                if symbol == "EUR/USD" and rates.get("EUR"):
                    curr = round(1.0 / rates["EUR"], 4)
                elif symbol == "GBP/USD" and rates.get("GBP"):
                    curr = round(1.0 / rates["GBP"], 4)
                elif symbol == "AUD/USD" and rates.get("AUD"):
                    curr = round(1.0 / rates["AUD"], 4)
                elif symbol == "USD/JPY" and rates.get("JPY"):
                    curr = round(rates["JPY"], 3)
                elif symbol == "USD/CAD" and rates.get("CAD"):
                    curr = round(rates["CAD"], 4)
                elif symbol == "USD/CHF" and rates.get("CHF"):
                    curr = round(rates["CHF"], 4)
                # Commodities: Gold & Silver via live Yahoo Finance or Binance PAXG
                elif symbol in ("XAU/USD", "XAG/USD"):
                    metal_ticker = "GC=F" if symbol == "XAU/USD" else "SI=F"
                    try:
                        y_resp = await self._client.get(
                            f"https://query1.finance.yahoo.com/v8/finance/chart/{metal_ticker}?interval=1d",
                            headers={"User-Agent": "Mozilla/5.0"},
                            timeout=5.0,
                        )
                        if y_resp.status_code == 200:
                            meta = y_resp.json()["chart"]["result"][0]["meta"]
                            curr_val = float(meta["regularMarketPrice"])
                            prev_val = float(meta.get("previousClose") or meta.get("chartPreviousClose") or curr_val)
                            change_val = round(curr_val - prev_val, 2)
                            pct_val = round((change_val / prev_val) * 100, 2) if prev_val else 0.0
                            return PriceData(
                                symbol=symbol,
                                current_price=curr_val,
                                previous_close=prev_val,
                                change=change_val,
                                change_percent=pct_val,
                                timestamp=datetime.now(timezone.utc),
                            )
                    except Exception as y_err:
                        logger.warning(f"Yahoo price fetch failed for {symbol}: {y_err}")

                    # Secondary fallback for Gold via Binance PAXG (backed 1:1 by physical gold)
                    if symbol == "XAU/USD":
                        try:
                            b_resp = await self._client.get(
                                "https://api.binance.com/api/v3/ticker/24hr?symbol=PAXGUSDT",
                                timeout=5.0,
                            )
                            if b_resp.status_code == 200:
                                d = b_resp.json()
                                return PriceData(
                                    symbol=symbol,
                                    current_price=float(d.get("lastPrice", 0)),
                                    previous_close=float(d.get("prevClosePrice", 0)),
                                    change=float(d.get("priceChange", 0)),
                                    change_percent=float(d.get("priceChangePercent", 0)),
                                    timestamp=datetime.now(timezone.utc),
                                )
                        except Exception as b_err:
                            logger.warning(f"Binance PAXG fallback failed: {b_err}")

                if curr is not None:
                    return PriceData(
                        symbol=symbol,
                        current_price=curr,
                        change=0.0,
                        change_percent=0.0,
                        timestamp=datetime.now(timezone.utc),
                    )
        except Exception as err:
            logger.error(f"Fallback price error for {symbol}: {err}")

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
