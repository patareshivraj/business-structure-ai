# backend/agents/duckduckgo_agent.py - DuckDuckGo search integration with logging

from duckduckgo_search import DDGS
from typing import List

from utils.logger import get_logger

# Setup logging
logger = get_logger(__name__)


def search_duckduckgo(company: str, max_results: int = 10) -> List[str]:
    """
    Search DuckDuckGo for company information.

    Args:
        company: Company name to search for
        max_results: Maximum number of results to return

    Returns:
        List of text snippets from search results
    """
    try:
        ddgs = DDGS()

        # Search for company information
        results = ddgs.text(
            f"{company} company business segments products services",
            max_results=max_results
        )

        if not results:
            logger.debug(f"No DuckDuckGo results for: {company}")
            return []

        # Extract text content from results
        texts = []
        for r in results:
            title = r.get("title", "")
            body = r.get("body", "")
            if body:
                texts.append(f"{title}: {body}")

        logger.info(f"DuckDuckGo search returned {len(texts)} results for: {company}")
        return texts

    except Exception as e:
        logger.warning(f"DuckDuckGo search failed for {company}: {e}")
        return []


def search_duckduckgo_news(company: str, max_results: int = 5) -> List[str]:
    """
    Search DuckDuckGo news for company.

    Args:
        company: Company name to search for
        max_results: Maximum number of results to return

    Returns:
        List of news snippets
    """
    try:
        ddgs = DDGS()

        # Search news
        results = ddgs.news(
            f"{company} latest news",
            max_results=max_results
        )

        if not results:
            logger.debug(f"No DuckDuckGo news results for: {company}")
            return []

        # Extract text content from news results
        texts = []
        for r in results:
            title = r.get("title", "")
            body = r.get("body", "")
            if body:
                texts.append(f"{title}: {body}")

        logger.info(f"DuckDuckGo news returned {len(texts)} results for: {company}")
        return texts

    except Exception as e:
        logger.warning(f"DuckDuckGo news search failed for {company}: {e}")
        return []


if __name__ == "__main__":
    # Test
    results = search_duckduckgo("infosys")
    print(f"Found {len(results)} results")
    for r in results[:3]:
        print(f"- {r[:100]}...")
