# backend/agents/research_agent.py - Multi-source company research using ScraperRegistry

import os
import urllib.parse
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
from dotenv import load_dotenv
from typing import List, Optional

from agents.pdf_agent import extract_pdf_text
from agents.duckduckgo_agent import search_duckduckgo
from scrapers.registry import get_registry, register_default_scrapers
from utils.logger import get_logger

# Setup logging
logger = get_logger(__name__)

# Load environment variables
load_dotenv()

# Lazy-initialized client (avoid init with None key)
_client = None


def _get_tavily_client() -> TavilyClient:
    """Get or create Tavily client with lazy initialization"""
    global _client
    if _client is None:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise RuntimeError(
                "TAVILY_API_KEY is not set. Please configure it in your .env file."
            )
        _client = TavilyClient(api_key=api_key)
    return _client

# Default headers for requests
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}


# Initialize scraper registry at module level
_scrapers_initialized = False


def _init_scrapers():
    """Initialize scraper registry (called once)"""
    global _scrapers_initialized
    if not _scrapers_initialized:
        register_default_scrapers()
        _scrapers_initialized = True


# ─── Text Cleaning Functions ─────────────────────────────────────────────────────────

def clean_text(text: Optional[str]) -> str:
    """Clean and validate text content"""
    if not text:
        return ""

    text = text.strip()

    # Remove junk / too short
    if len(text) < 200:
        return ""

    # Limit length to prevent memory issues
    return text[:5000]


# ─── Web Scraping Functions ─────────────────────────────────────────────────────────

def scrape_page(url: str) -> str:
    """Scrape a web page and extract text content"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style"]):
            element.decompose()

        paragraphs = soup.find_all("p")
        text = " ".join([p.get_text() for p in paragraphs])

        return clean_text(text)

    except requests.RequestException as e:
        logger.warning(f"Failed to scrape {url}: {e}")
        return ""


# ─── Annual Report PDF Search ───────────────────────────────────────────────────────

def find_annual_report(company: str) -> Optional[str]:
    """Find annual report PDF URL for a company"""
    try:
        results = _get_tavily_client().search(
            query=f"{company} annual report investor relations pdf",
            max_results=5
        )

        for r in results.get("results", []):
            url = r.get("url", "").lower()

            # Strict filter for actual annual reports
            if (
                ".pdf" in url
                and "annual" in url
                and "report" in url
                and "foundation" not in url
                and "csr" not in url
                and "sustainability" not in url
            ):
                logger.info(f"Found annual report: {url}")
                return url

        return None

    except Exception as e:
        logger.error(f"Annual report search failed for {company}: {e}")
        return None


# ─── Main Research Pipeline ─────────────────────────────────────────────────────────

def research_company(company: str) -> List[str]:
    """
    Research a company using multiple data sources.

    Args:
        company: Company name to research

    Returns:
        List of research text snippets from various sources
    """
    # Initialize scrapers
    _init_scrapers()

    logger.info(f"Researching company: {company}")

    research_text = []
    visited_urls = set()

    # URL-safe company name for API calls
    encoded_company = urllib.parse.quote(company)

    # ─── 1️⃣ Tavily Search ─────────────────────────────────────────────────────────
    try:
        results = _get_tavily_client().search(
            query=f"{company} India company business segments products services technologies",
            max_results=6
        )

        for r in results.get("results", []):
            content = clean_text(r.get("content", ""))
            url = r.get("url", "")

            if content:
                research_text.append(content)

            if url and url not in visited_urls:
                visited_urls.add(url)

                page_text = scrape_page(url)
                if page_text:
                    research_text.append(page_text)

    except Exception as e:
        logger.error(f"Tavily search failed for {company}: {e}")

    # ─── 2️⃣ Registry-Based Scrapers (Wikipedia, MoneyControl, NSE, Web) ──────────
    registry = get_registry()
    for name in registry.list_scrapers(enabled_only=True):
        scraper = registry.get(name)
        if scraper:
            try:
                # Registry scrapers are async but we call them from sync context
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None

                if loop and loop.is_running():
                    # We're inside an event loop — create a new thread
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        content = pool.submit(
                            asyncio.run, scraper.scrape(company)
                        ).result(timeout=15)
                else:
                    content = asyncio.run(scraper.scrape(company))

                if content:
                    research_text.append(content)
                    logger.info(f"Scraper '{name}' returned {len(content)} chars")
            except Exception as e:
                logger.warning(f"Scraper '{name}' failed: {e}")

    # ─── 3️⃣ DuckDuckGo Search ─────────────────────────────────────────────────────
    logger.info("Running DuckDuckGo search...")
    ddg_texts = search_duckduckgo(company, max_results=8)
    for text in ddg_texts:
        if text and len(text) > 50:
            research_text.append(text[:2000])

    # ─── 4️⃣ Annual Report (PDF) ───────────────────────────────────────────────────
    pdf_url = find_annual_report(company)
    if pdf_url:
        pdf_text = extract_pdf_text(pdf_url)
        if pdf_text:
            research_text.append(clean_text(pdf_text))

    # ─── Final Cleanup ─────────────────────────────────────────────────────────────
    # Remove duplicates while preserving order
    research_text = list(dict.fromkeys(research_text))

    logger.info(f"Research complete: {len(research_text)} sources collected")

    return research_text