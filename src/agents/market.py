"""Market analyst — competitive positioning and demand signals."""
from __future__ import annotations
from .base import AgentReport, call_agent
from ..sources.news import NewsItem


def run(company: str, sector: str | None, industry: str | None, news: list[NewsItem]) -> AgentReport:
    news_blob = "\n\n".join(
        f"- {n.title} ({n.published or 'n.d.'})\n  {n.content[:400]}"
        for n in news[:8]
    ) or "No recent news returned."

    ctx = f"""Company: {company}
Sector: {sector or 'unknown'} | Industry: {industry or 'unknown'}

RECENT NEWS COVERAGE:
{news_blob}

Task: Assess competitive position, end-market demand trajectory, pricing power signals, and notable strategic moves (M&A, product launches, share gains/losses). Flag signs of share erosion or category headwinds."""

    return call_agent(
        role="market and competitive intelligence analyst",
        dimension="market_position",
        user_context=ctx,
        agent_name="market",
    )
