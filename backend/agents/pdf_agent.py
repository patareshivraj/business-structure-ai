# backend/agents/pdf_agent.py - PDF extraction with proper SSL handling

import requests
from pypdf import PdfReader
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Default timeout for requests
DEFAULT_TIMEOUT = 15

# Default headers
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/pdf"
}


def is_valid_pdf(response: requests.Response) -> bool:
    """
    Check if response is actually a PDF.
    More lenient checking - some servers don't set correct Content-Type.
    """
    content = response.content
    
    # Must start with PDF signature
    if content.startswith(b"%PDF"):
        return True
    
    # Check if it's HTML (redirect or blocked)
    if content.startswith(b"<"):
        return False
    
    # Check for PDF magic bytes anywhere in content (some servers send partial)
    if b"%PDF" in content[:1000]:
        return True
    
    return False


def extract_pdf_text(url: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """
    Extract text from a PDF URL.
    
    Args:
        url: URL of the PDF to download and extract
        timeout: Request timeout in seconds
        
    Returns:
        Extracted text from PDF, empty string on failure
    """
    try:
        logger.info(f"Downloading PDF: {url}")
        
        response = requests.get(
            url, 
            headers=DEFAULT_HEADERS, 
            timeout=timeout,
            # SSL verification enabled - no verify=False
            # If corporate proxies need certs, use verify='/path/to/cert.pem'
        )
        
        # Check HTTP status
        response.raise_for_status()
        
        if not is_valid_pdf(response):
            logger.warning(f"Not a valid PDF (HTML page or blocked): {url}")
            return ""
        
        pdf_file = io.BytesIO(response.content)
        
        reader = PdfReader(pdf_file)
        
        text = ""
        
        # Limit to first 20 pages to prevent memory issues
        for page in reader.pages[:20]:
            page_text = page.extract_text()
            if page_text:
                text += page_text
        
        # Limit total text length
        logger.info(f"PDF extracted successfully: {len(text)} chars")
        return text[:10000]
        
    except requests.Timeout:
        logger.error(f"PDF download timeout: {url}")
        return ""
    except requests.RequestException as e:
        logger.error(f"PDF download failed: {url} - {e}")
        return ""
    except Exception as e:
        logger.exception(f"PDF extraction error: {url} - {e}")
        return ""


if __name__ == "__main__":
    # Test extraction
    test_url = "https://example.com/sample.pdf"
    result = extract_pdf_text(test_url)
    print(f"Extracted {len(result)} characters")