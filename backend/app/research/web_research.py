import logging
from typing import List, Dict, Any, Optional
import httpx
from app.core.config import settings
from app.research.query_generator import generate_research_queries
from app.research.page_extractor import fetch_page_html, clean_and_extract_page
from app.research.source_evaluator import evaluate_and_rank_source

logger = logging.getLogger(__name__)

# Primary authoritative fallback leads for reliable local verification
CURATED_RESEARCH_LEADS = {
    "http": [
        {
            "url": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods",
            "title": "HTTP request methods - HTTP | MDN",
            "publisher": "MDN Web Docs",
        },
        {
            "url": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status",
            "title": "HTTP response status codes - HTTP | MDN",
            "publisher": "MDN Web Docs",
        },
        {
            "url": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview",
            "title": "An overview of HTTP - HTTP | MDN",
            "publisher": "MDN Web Docs",
        },
        {
            "url": "https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol",
            "title": "Hypertext Transfer Protocol - Wikipedia",
            "publisher": "Wikipedia",
        }
    ],
    "database": [
        {
            "url": "https://en.wikipedia.org/wiki/Database_normalization",
            "title": "Database normalization - Wikipedia",
            "publisher": "Wikipedia",
        },
        {
            "url": "https://en.wikipedia.org/wiki/First_normal_form",
            "title": "First normal form - Wikipedia",
            "publisher": "Wikipedia",
        },
        {
            "url": "https://en.wikipedia.org/wiki/Second_normal_form",
            "title": "Second normal form - Wikipedia",
            "publisher": "Wikipedia",
        },
        {
            "url": "https://en.wikipedia.org/wiki/Third_normal_form",
            "title": "Third normal form - Wikipedia",
            "publisher": "Wikipedia",
        }
    ]
}

def perform_web_research(title: str, learning_objective: str) -> List[Dict[str, Any]]:
    """
    Executes web research using Tavily Search API if configured,
    or fetches and extracts authoritative primary sources matching the query concepts.
    Returns evaluated, ranked source dictionaries with extracted chunks.
    """
    queries = generate_research_queries(title, learning_objective)
    logger.info(f"Generated {len(queries)} search queries for '{title}': {queries}")

    candidate_urls: List[Dict[str, Any]] = []

    # 1. Check Tavily Search API
    if settings.TAVILY_API_KEY:
        candidate_urls = _search_with_tavily(queries, settings.TAVILY_API_KEY)

    # 2. If Tavily returned no results or is unconfigured, use domain leads
    if not candidate_urls:
        logger.info("Using authoritative web leads for retrieval.")
        title_lower = title.lower() + " " + learning_objective.lower()
        if "http" in title_lower or "get" in title_lower:
            candidate_urls = CURATED_RESEARCH_LEADS["http"]
        elif "normal" in title_lower or "database" in title_lower:
            candidate_urls = CURATED_RESEARCH_LEADS["database"]
        else:
            # General fallback to wikipedia & MDN
            candidate_urls = [
                {"url": "https://en.wikipedia.org/wiki/" + title.replace(" ", "_"), "title": title, "publisher": "Wikipedia"},
                {"url": "https://developer.mozilla.org/en-US/", "title": "MDN Documentation", "publisher": "MDN Web Docs"}
            ]

    # 3. Retrieve, Extract, and Evaluate each source
    collected_sources: List[Dict[str, Any]] = []

    for candidate in candidate_urls:
        url = candidate["url"]
        logger.info(f"Retrieving and extracting webpage: {url}")
        html = fetch_page_html(url)
        
        if not html:
            # Handle inaccessible pages gracefully (mark as skipped / failed without aborting job)
            collected_sources.append({
                "source_type": "website",
                "title": candidate.get("title", url),
                "author_publisher": candidate.get("publisher", "Web Source"),
                "url_or_identifier": url,
                "published_date": None,
                "relevance_score": 0.0,
                "status": "failed",
                "source_metadata": {"error": "Page unreachable or non-200 HTTP response"},
                "chunks": []
            })
            continue

        extracted = clean_and_extract_page(html, url)
        evaluation = evaluate_and_rank_source(
            url=url,
            title=extracted["title"] or candidate.get("title", ""),
            full_text=extracted["full_text"],
            learning_objective=learning_objective
        )

        source_dict = {
            "source_type": "website",
            "title": extracted["title"] or candidate.get("title", url),
            "author_publisher": extracted["publisher"] or candidate.get("publisher", "Web Source"),
            "url_or_identifier": url,
            "published_date": extracted["published_date"],
            "relevance_score": evaluation["relevance_score"],
            "status": "active",
            "source_metadata": {
                "evaluation": evaluation["evaluation_notes"],
                "content_preview": extracted["full_text"][:300] + "..."
            },
            "chunks": [
                {
                    "chunk_text": chunk,
                    "section_heading": f"Excerpt {i+1}",
                    "page_number": None
                }
                for i, chunk in enumerate(extracted["chunks"])
            ]
        }
        collected_sources.append(source_dict)

    # Sort sources by relevance score descending
    collected_sources.sort(key=lambda s: s["relevance_score"], reverse=True)
    return collected_sources

def _search_with_tavily(queries: List[str], api_key: str) -> List[Dict[str, Any]]:
    results = []
    seen_urls = set()
    try:
        with httpx.Client(timeout=10.0) as client:
            for q in queries[:2]:  # Limit queries to preserve quota
                resp = client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": api_key,
                        "query": q,
                        "search_depth": "advanced",
                        "include_answer": False,
                        "max_results": 4
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for r in data.get("results", []):
                        url = r.get("url")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            results.append({
                                "url": url,
                                "title": r.get("title", ""),
                                "publisher": r.get("domain", "")
                            })
    except Exception as e:
        logger.warning(f"Tavily search API error: {e}")
    return results
