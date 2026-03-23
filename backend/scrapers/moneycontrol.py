# backend/scrapers/moneycontrol.py - MoneyControl scraper for Indian companies

import requests
from bs4 import BeautifulSoup
from typing import Optional

from scrapers.base import BaseScraper
from utils.logger import get_logger

logger = get_logger(__name__)


class MoneyControlScraper(BaseScraper):
    """Scraper for MoneyControl (Indian financial website)"""

    SEARCH_URL = "https://www.moneycontrol.com/stocks/company_info/search_result.php"

    def __init__(self):
        super().__init__(name="moneycontrol", enabled=True)

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
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()

            paragraphs = soup.find_all("p")
            text = " ".join([p.get_text(strip=True) for p in paragraphs])

            return text

        except Exception:
            return ""

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

            # Find result links in the search results table (not navigation links)
            # MoneyControl search results are typically in table rows or div containers
            result_link = None
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                # Look for company info page links specifically
                if "company_info" in href or "stocks/company_info" in href:
                    result_link = href
                    break

            # Fallback: find any link that points to a stock page
            if not result_link:
                for link in soup.find_all("a", href=True):
                    href = link.get("href", "")
                    if href.startswith("http") and "moneycontrol.com" in href:
                        result_link = href
                        break

            if not result_link:
                logger.debug(f"No MoneyControl result link found for: {company}")
                self.record_failure()
                return None

            # Scrape company page
            page_response = requests.get(
                result_link,
                headers=self.DEFAULT_HEADERS,
                timeout=self.DEFAULT_TIMEOUT
            )

            if page_response.status_code != 200:
                self.record_failure()
                return None

            text = self._extract_text_from_html(page_response.text)
            cleaned = self._clean_text(text)

            if cleaned:
                self.record_success()
                return cleaned
            else:
                self.record_failure()
                return None

        except Exception as e:
            logger.warning(f"MoneyControl scrape failed for {company}: {e}")
            self.record_failure()
            return None
