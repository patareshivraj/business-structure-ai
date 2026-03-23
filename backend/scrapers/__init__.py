# backend/scrapers - Dynamic scraper registry for Business Structure Intelligence

from scrapers.registry import ScraperRegistry, get_registry
from scrapers.base import BaseScraper

__all__ = ["ScraperRegistry", "get_registry", "BaseScraper"]
