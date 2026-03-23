# backend/scrapers/moneycontrol.py - MoneyControl scraper for Indian companies

import requests
from bs4 import BeautifulSoup
from typing import Optional

from scrapers.base import BaseScraper
from scrapers.web import WebScraper


class MoneyControlScraper(BaseScraper):
    """Scraper for MoneyControl (Indian financial website)"""
    
    SEARCH_URL = "https://www.moneycontrol.com/stocks/company_info/search_result.php"
    
    def __init__(self):
        super().__init__(name="moneycontrol", enabled=True)
        self._web_scraper = WebScraper()
    
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
        Scrape MoneyControl for company information
        
        Args:
            company: Company name to search for
            
        Returns:
            Scraped text content or None if failed
        """
        try:
            # Search for company
            search_url = f"{self.SEARCH_URL}?query={company.replace(' ', '+')}"
            
            response = requests.get(
                search_url,
                headers=self.DEFAULT_HEADERS,
                timeout=self.DEFAULT_TIMEOUT
            )
            
            if response.status_code != 200:
                self.record_failure()
                return None
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Find first result link
            link = soup.find("a")
            
            if not link:
                self.record_failure()
                return None
            
            company_url = link.get("href")
            
            if not company_url:
                self.record_failure()
                return None
            
            # Scrape company page
            result = await self._web_scraper.scrape(company, url=company_url)
            
            if result:
                self.record_success()
                return self._clean_text(result)
            else:
                self.record_failure()
                return None
            
        except Exception as e:
            self.record_failure()
            return None
