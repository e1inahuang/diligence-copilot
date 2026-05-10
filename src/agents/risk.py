"""Risk analyst — reads filings risk-factors and litigation search."""
from __future__ import annotations
from .base import AgentReport, call_agent
from ..sources.filings import FilingSummary
from ..sources.news import NewsItem


def run(company: str, filings: list[FilingSummary], litigation: list[NewsItem]) -> AgentReport:
    rf_blob = "\n\n".join(
        f"[{f.form} {f.filed_date}] {f.risk_factors_excerpt[:3500]}"
        for f in filings if f.risk_factors_excerpt
    ) or "No risk factor excerpts available."

    lit_blob = "\n\n".join(
        f"- {n.title}\n  {n.content[:400]}"
        for n in litigation[:6]
    ) or "No litigation results returned."

    ctx = f"""Company: {company}

RISK FACTORS (from latest filings):
{rf_blob[:6000]}

LITIGATION / CONTROVERSY SEARCH RESULTS:
{lit_blob}

Task: Identify the highest-impact risks an IC should weigh. Surface concrete litigation, regulatory, or compliance exposures rather than boilerplate. Distinguish material risks from standard disclosure language."""

    return call_agent(
        role="risk and compliance analyst",
        dimension="risk_and_compliance",
        user_context=ctx,
        agent_name="risk",
    )
