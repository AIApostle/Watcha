"""Data collectors module."""

from app.collectors.base import BaseCollector, CollectedItem, PriceData
from app.collectors.finnhub_client import FinnhubCollector
from app.collectors.forexfactory_client import ForexFactoryCollector
from app.collectors.marketaux_client import MarketauxCollector
from app.collectors.rss_collector import RSSCollector
from app.collectors.social_monitor import SocialMonitor
from app.collectors.truthsocial_scraper import TruthSocialScraper
from app.collectors.x_scraper import XScraper

__all__ = [
    "BaseCollector",
    "CollectedItem",
    "PriceData",
    "FinnhubCollector",
    "ForexFactoryCollector",
    "MarketauxCollector",
    "RSSCollector",
    "SocialMonitor",
    "TruthSocialScraper",
    "XScraper",
]
