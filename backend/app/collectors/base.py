"""Abstract base class for all data collectors."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class CollectedItem:
    """A single item collected from any data source."""

    source: str  # e.g. "finnhub", "marketaux", "reuters_rss"
    source_type: str  # "api", "rss", "social"
    title: str
    url: str | None = None
    summary: str | None = None
    sentiment_score: float | None = None
    published_at: datetime | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class PriceData:
    """Real-time price data for an asset."""

    symbol: str  # e.g. "XAU/USD"
    current_price: float
    open_price: float | None = None
    high_price: float | None = None
    low_price: float | None = None
    previous_close: float | None = None
    change: float | None = None
    change_percent: float | None = None
    timestamp: datetime | None = None


class BaseCollector(ABC):
    """Interface that all data collectors must implement."""

    @abstractmethod
    async def collect(self, **kwargs) -> list[CollectedItem]:
        """Collect data items from the source."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the data source is reachable and functional."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this collector."""
        ...
