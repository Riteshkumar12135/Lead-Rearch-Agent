"""Optional web search layer for signals a homepage won't have:
funding rounds, headcount estimates, recent news, etc.

Uses Tavily (https://tavily.com) since it's built for LLM agents and has a
free tier, but this is intentionally a thin wrapper — swap in Serper,
SerpAPI, Bing, or anything else without touching the rest of the agent.
If no TAVILY_API_KEY is set, these functions degrade gracefully to
returning empty results rather than raising.
"""
from typing import List, Optional

from . import config


def _tavily_client():
    if not config.TAVILY_API_KEY:
        return None
    try:
        from tavily import TavilyClient
        return TavilyClient(api_key=config.TAVILY_API_KEY)
    except ImportError:
        return None


def web_search(query: str, max_results: int = 5) -> List[dict]:
    """Return a list of {title, url, content} dicts, or [] if search unavailable."""
    client = _tavily_client()
    if client is None:
        return []
    try:
        result = client.search(query=query, max_results=max_results)
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", ""),
            }
            for r in result.get("results", [])
        ]
    except Exception:
        return []


def find_company_domain(company_name: str) -> Optional[str]:
    """Best-effort resolution of a bare company name to its homepage domain."""
    results = web_search(f"{company_name} official website")
    if results:
        return results[0]["url"]
    return None


def find_recent_news(company_name: str) -> List[dict]:
    """Recent news/funding signals, used to sharpen pain-point guesses."""
    return web_search(f"{company_name} funding OR news OR hiring 2026", max_results=3)
