# backend/scrapers/nse.py - NSE India scraper

import requests
from typing import Optional

from scrapers.base import BaseScraper


class NSEScraper(BaseScraper):
    """Scraper for National Stock Exchange of India"""
    
    SEARCH_URL = "https://www.nseindia.com/api/search/autocomplete"
    
    def __init__(self):
        super().__init__(name="nse", enabled=True)
    
    def _clean_text(self, text: str, min_length: int = 50) -> str:
        """Clean and validate scraped text"""
        if not text:
            return ""
        
        text = text.strip()
        
        if len(text) < min_length:
            return ""
        
        return text[:5000]
    
    async def scrape(self, company: str, **kwargs) -> Optional[str]:
        """
        Scrape NSE for company information
        
        Args:
            company: Company name to search for
            
        Returns:
            Scraped text content or None if failed
        """
        try:
            # Use NSE autocomplete API
            search_url = f"{self.SEARCH_URL}?q={company.replace(' ', '%20')}"
            
            response = requests.get(
                search_url,
                headers=self.DEFAULT_HEADERS,
                timeout=self.DEFAULT_TIMEOUT
            )
            
            if response.status_code != 200:
                self.record_failure()
                return None
            
            # The response is typically JSON
            try:
                data = response.json()
                text = str(data)
                cleaned = self._clean_text(text)
                
                if cleaned:
                    self.record_success()
                else:
                    self.record_failure()
                
                return cleaned
                
            except Exception:
                # If not JSON, return raw text
                text = response.text
                cleaned = self._clean_text(text)
                
                if cleaned:
                    self.record_success()
                else:
                    self.record_failure()
                
                return cleaned
            
        except Exception as e:
            self.record_failure()
            return None
