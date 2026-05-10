"""SEC EDGAR filings — fetch latest 10-K / 10-Q risk factors and MD&A excerpts."""
from __future__ import annotations
import os
import re
import httpx
from dataclasses import dataclass

TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"


def _ua() -> dict:
    ua = os.getenv("SEC_USER_AGENT", "diligence-copilot research@example.com")
    return {"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}


@dataclass
class FilingSummary:
    form: str
    filed_date: str
    accession: str
    url: str
    risk_factors_excerpt: str | None
    mdna_excerpt: str | None


def _ticker_to_cik(ticker: str) -> str | None:
    try:
        r = httpx.get(TICKER_MAP_URL, headers=_ua(), timeout=15)
        r.raise_for_status()
        for _, row in r.json().items():
            if row.get("ticker", "").upper() == ticker.upper():
                return str(row["cik_str"]).zfill(10)
    except Exception:
        return None
    return None


def _latest_filing(cik: str, form: str) -> dict | None:
    try:
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        r = httpx.get(url, headers=_ua(), timeout=15)
        r.raise_for_status()
        recent = r.json().get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        for i, f in enumerate(forms):
            if f == form:
                return {
                    "accession": recent["accessionNumber"][i],
                    "filed_date": recent["filingDate"][i],
                    "primary_doc": recent["primaryDocument"][i],
                }
    except Exception:
        return None
    return None


def _excerpt(text: str, patterns: list[str], max_chars: int = 6000) -> str | None:
    lowered = text.lower()
    for pat in patterns:
        idx = lowered.find(pat)
        if idx >= 0:
            chunk = text[idx : idx + max_chars]
            chunk = re.sub(r"\s+", " ", chunk)
            return chunk.strip()
    return None


def fetch_latest_filings(ticker: str) -> list[FilingSummary]:
    cik = _ticker_to_cik(ticker)
    if not cik:
        return []
    results: list[FilingSummary] = []
    for form in ("10-K", "10-Q"):
        meta = _latest_filing(cik, form)
        if not meta:
            continue
        acc_clean = meta["accession"].replace("-", "")
        doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_clean}/{meta['primary_doc']}"
        risk = mdna = None
        try:
            r = httpx.get(doc_url, headers=_ua(), timeout=30)
            r.raise_for_status()
            text = re.sub(r"<[^>]+>", " ", r.text)
            text = re.sub(r"&nbsp;|&amp;", " ", text)
            risk = _excerpt(text, ["risk factors", "item 1a"])
            mdna = _excerpt(text, ["management's discussion and analysis", "item 7."])
        except Exception:
            pass
        results.append(
            FilingSummary(
                form=form,
                filed_date=meta["filed_date"],
                accession=meta["accession"],
                url=doc_url,
                risk_factors_excerpt=risk,
                mdna_excerpt=mdna,
            )
        )
    return results
