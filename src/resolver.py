"""Resolve a user input (ticker or company name) to a canonical entity record."""
from __future__ import annotations
from dataclasses import dataclass
import yfinance as yf


@dataclass
class Entity:
    ticker: str
    name: str
    sector: str | None
    industry: str | None
    summary: str | None
    website: str | None
    country: str | None


def resolve(query: str) -> Entity:
    query = query.strip().upper()
    t = yf.Ticker(query)
    info = t.info or {}
    if not info.get("symbol"):
        raise ValueError(f"Could not resolve '{query}' to a public ticker.")
    return Entity(
        ticker=info.get("symbol", query),
        name=info.get("longName") or info.get("shortName") or query,
        sector=info.get("sector"),
        industry=info.get("industry"),
        summary=info.get("longBusinessSummary"),
        website=info.get("website"),
        country=info.get("country"),
    )
