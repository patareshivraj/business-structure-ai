# backend/agents/research_agent.py - Multi-source company research using ScraperRegistry

import os
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
from dotenv import load_dotenv
import logging
from typing import List, Optional

from agents.pdf_agent import extract_pdf_text
from agents.duckduckgo_agent import search_duckduckgo
from scrapers.registry import get_registry, register_default_scrapers
from utils.rate_limiter import check_api_call_limit, increment_api_calls

# Setup logging
logger = logging.getLogger(__name__)

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
    if not check_api_call_limit():
        logger.warning(f"API call limit reached, skipping: {url}")
        return ""
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Remove script and style elements
        for element in soup(["script", "style"]):
            element.decompose()
        
        paragraphs = soup.find_all("p")
        text = " ".join([p.get_text() for p in paragraphs])
        
        increment_api_calls()
        return clean_text(text)
        
    except requests.RequestException as e:
        logger.warning(f"Failed to scrape {url}: {e}")
        return ""


# ─── Wikipedia Scraping ─────────────────────────────────────────────────────────────

def scrape_wikipedia(company: str) -> str:
    """Scrape Wikipedia summary for a company"""
    if not check_api_call_limit():
        logger.warning("API call limit reached, skipping Wikipedia")
        return ""
    
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{company}"
        
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code != 200:
            return ""
        
        data = response.json()
        increment_api_calls()
        return clean_text(data.get("extract", ""))
        
    except requests.RequestException as e:
        logger.warning(f"Failed to scrape Wikipedia for {company}: {e}")
        return ""


# ─── India-Specific Scraping ───────────────────────────────────────────────────────

def scrape_moneycontrol(company: str) -> str:
    """Scrape MoneyControl (India) for company information"""
    if not check_api_call_limit():
        logger.warning("API call limit reached, skipping MoneyControl")
        return ""
    
    try:
        search_url = f"https://www.moneycontrol.com/stocks/company_info/search_result.php?query={company}"
        
        response = requests.get(search_url, headers=HEADERS, timeout=10)
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        link = soup.find("a")
        
        if link:
            url = link["href"]
            increment_api_calls()
            return scrape_page(url)
        
        return ""
        
    except requests.RequestException as e:
        logger.warning(f"Failed to scrape MoneyControl for {company}: {e}")
        return ""


def scrape_nse(company: str) -> str:
    """Scrape NSE (India) for company information"""
    if not check_api_call_limit():
        logger.warning("API call limit reached, skipping NSE")
        return ""
    
    try:
        url = f"https://www.nseindia.com/api/search/autocomplete?q={company}"
        
        response = requests.get(url, headers=HEADERS, timeout=10)
        increment_api_calls()
        
        return clean_text(response.text)
        
    except requests.RequestException as e:
        logger.warning(f"Failed to scrape NSE for {company}: {e}")
        return ""


# ─── Annual Report PDF Search ───────────────────────────────────────────────────────

def find_annual_report(company: str) -> Optional[str]:
    """Find annual report PDF URL for a company"""
    if not check_api_call_limit():
        logger.warning("API call limit reached, skipping annual report search")
        return None
    
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
                increment_api_calls()
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
    Uses ScraperRegistry for consistent scraper management.
    
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
    
    # ─── 1️⃣ Tavily Search ─────────────────────────────────────────────────────────
    try:
        results = _get_tavily_client().search(
            query=f"{company} India company business segments products services technologies",
            max_results=6
        )
        
        for r in results.get("results", []):
            if not check_api_call_limit():
                logger.warning("API call limit reached during Tavily search")
                break
            
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
    
    # ─── 2️⃣ Wikipedia ───────────────────────────────────────────────────────────────
    wiki_text = scrape_wikipedia(company)
    if wiki_text:
        research_text.append(wiki_text)
    
    # ─── 3️⃣ MoneyControl (India) ─────────────────────────────────────────────────
    mc_text = scrape_moneycontrol(company)
    if mc_text:
        research_text.append(mc_text)
    
    # ─── 4️⃣ NSE (India) ───────────────────────────────────────────────────────────
    nse_text = scrape_nse(company)
    if nse_text:
        research_text.append(nse_text)
    
    # ─── 5️⃣ DuckDuckGo Search ─────────────────────────────────────────────────────
    logger.info("Running DuckDuckGo search...")
    ddg_texts = search_duckduckgo(company, max_results=8)
    for text in ddg_texts:
        if text and len(text) > 50:
            research_text.append(text[:2000])
    
    # ─── 6️⃣ Annual Report (PDF) ───────────────────────────────────────────────────
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


# ─── Registry-based Alternative (for future use) ───────────────────────────────────

def research_with_registry(company: str) -> List[str]:
    """
    Alternative research using ScraperRegistry (when ready).
    This is a placeholder for future migration.
    """
    _init_scrapers()
    registry = get_registry()
    
    logger.info(f"Researching {company} via scraper registry")
    
    results = []
    
    for name in registry.list_scrapers(enabled_only=True):
        scraper = registry.get(name)
        if scraper:
            try:
                content = scraper.scrape(company)
                if content:
                    results.append(content)
            except Exception as e:
                logger.warning(f"Scraper {name} failed: {e}")
    
    return results