"""Consensus + verdict logic across agent reports."""
from __future__ import annotations
from dataclasses import dataclass
from .agents.base import AgentReport


@dataclass
class Consensus:
    conviction_score: float        # 0..1
    verdict: str                   # PURSUE | INVESTIGATE | PASS
    overall_confidence: float      # mean agent confidence
    sentiment_balance: dict
    top_red_flags: list[str]


_SENTIMENT_WEIGHT = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}
_AGENT_WEIGHTS = {
    "financial": 0.35,
    "market": 0.25,
    "risk": 0.30,
    "news": 0.10,
}


def consense(reports: list[AgentReport]) -> Consensus:
    score = 0.0
    weight_used = 0.0
    sentiment = {"positive": 0, "neutral": 0, "negative": 0}

    for r in reports:
        if not r.findings:
            continue
        agent_dir = 0.0
        for f in r.findings:
            sentiment[f.sentiment] = sentiment.get(f.sentiment, 0) + 1
            agent_dir += _SENTIMENT_WEIGHT.get(f.sentiment, 0) * f.confidence
        agent_dir /= len(r.findings)
        w = _AGENT_WEIGHTS.get(r.agent, 0.1)
        score += agent_dir * w
        weight_used += w

    if weight_used > 0:
        score /= weight_used
    conviction = round((score + 1) / 2, 3)

    if conviction >= 0.6:
        verdict = "PURSUE"
    elif conviction >= 0.45:
        verdict = "INVESTIGATE"
    else:
        verdict = "PASS"

    overall_conf = (
        round(sum(r.overall_confidence for r in reports) / len(reports), 3)
        if reports else 0.0
    )

    red_flags: list[str] = []
    for r in reports:
        red_flags.extend(r.red_flags)

    return Consensus(
        conviction_score=conviction,
        verdict=verdict,
        overall_confidence=overall_conf,
        sentiment_balance=sentiment,
        top_red_flags=red_flags[:10],
    )
