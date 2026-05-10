"""IC-memo style markdown report."""
from __future__ import annotations
from datetime import datetime
from .orchestrator import DiligenceBundle


def _fmt_money(v):
    if v is None:
        return "n/a"
    if abs(v) >= 1e9:
        return f"${v/1e9:.2f}B"
    if abs(v) >= 1e6:
        return f"${v/1e6:.2f}M"
    return f"${v:,.0f}"


def _fmt_pct(v):
    return f"{v*100:.1f}%" if v is not None else "n/a"


def render(bundle: DiligenceBundle) -> str:
    e = bundle.entity
    m = bundle.market
    c = bundle.consensus
    today = datetime.utcnow().strftime("%Y-%m-%d")

    md = [
        f"# Preliminary Diligence Memo — {e.name} ({e.ticker})",
        f"_Generated {today} · diligence-copilot_",
        "",
        f"**Verdict:** `{c.verdict}`  ·  **Conviction score:** `{c.conviction_score:.2f}` / 1.00  ·  **Mean agent confidence:** `{c.overall_confidence:.2f}`",
        "",
        "> Automated draft for analyst review. Confidence scores reflect evidence support, not investment merit.",
        "",
        "## 1. Company Snapshot",
        f"- **Sector / Industry:** {e.sector or 'n/a'} / {e.industry or 'n/a'}",
        f"- **HQ country:** {e.country or 'n/a'}",
        f"- **Website:** {e.website or 'n/a'}",
        "",
        f"{(e.summary or '')[:800]}",
        "",
        "## 2. Market Snapshot",
        "| Metric | Value |",
        "|---|---|",
        f"| Price | {m.price if m.price is not None else 'n/a'} |",
        f"| Market cap | {_fmt_money(m.market_cap)} |",
        f"| TTM revenue | {_fmt_money(m.revenue_ttm)} |",
        f"| Revenue growth (YoY) | {_fmt_pct(m.revenue_growth)} |",
        f"| Profit margin | {_fmt_pct(m.profit_margin)} |",
        f"| Return on equity | {_fmt_pct(m.return_on_equity)} |",
        f"| Debt / Equity | {m.debt_to_equity if m.debt_to_equity is not None else 'n/a'} |",
        f"| Free cash flow | {_fmt_money(m.free_cash_flow)} |",
        f"| Trailing P/E | {m.pe_ratio if m.pe_ratio is not None else 'n/a'} |",
        f"| Forward P/E | {m.forward_pe if m.forward_pe is not None else 'n/a'} |",
        f"| Beta | {m.beta if m.beta is not None else 'n/a'} |",
        f"| 1Y total return | {_fmt_pct(m.one_year_return)} |",
        "",
        "## 3. Multi-Agent Findings",
    ]

    for r in bundle.reports:
        md.append(f"### {r.agent.title()} Analyst  · _{r.dimension}_")
        md.append(f"**Summary.** {r.summary}")
        md.append(
            f"**Agent confidence:** {r.overall_confidence:.2f}  ·  "
            f"**Unverified findings:** {int(r.hallucination_rate * 100)}%"
        )
        md.append("")
        if r.findings:
            md.append("| Claim | Evidence | Sentiment | Conf. | Data | Evid. match |")
            md.append("|---|---|---|---|---|---|")
            for f in r.findings:
                claim = f.claim.replace("|", "\\|")[:220]
                ev = f.evidence.replace("|", "\\|")[:160]
                if f.match_score is None:
                    match_cell = "n/a"
                else:
                    pct = int(f.match_score * 100)
                    match_cell = f"{pct}%" if f.verified else f"{pct}% (unverified)"
                md.append(
                    f"| {claim} | {ev} | {f.sentiment} | {f.confidence:.2f} | "
                    f"{f.data_quality} | {match_cell} |"
                )
        if r.red_flags:
            md.append("")
            md.append("**Red flags raised:**")
            for rf in r.red_flags:
                md.append(f"- {rf}")
        md.append("")

    total_findings = sum(len(r.findings) for r in bundle.reports)
    unverified = sum(
        1 for r in bundle.reports for f in r.findings
        if f.verified is False
    )
    halluc_rate = (unverified / total_findings) if total_findings else 0.0

    md += [
        "## 4. Consensus & Red Flags",
        f"- **Verdict:** {c.verdict}",
        f"- **Conviction score:** {c.conviction_score:.2f}",
        f"- **Sentiment balance:** {c.sentiment_balance}",
        f"- **Overall unverified findings:** {unverified}/{total_findings} ({halluc_rate*100:.0f}%)",
        "",
        "**Top red flags across agents:**",
    ]
    if c.top_red_flags:
        for rf in c.top_red_flags:
            md.append(f"- {rf}")
    else:
        md.append("- _None surfaced._")

    md += [
        "",
        "## 5. Sources Used",
        "- Market data: Yahoo Finance",
        "- Filings: SEC EDGAR (latest 10-K and 10-Q risk factors / MD&A excerpts)",
        "- News & litigation search: Tavily web search",
        "",
        "## 6. Methodology & Caveats",
        "- Each agent runs independently against a different evidence slice; outputs are merged via weighted sentiment × confidence consensus.",
        "- Agent weights (v1): financial 0.35, risk 0.30, market 0.25, news 0.10.",
        "- Each finding is post-hoc verified by substring-matching distinctive tokens (numbers, named entities, filing labels) against the source corpus handed to that agent. Findings below a 40% token-match threshold are flagged `unverified` — treat their evidence with skepticism.",
        "- Verdicts are heuristic, not investment advice. All findings require analyst verification.",
        "",
    ]
    return "\n".join(md)
