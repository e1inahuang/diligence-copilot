"""Shared agent infrastructure: schema, prompt scaffold, OpenAI call."""
from __future__ import annotations
import json
import os
from dataclasses import dataclass, field
from openai import OpenAI


@dataclass
class Finding:
    claim: str
    evidence: str
    sentiment: str        # positive | neutral | negative
    confidence: float     # 0..1
    data_quality: str     # high | medium | low
    verified: bool | None = None       # filled by validator
    match_score: float | None = None   # filled by validator


@dataclass
class AgentReport:
    agent: str
    dimension: str
    summary: str
    findings: list[Finding] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)
    overall_confidence: float = 0.0
    corpus: str = ""                    # transient — passed to validator then cleared
    hallucination_rate: float = 0.0     # filled by validator


SYSTEM_TEMPLATE = """You are a {role} working on preliminary investment diligence.
You write tight, evidence-anchored analysis for a private equity investment committee.

Rules:
- Each finding must cite the specific evidence you used (filing section, news headline, metric, etc.).
- Assign a confidence in [0,1] reflecting how well-supported the claim is by the provided context.
- Assign data_quality as high/medium/low based on source freshness and specificity.
- Be willing to say "insufficient evidence" rather than speculate.
- Output strictly valid JSON matching the schema. No prose outside JSON."""

SCHEMA_INSTRUCTION = """Return JSON with this exact shape:
{
  "summary": "2-4 sentence executive synthesis from this agent's perspective.",
  "findings": [
    {
      "claim": "...",
      "evidence": "...",
      "sentiment": "positive|neutral|negative",
      "confidence": 0.0,
      "data_quality": "high|medium|low"
    }
  ],
  "red_flags": ["short red flag string"]
}"""


def _client() -> OpenAI:
    return OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def call_agent(role: str, dimension: str, user_context: str, agent_name: str) -> AgentReport:
    model = os.getenv("OPENAI_MODEL", "gpt-4o")
    system = SYSTEM_TEMPLATE.format(role=role) + "\n\n" + SCHEMA_INSTRUCTION
    resp = _client().chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_context},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"summary": "Agent output was not valid JSON.", "findings": [], "red_flags": []}

    findings = [
        Finding(
            claim=f.get("claim", ""),
            evidence=f.get("evidence", ""),
            sentiment=f.get("sentiment", "neutral"),
            confidence=float(f.get("confidence", 0.0)),
            data_quality=f.get("data_quality", "low"),
        )
        for f in data.get("findings", [])
    ]
    overall = sum(f.confidence for f in findings) / len(findings) if findings else 0.0
    return AgentReport(
        agent=agent_name,
        dimension=dimension,
        summary=data.get("summary", ""),
        findings=findings,
        red_flags=data.get("red_flags", []),
        overall_confidence=round(overall, 3),
        corpus=user_context,
    )
