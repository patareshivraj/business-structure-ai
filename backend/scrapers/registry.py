# backend/scrapers/registry.py - Scraper registry with dynamic registration

from typing import Dict, List, Optional, Type, Any
import logging

from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class ScraperRegistry:
    """
    Registry for managing scrapers with dynamic registration.
    Implements the registry pattern for extensible scraper collection.
    """
    
    def __init__(self):
        """Initialize empty registry"""
        self._scrapers: Dict[str, BaseScraper] = {}
        self._scraper_classes: Dict[str, Type[BaseScraper]] = {}
    
    def register(self, scraper: BaseScraper) -> None:
        """
        Register a scraper instance
        
        Args:
            scraper: Scraper instance to register
        """
        if not isinstance(scraper, BaseScraper):
            raise TypeError(f"Scraper must inherit from BaseScraper")
        
        self._scrapers[scraper.name] = scraper
        logger.info(f"Registered scraper: {scraper.name}")
    
    def register_class(self, name: str, scraper_class: Type[BaseScraper]) -> None:
        """
        Register a scraper class for lazy instantiation
        
        Args:
            name: Scraper identifier
            scraper_class: Scraper class to register
        """
        if not issubclass(scraper_class, BaseScraper):
            raise TypeError(f"Scraper class must inherit from BaseScraper")
        
        self._scraper_classes[name] = scraper_class
        logger.info(f"Registered scraper class: {name}")
    
    def unregister(self, name: str) -> bool:
        """
        Unregister a scraper
        
        Args:
            name: Scraper identifier
            
        Returns:
            True if scraper was removed, False if not found
        """
        if name in self._scrapers:
            del self._scrapers[name]
            logger.info(f"Unregistered scraper: {name}")
            return True
        return False
    
    def get(self, name: str) -> Optional[BaseScraper]:
        """
        Get a scraper by name
        
        Args:
            name: Scraper identifier
            
        Returns:
            Scraper instance or None if not found
        """
        return self._scrapers.get(name)
    
    def create(self, name: str, **kwargs) -> Optional[BaseScraper]:
        """
        Create a scraper instance from registered class
        
        Args:
            name: Scraper identifier
            **kwargs: Arguments to pass to scraper constructor
            
        Returns:
            Created scraper instance or None
        """
        scraper_class = self._scraper_classes.get(name)
        if scraper_class:
            scraper = scraper_class(**kwargs)
            self.register(scraper)
            return scraper
        return None
    
    def list_scrapers(self, enabled_only: bool = False) -> List[str]:
        """
        List registered scraper names
        
        Args:
            enabled_only: Only return enabled scrapers
            
        Returns:
            List of scraper names
        """
        scrapers = self._scrapers.values()
        if enabled_only:
            scrapers = [s for s in scrapers if s.enabled]
        return [s.name for s in scrapers]
    
    def get_all(self, enabled_only: bool = False) -> Dict[str, BaseScraper]:
        """
        Get all registered scrapers
        
        Args:
            enabled_only: Only return enabled scrapers
            
        Returns:
            Dictionary of scraper name to instance
        """
        if enabled_only:
            return {name: s for name, s in self._scrapers.items() if s.enabled}
        return self._scrapers.copy()
    
    def enable(self, name: str) -> bool:
        """
        Enable a scraper
        
        Args:
            name: Scraper identifier
            
        Returns:
            True if enabled, False if not found
        """
        scraper = self._scrapers.get(name)
        if scraper:
            scraper.enabled = True
            return True
        return False
    
    def disable(self, name: str) -> bool:
        """
        Disable a scraper
        
        Args:
            name: Scraper identifier
            
        Returns:
            True if disabled, False if not found
        """
        scraper = self._scrapers.get(name)
        if scraper:
            scraper.enabled = False
            return True
        return False
    
    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all scrapers
        
        Returns:
            Dictionary of scraper stats
        """
        return {
            name: scraper.get_info() 
            for name, scraper in self._scrapers.items()
        }
    
    def clear(self) -> None:
        """Clear all registered scrapers"""
        self._scrapers.clear()
        self._scraper_classes.clear()
        logger.info("Cleared all scrapers from registry")


# Global registry instance
_global_registry = ScraperRegistry()


def get_registry() -> ScraperRegistry:
    """Get the global scraper registry"""
    return _global_registry


def register_default_scrapers() -> None:
    """Register all default scrapers"""
    from scrapers.wikipedia import WikipediaScraper
    from scrapers.web import WebScraper
    from scrapers.moneycontrol import MoneyControlScraper
    from scrapers.nse import NSEScraper
    
    registry = get_registry()
    
    # Register default scrapers
    registry.register(WikipediaScraper())
    registry.register(WebScraper())
    registry.register(MoneyControlScraper())
    registry.register(NSEScraper())
    
    logger.info("Registered default scrapers")
