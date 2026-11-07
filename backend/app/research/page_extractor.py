import re
import logging
from typing import Dict, Any, List, Optional
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 AI-Lesson-Creator/1.0"

def fetch_page_html(url: str, timeout_seconds: float = 8.0) -> Optional[str]:
    """
    Safely retrieves page HTML with timeout and User-Agent.
    Returns None if the page is unreachable or returns HTTP errors.
    """
    try:
        headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
        with httpx.Client(timeout=timeout_seconds, follow_redirects=True, verify=False) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", "").lower():
                return resp.text
            logger.warning(f"Failed to fetch {url}: HTTP {resp.status_code}")
            return None
    except Exception as e:
        logger.warning(f"Exception fetching {url}: {e}")
        return None

def clean_and_extract_page(html: str, url: str) -> Dict[str, Any]:
    """
    Parses HTML, removes boilerplate, and extracts title, publisher, date,
    clean text, and logical text chunks.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove irrelevant tags
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "noscript", "svg", "iframe", "button"]):
        tag.decompose()

    # Extract Title
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    elif soup.find("meta", property="og:title"):
        title = soup.find("meta", property="og:title").get("content", "").strip()

    # Extract Publisher / Author
    publisher = ""
    meta_publisher = soup.find("meta", property="og:site_name") or soup.find("meta", attrs={"name": "publisher"})
    if meta_publisher and meta_publisher.get("content"):
        publisher = meta_publisher.get("content").strip()
    else:
        # Fallback to domain name
        domain_match = re.search(r"https?://(?:www\.)?([^/]+)", url)
        publisher = domain_match.group(1) if domain_match else "Web Source"

    # Extract Published / Updated Date
    pub_date = None
    meta_date = (
        soup.find("meta", property="article:published_time")
        or soup.find("meta", property="article:modified_time")
        or soup.find("meta", attrs={"name": "date"})
    )
    if meta_date and meta_date.get("content"):
        pub_date = meta_date.get("content").strip()[:10]

    # Extract Text from headings and paragraphs
    paragraphs = []
    for p in soup.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        txt = p.get_text(separator=" ", strip=True)
        # Filter very short fragments or copyright disclaimers
        if len(txt) > 30 and not re.search(r"cookie|privacy policy|terms of service|all rights reserved", txt, re.I):
            paragraphs.append(txt)

    full_text = "\n\n".join(paragraphs)

    # Chunk into digestible 400-800 character pieces preserving paragraph blocks
    chunks: List[str] = []
    current_chunk = []
    current_length = 0

    for p in paragraphs:
        if current_length + len(p) > 750 and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = [p]
            current_length = len(p)
        else:
            current_chunk.append(p)
            current_length += len(p)

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return {
        "url": url,
        "title": title or "Untitled Resource",
        "publisher": publisher,
        "published_date": pub_date,
        "full_text": full_text[:12000],  # Bound text size
        "chunks": chunks[:10],  # Top 10 most relevant chunks
    }
