"""News/sentiment analyst — synthesizes recent narrative."""
from __future__ import annotations
from .base import AgentReport, call_agent
from ..sources.news import NewsItem


def run(company: str, news: list[NewsItem]) -> AgentReport:
    blob = "\n\n".join(
        f"- {n.title} ({n.published or 'n.d.'}) [{n.url}]\n  {n.content[:500]}"
        for n in news[:10]
    ) or "No news items."

    ctx = f"""Company: {company}

RECENT NEWS (90 days):
{blob}

Task: Synthesize the dominant narrative in recent press coverage. Are sentiment and momentum positive, neutral, or deteriorating? Surface event-driven items (management change, guidance cut, major contract win/loss) that materially shift the thesis."""

    return call_agent(
        role="financial press and sentiment analyst",
        dimension="narrative_and_sentiment",
        user_context=ctx,
        agent_name="news",
    )
