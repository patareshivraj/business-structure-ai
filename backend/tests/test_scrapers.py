# backend/tests/test_scrapers.py - Scraper registry tests

import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.registry import ScraperRegistry, get_registry
from scrapers.base import BaseScraper


class MockScraper(BaseScraper):
    """Mock scraper for testing"""
    
    async def scrape(self, company: str, **kwargs):
        return f"Mock result for {company}"


class TestScraperRegistry:
    """Test scraper registry functionality"""
    
    def setup_method(self):
        """Reset registry before each test"""
        self.registry = ScraperRegistry()
    
    def test_register_scraper(self):
        """Test registering a scraper"""
        scraper = MockScraper(name="test")
        
        self.registry.register(scraper)
        
        assert "test" in self.registry.list_scrapers()
        assert self.registry.get("test") is scraper
    
    def test_register_invalid_scraper(self):
        """Test registering invalid type raises error"""
        with pytest.raises(TypeError):
            self.registry.register("not a scraper")
    
    def test_unregister_scraper(self):
        """Test unregistering a scraper"""
        scraper = MockScraper(name="test")
        self.registry.register(scraper)
        
        result = self.registry.unregister("test")
        
        assert result is True
        assert "test" not in self.registry.list_scrapers()
    
    def test_unregister_nonexistent(self):
        """Test unregistering non-existent scraper"""
        result = self.registry.unregister("nonexistent")
        assert result is False
    
    def test_enable_disable_scraper(self):
        """Test enabling and disabling scrapers"""
        scraper = MockScraper(name="test", enabled=True)
        self.registry.register(scraper)
        
        assert scraper.enabled is True
        
        self.registry.disable("test")
        assert scraper.enabled is False
        
        self.registry.enable("test")
        assert scraper.enabled is True
    
    def test_list_scrapers_enabled_only(self):
        """Test listing only enabled scrapers"""
        self.registry.register(MockScraper(name="enabled", enabled=True))
        self.registry.register(MockScraper(name="disabled", enabled=False))
        
        all_scrapers = self.registry.list_scrapers()
        enabled_scrapers = self.registry.list_scrapers(enabled_only=True)
        
        assert len(all_scrapers) == 2
        assert len(enabled_scrapers) == 1
        assert "enabled" in enabled_scrapers
    
    def test_get_stats(self):
        """Test getting scraper statistics"""
        scraper = MockScraper(name="test")
        scraper.record_success()
        scraper.record_success()
        scraper.record_failure()
        
        self.registry.register(scraper)
        
        stats = self.registry.get_stats()
        
        assert "test" in stats
        assert stats["test"]["stats"]["calls"] == 3
        assert stats["test"]["stats"]["successes"] == 2
        assert stats["test"]["stats"]["failures"] == 1
    
    def test_clear_registry(self):
        """Test clearing registry"""
        self.registry.register(MockScraper(name="test1"))
        self.registry.register(MockScraper(name="test2"))
        
        self.registry.clear()
        
        assert len(self.registry.list_scrapers()) == 0


class TestBaseScraper:
    """Test base scraper functionality"""
    
    def test_scraper_initialization(self):
        """Test scraper initializes correctly"""
        scraper = MockScraper(name="test", enabled=True)
        
        assert scraper.name == "test"
        assert scraper.enabled is True
        assert scraper.stats["calls"] == 0
    
    def test_record_success(self):
        """Test recording successful scrape"""
        scraper = MockScraper(name="test")
        scraper.record_success()
        
        assert scraper.stats["calls"] == 1
        assert scraper.stats["successes"] == 1
        assert scraper.stats["failures"] == 0
    
    def test_record_failure(self):
        """Test recording failed scrape"""
        scraper = MockScraper(name="test")
        scraper.record_failure()
        
        assert scraper.stats["calls"] == 1
        assert scraper.stats["successes"] == 0
        assert scraper.stats["failures"] == 1
    
    def test_reset_stats(self):
        """Test resetting statistics"""
        scraper = MockScraper(name="test")
        scraper.record_success()
        scraper.record_failure()
        
        scraper.reset_stats()
        
        assert scraper.stats["calls"] == 0
        assert scraper.stats["successes"] == 0
        assert scraper.stats["failures"] == 0
    
    def test_get_info(self):
        """Test getting scraper info"""
        scraper = MockScraper(name="test", enabled=True)
        
        info = scraper.get_info()
        
        assert info["name"] == "test"
        assert info["enabled"] is True
        assert info["type"] == "MockScraper"


class TestGlobalRegistry:
    """Test global registry"""
    
    def test_get_global_registry(self):
        """Test getting global registry"""
        registry = get_registry()
        
        assert isinstance(registry, ScraperRegistry)
        assert registry is get_registry()  # Same instance
