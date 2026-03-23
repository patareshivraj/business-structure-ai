# backend/scrapers/base.py - Base scraper class

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Base class for all scrapers in the registry"""
    
    # Default timeout for requests
    DEFAULT_TIMEOUT = 10
    
    # Default headers for requests
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    def __init__(self, name: str, enabled: bool = True):
        """
        Initialize scraper
        
        Args:
            name: Scraper identifier
            enabled: Whether scraper is enabled by default
        """
        self.name = name
        self.enabled = enabled
        self._stats = {
            "calls": 0,
            "successes": 0,
            "failures": 0
        }
    
    @abstractmethod
    async def scrape(self, company: str, **kwargs) -> Optional[str]:
        """
        Scrape data for a company
        
        Args:
            company: Company name to search for
            **kwargs: Additional scraper-specific parameters
            
        Returns:
            Scraped text content or None if failed
        """
        pass
    
    @property
    def stats(self) -> Dict[str, int]:
        """Get scraper statistics"""
        return self._stats.copy()
    
    def record_success(self):
        """Record a successful scrape"""
        self._stats["calls"] += 1
        self._stats["successes"] += 1
    
    def record_failure(self):
        """Record a failed scrape"""
        self._stats["calls"] += 1
        self._stats["failures"] += 1
    
    def reset_stats(self):
        """Reset scraper statistics"""
        self._stats = {"calls": 0, "successes": 0, "failures": 0}
    
    def is_available(self) -> bool:
        """Check if scraper is available and enabled"""
        return self.enabled
    
    def get_info(self) -> Dict[str, Any]:
        """Get scraper information"""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "stats": self.stats,
            "type": self.__class__.__name__
        }
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', enabled={self.enabled})>"
