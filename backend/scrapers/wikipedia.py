# backend/scrapers/wikipedia.py - Wikipedia scraper

import requests
from typing import Optional

from scrapers.base import BaseScraper


class WikipediaScraper(BaseScraper):
    """Scraper for Wikipedia company information"""
    
    BASE_URL = "https://en.wikipedia.org/api/rest_v1/page/summary"
    
    def __init__(self):
        super().__init__(name="wikipedia", enabled=True)
    
    def _clean_text(self, text: str, min_length: int = 200) -> str:
        """Clean and validate scraped text"""
        if not text:
            return ""
        
        text = text.strip()
        
        if len(text) < min_length:
            return ""
        
        return text[:5000]
    
    async def scrape(self, company: str, **kwargs) -> Optional[str]:
        """
        Scrape Wikipedia summary for a company
        
        Args:
            company: Company name to search for
            
        Returns:
            Wikipedia extract text or None if failed
        """
        try:
            # URL encode company name
            import urllib.parse
            encoded_name = urllib.parse.quote(company.replace(" ", "_"))
            url = f"{self.BASE_URL}/{encoded_name}"
            
            response = requests.get(
                url,
                headers=self.DEFAULT_HEADERS,
                timeout=self.DEFAULT_TIMEOUT
            )
            
            if response.status_code != 200:
                self.record_failure()
                return None
            
            data = response.json()
            extract = data.get("extract", "")
            
            cleaned = self._clean_text(extract)
            
            if cleaned:
                self.record_success()
            else:
                self.record_failure()
            
            return cleaned
            
        except Exception as e:
            self.record_failure()
            return None
