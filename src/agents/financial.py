"""Financial analyst agent."""
from __future__ import annotations
from .base import AgentReport, call_agent
from ..sources.market import MarketSnapshot
from ..sources.filings import FilingSummary


def _fmt(v, pct=False, money=False):
    if v is None:
        return "n/a"
    if pct:
        return f"{v*100:.1f}%"
    if money and abs(v) >= 1e9:
        return f"${v/1e9:.2f}B"
    if money and abs(v) >= 1e6:
        return f"${v/1e6:.2f}M"
    return f"{v}"


def _format_market(m: MarketSnapshot) -> str:
    return (
        f"Price: {_fmt(m.price)} | Market cap: {_fmt(m.market_cap, money=True)}\n"
        f"TTM revenue: {_fmt(m.revenue_ttm, money=True)} | YoY rev growth: {_fmt(m.revenue_growth, pct=True)}\n"
        f"Profit margin: {_fmt(m.profit_margin, pct=True)} | ROE: {_fmt(m.return_on_equity, pct=True)}\n"
        f"Debt/Equity: {_fmt(m.debt_to_equity)} | FCF: {_fmt(m.free_cash_flow, money=True)}\n"
        f"Trailing P/E: {_fmt(m.pe_ratio)} | Forward P/E: {_fmt(m.forward_pe)} | Beta: {_fmt(m.beta)}\n"
        f"1Y return: {_fmt(m.one_year_return, pct=True)} | "
        f"52W range: {_fmt(m.fifty_two_week_low)}-{_fmt(m.fifty_two_week_high)}"
    )


def run(company: str, market: MarketSnapshot, filings: list[FilingSummary]) -> AgentReport:
    mdna_blob = "\n\n".join(
        f"[{f.form} {f.filed_date}] {f.mdna_excerpt[:3000]}"
        for f in filings if f.mdna_excerpt
    ) or "No MD&A excerpts available."

    ctx = f"""Company: {company}

MARKET METRICS:
{_format_market(market)}

MD&A EXCERPTS (most recent filings):
{mdna_blob[:8000]}

Task: Evaluate financial health, growth quality, margin trajectory, capital structure, and valuation reasonableness. Identify deteriorating trends and strengths."""

    return call_agent(
        role="senior financial analyst",
        dimension="financial_health",
        user_context=ctx,
        agent_name="financial",
    )
