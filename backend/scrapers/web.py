# backend/scrapers/web.py - Generic web scraper

import requests
from bs4 import BeautifulSoup
from typing import Optional, List

from scrapers.base import BaseScraper


class WebScraper(BaseScraper):
    """Generic web scraper for scraping company web pages"""
    
    def __init__(self, timeout: int = 10):
        super().__init__(name="web", enabled=True)
        self.timeout = timeout
    
    def _clean_text(self, text: str, min_length: int = 200) -> str:
        """Clean and validate scraped text"""
        if not text:
            return ""
        
        text = text.strip()
        
        if len(text) < min_length:
            return ""
        
        return text[:5000]
    
    def _extract_text_from_html(self, html: str) -> str:
        """Extract text content from HTML"""
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # Remove script and style elements
            for element in soup(["script", "style"]):
                element.decompose()
            
            # Get text
            text = soup.get_text(separator=" ", strip=True)
            
            # Clean up whitespace
            text = " ".join(text.split())
            
            return text
            
        except Exception:
            return ""
    
    async def scrape(self, company: str, url: str = None, **kwargs) -> Optional[str]:
        """
        Scrape a web page for company information
        
        Args:
            company: Company name (used if URL not provided)
            url: Specific URL to scrape (optional)
            
        Returns:
            Scraped text content or None if failed
        """
        try:
            if not url:
                # Use a search to find company page
                from tavily import TavilyClient
                import os
                
                client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY", ""))
                
                try:
                    results = client.search(
                        query=f"{company} official website about",
                        max_results=1
                    )
                    if results.get("results"):
                        url = results["results"][0].get("url")
                except Exception:
                    pass
            
            if not url:
                self.record_failure()
                return None
            
            response = requests.get(
                url,
                headers=self.DEFAULT_HEADERS,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                self.record_failure()
                return None
            
            text = self._extract_text_from_html(response.text)
            cleaned = self._clean_text(text)
            
            if cleaned:
                self.record_success()
            else:
                self.record_failure()
            
            return cleaned
            
        except Exception as e:
            self.record_failure()
            return None
    
    async def scrape_urls(self, urls: List[str]) -> List[str]:
        """
        Scrape multiple URLs and return combined results
        
        Args:
            urls: List of URLs to scrape
            
        Returns:
            List of scraped text contents
        """
        results = []
        
        for url in urls:
            try:
                response = requests.get(
                    url,
                    headers=self.DEFAULT_HEADERS,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    text = self._extract_text_from_html(response.text)
                    cleaned = self._clean_text(text)
                    
                    if cleaned:
                        results.append(cleaned)
                        
            except Exception:
                continue
        
        return results
