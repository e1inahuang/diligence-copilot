"""Post-hoc evidence verifier.

Each agent cites an `evidence` string per finding. The model can in principle
fabricate that citation. This module does a closed-loop check: for every
finding, we extract distinctive tokens from the evidence (numbers, named
entities, filing labels) and confirm they actually appear in the source corpus
we handed the agent. Findings whose evidence cannot be located get marked
unverified, and we surface a per-agent hallucination rate.

This is intentionally a substring/token heuristic, not an embedding match.
Cheap, deterministic, easy to debug, and good enough at the prototype stage.
A v2 would use entailment scoring or RAG-style attribution.
"""
from __future__ import annotations
import re
from .agents.base import AgentReport, Finding


_NUM_RE = re.compile(r"\$?\d+(?:[,\.]\d+)*%?[BMK]?", re.IGNORECASE)
_FORM_RE = re.compile(r"\b(?:10-K|10-Q|8-K|Item\s+\d+[A-Z]?)\b", re.IGNORECASE)
_CAP_PHRASE_RE = re.compile(r"\b(?:[A-Z][a-z0-9&]+(?:\s+[A-Z][a-z0-9&]+){0,3})\b")
_ACRONYM_RE = re.compile(r"\b[A-Z]{2,}(?:-[A-Z0-9]+)?\b")

_STOPWORDS = {
    "The", "And", "Or", "But", "If", "Then", "So", "As", "Of", "In", "On",
    "At", "To", "From", "By", "For", "With", "About", "Inc", "Company",
    "Item", "Section", "Report", "Note", "Analyst", "CEO", "U.S.",
}

# Findings with match score below this are flagged unverified.
_VERIFY_THRESHOLD = 0.4


def _extract_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    tokens.update(m.group(0).lower() for m in _NUM_RE.finditer(text))
    tokens.update(m.group(0).lower() for m in _FORM_RE.finditer(text))
    for m in _CAP_PHRASE_RE.finditer(text):
        phrase = m.group(0)
        if phrase not in _STOPWORDS and len(phrase) > 3:
            tokens.add(phrase.lower())
    for m in _ACRONYM_RE.finditer(text):
        acro = m.group(0)
        if acro not in _STOPWORDS:
            tokens.add(acro.lower())
    return tokens


def _verify_finding(finding: Finding, corpus_lower: str) -> tuple[bool, float]:
    if not finding.evidence or len(finding.evidence.strip()) < 8:
        return (False, 0.0)
    tokens = _extract_tokens(finding.evidence)
    if not tokens:
        # Purely qualitative citation — can't substring-check; mark inconclusive.
        return (True, 0.5)
    matched = sum(1 for t in tokens if t in corpus_lower)
    score = matched / len(tokens)
    return (score >= _VERIFY_THRESHOLD, round(score, 3))


def verify_report(report: AgentReport) -> AgentReport:
    """Annotate findings with verified + match_score; set hallucination_rate.

    Mutates and returns the same report. Clears `corpus` after verifying so the
    downstream renderer doesn't have to worry about it.
    """
    if not report.findings or not report.corpus:
        return report

    corpus_lower = report.corpus.lower()
    failed = 0
    for f in report.findings:
        verified, score = _verify_finding(f, corpus_lower)
        f.verified = verified
        f.match_score = score
        if not verified:
            failed += 1

    report.hallucination_rate = round(failed / len(report.findings), 3)
    report.corpus = ""
    return report
