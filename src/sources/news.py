"""Recent news + litigation/controversy search via Tavily."""
from __future__ import annotations
import os
from dataclasses import dataclass
from tavily import TavilyClient


@dataclass
class NewsItem:
    title: str
    url: str
    content: str
    published: str | None = None


def _client() -> TavilyClient:
    key = os.getenv("TAVILY_API_KEY")
    if not key:
        raise RuntimeError("TAVILY_API_KEY missing")
    return TavilyClient(api_key=key)


def search_news(company: str, max_results: int = 6) -> list[NewsItem]:
    try:
        c = _client()
        r = c.search(
            query=f"{company} recent news earnings strategy",
            topic="news",
            max_results=max_results,
            days=90,
        )
        return [
            NewsItem(
                title=x.get("title", ""),
                url=x.get("url", ""),
                content=x.get("content", ""),
                published=x.get("published_date"),
            )
            for x in r.get("results", [])
        ]
    except Exception:
        return []


def search_litigation(company: str, max_results: int = 5) -> list[NewsItem]:
    try:
        c = _client()
        r = c.search(
            query=f"{company} lawsuit litigation investigation SEC fine settlement controversy",
            max_results=max_results,
        )
        return [
            NewsItem(
                title=x.get("title", ""),
                url=x.get("url", ""),
                content=x.get("content", ""),
            )
            for x in r.get("results", [])
        ]
    except Exception:
        return []
