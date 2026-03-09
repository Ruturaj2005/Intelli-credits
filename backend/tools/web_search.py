"""
SurfApi Web Search wrapper for the Research Agent.
Executes ordered searches and returns aggregated results.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
import httpx


def get_surfapi_client() -> str:
    """Get SurfApi API key from environment."""
    api_key = os.getenv("SURFAPI_KEY", "")
    if not api_key:
        raise ValueError("SURFAPI_KEY environment variable is not set.")
    return api_key


def search_web(
    query: str,
    max_results: int = 5,
    search_depth: str = "advanced",
    include_domains: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Execute a single SurfApi web search.

    Returns:
        dict with keys: query, results (list of {title, url, content, score}), answer
    """
    try:
        api_key = get_surfapi_client()
        
        # SurfApi endpoint
        url = "https://api.surfapi.com/v1/search"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "query": query,
            "num_results": max_results,
            "search_type": search_depth,
        }
        
        if include_domains:
            payload["include_domains"] = include_domains

        response = httpx.post(url, json=payload, headers=headers, timeout=30.0)
        response.raise_for_status()
        
        data = response.json()
        
        # Transform SurfApi response to match expected format
        results = []
        for item in data.get("results", [])[:max_results]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("snippet", "") or item.get("content", ""),
                "score": item.get("relevance_score", 0.0),
            })
        
        return {
            "query": query,
            "results": results,
            "answer": data.get("summary", "") or data.get("answer", ""),
            "error": None,
        }
    except Exception as exc:
        return {
            "query": query,
            "results": [],
            "answer": "",
            "error": str(exc),
        }


# ─── Ordered Research Searches ────────────────────────────────────────────────

INDIAN_FINANCIAL_DOMAINS = [
    "economictimes.indiatimes.com",
    "livemint.com",
    "business-standard.com",
    "thehindubusinessline.com",
    "financialexpress.com",
    "mca.gov.in",
    "rbi.org.in",
    "sebi.gov.in",
    "nclt.gov.in",
    "bseindia.com",
    "nseindia.com",
    "moneycontrol.com",
]


def run_due_diligence_searches(
    company_name: str,
    sector: str,
    promoter_names: List[str],
) -> List[Dict[str, Any]]:
    """
    Execute the 5 mandated due diligence searches for the Research Agent.
    Returns a list of search result payloads.
    """
    promoter_str = promoter_names[0] if promoter_names else company_name

    queries = [
        f'"{company_name}" fraud OR default OR NPA OR NCLT India',
        f'"{promoter_str}" court case OR ED OR CBI OR money laundering India',
        f'"{company_name}" MCA filing struck off OR winding up',
        f"{sector} RBI regulation OR SEBI notice 2024 2025",
        f'"{company_name}" latest news 2024 2025',
    ]

    search_labels = [
        "Fraud/NPA/Default Check",
        "Promoter Background Check",
        "MCA/Corporate Status Check",
        "Sector Regulatory Outlook",
        "Recent News",
    ]

    results: List[Dict[str, Any]] = []
    for label, query in zip(search_labels, queries):
        result = search_web(
            query=query,
            max_results=5,
            search_depth="advanced",
            include_domains=INDIAN_FINANCIAL_DOMAINS,
        )
        result["label"] = label
        results.append(result)

    return results


def format_search_results_for_llm(search_results: List[Dict[str, Any]]) -> str:
    """
    Format all search results into a readable string for the LLM synthesis prompt.
    """
    parts: List[str] = []
    for i, sr in enumerate(search_results, 1):
        label = sr.get("label", f"Search {i}")
        query = sr.get("query", "")
        answer = sr.get("answer", "")
        error = sr.get("error")

        header = f"=== SEARCH {i}: {label} ===\nQuery: {query}"
        if error:
            parts.append(f"{header}\nERROR: {error}\n")
            continue

        body_parts = []
        if answer:
            body_parts.append(f"Summary: {answer}")

        for j, result in enumerate(sr.get("results", [])[:5], 1):
            title = result.get("title", "No title")
            url = result.get("url", "")
            content = result.get("content", "")[:600]  # Cap content length
            body_parts.append(f"  [{j}] {title}\n  URL: {url}\n  {content}")

        if not body_parts:
            body_parts.append("No results found.")

        parts.append(f"{header}\n" + "\n".join(body_parts))

    return "\n\n".join(parts)
