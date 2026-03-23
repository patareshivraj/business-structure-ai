# backend/scrapers/nse.py - NSE India scraper

import requests
import urllib.parse
from typing import Optional

from scrapers.base import BaseScraper
from utils.logger import get_logger

logger = get_logger(__name__)


class NSEScraper(BaseScraper):
    """Scraper for National Stock Exchange of India"""

    SEARCH_URL = "https://www.nseindia.com/api/search/autocomplete"

    def __init__(self):
        super().__init__(name="nse", enabled=True)

    def _parse_nse_response(self, data: dict, company: str) -> str:
        """Parse NSE JSON response into a human-readable text summary"""
        parts = [f"NSE India data for {company}:"]

        # Handle autocomplete response
        symbols = data.get("symbols", [])
        if symbols:
            for sym in symbols[:10]:
                symbol_name = sym.get("symbol", "")
                company_name = sym.get("symbol_info", sym.get("company_name", ""))
                activeSeries = sym.get("activeSeries", [])

                entry = f"- {symbol_name}"
                if company_name:
                    entry += f" ({company_name})"
                if activeSeries:
                    entry += f", Series: {', '.join(activeSeries)}"
                parts.append(entry)

        # Handle other response formats
        if not symbols:
            # Try to extract any useful info from top-level keys
            for key in ["info", "metadata", "priceInfo", "industryInfo"]:
                if key in data:
                    val = data[key]
                    if isinstance(val, dict):
                        for k, v in val.items():
                            if isinstance(v, (str, int, float)):
                                parts.append(f"- {k}: {v}")
                    elif isinstance(val, str):
                        parts.append(f"- {key}: {val}")

        result = "\n".join(parts)
        return result if len(result) > 50 else ""

    async def scrape(self, company: str, **kwargs) -> Optional[str]:
        """
        Scrape NSE for company information

        Args:
            company: Company name to search for

        Returns:
            Scraped text content or None if failed
        """
        try:
            # Use NSE autocomplete API with proper URL encoding
            encoded_company = urllib.parse.quote(company)
            search_url = f"{self.SEARCH_URL}?q={encoded_company}"

            response = requests.get(
                search_url,
                headers=self.DEFAULT_HEADERS,
                timeout=self.DEFAULT_TIMEOUT
            )

            if response.status_code != 200:
                logger.debug(f"NSE returned status {response.status_code} for: {company}")
                self.record_failure()
                return None

            # Parse JSON and convert to meaningful text
            try:
                data = response.json()
                text = self._parse_nse_response(data, company)

                if text:
                    self.record_success()
                    return text
                else:
                    self.record_failure()
                    return None

            except ValueError:
                logger.debug(f"NSE response was not valid JSON for: {company}")
                self.record_failure()
                return None

        except Exception as e:
            logger.warning(f"NSE scrape failed for {company}: {e}")
            self.record_failure()
            return None
