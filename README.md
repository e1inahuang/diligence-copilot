# diligence-copilot

A CLI/agent tool I built for people in private equity to speed up preliminary diligence on public-company comparables. Runs several specialist agents in parallel, scores each finding by confidence, and outputs an IC-memo-style markdown report.

## What it does

Given a ticker or company name, it:

1. Resolves the entity and pulls market metrics (Yahoo Finance), latest 10-K / 10-Q excerpts (SEC EDGAR), and recent news + litigation hits (Tavily web search).
2. Runs four specialist agents **in parallel** — financial, market, risk, news — each grounded on its own evidence slice and asked to emit JSON findings with `confidence` and `data_quality` fields.
3. Merges the agent outputs into a weighted-consensus verdict (`PURSUE` / `INVESTIGATE` / `PASS`) with a conviction score.
4. Renders an IC-memo-style markdown report.

## Install

```bash
git clone https://github.com/e1inahuang/diligence-copilot.git
cd diligence-copilot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# fill in OPENAI_API_KEY, TAVILY_API_KEY, SEC_USER_AGENT
```

## Use

Single company:
```bash
python -m src.cli AAPL
python -m src.cli "Tesla"
python -m src.cli NVDA --print-only
```
Output lands in `reports/<TICKER>_<DATE>.md`.

Batch mode:
```bash
python -m src.batch examples/batch_input.csv
```

## Structure

```
src/
├── cli.py                CLI entry
├── batch.py              Batch CSV runner
├── resolver.py           Ticker / company → canonical entity
├── orchestrator.py       Parallel data fetch + parallel agent execution
├── scoring.py            Weighted-consensus verdict logic
├── report.py             Markdown IC-memo renderer
├── sources/
│   ├── market.py         yfinance
│   ├── filings.py        SEC EDGAR (no key)
│   └── news.py           Tavily search
└── agents/
    ├── base.py           Shared schema + LLM call
    ├── financial.py
    ├── market.py
    ├── risk.py
    └── news.py
```

## Design notes

- **Why multi-agent, not one big prompt.** Each agent sees only the evidence relevant to its lens, which keeps context tight, makes confidence scoring per-domain, and lets you swap or weight agents independently.
- **Confidence ≠ conviction.** `confidence` measures how well evidence supports a claim; the `verdict` is a weighted combination of (sentiment × confidence) across agents. They're separate on purpose so analysts can disagree with the verdict without disputing the evidence read.
- **JSON-only agent output.** All agent prompts pin the model to a strict JSON schema (`response_format=json_object`). Easier to merge, easier to test, easier to debug.
- **No paid market-data API.** yfinance + SEC EDGAR cover ~90% of what a preliminary read needs without any auth.

## What I left out (and why)

- **PDF export.** Markdown → PDF is a one-liner with pandoc; not worth bundling for a prototype.
- **Caching / persistence.** Reports are file-based; no DB.
- **Local geo / competitor search.** This version targets public companies, not multi-location SMB targets.
- **A web UI.** A Streamlit shell would take ~30 min to add over this core; the CLI is the interesting part.

## Roadmap

- Bayesian agent aggregation instead of weighted average
- Add a comparables agent (peer multiples table)
- Replace Tavily with a richer litigation source (CourtListener)
- Stream agent progress in the CLI as each finishes

## Sample report generated

<img width="650" height="751" alt="Screenshot 2026-05-11 at 7 25 59 PM" src="https://github.com/user-attachments/assets/67e04511-d1aa-4929-bf19-16facdc4fb6f" />
<img width="654" height="760" alt="Screenshot 2026-05-11 at 7 26 10 PM" src="https://github.com/user-attachments/assets/17885856-b961-4bb1-9b63-28d6558e8d62" />
<img width="643" height="763" alt="Screenshot 2026-05-11 at 7 26 36 PM" src="https://github.com/user-attachments/assets/76cbf2d4-2e67-490e-8853-6e7280a8719a" />
<img width="644" height="755" alt="Screenshot 2026-05-11 at 7 26 47 PM" src="https://github.com/user-attachments/assets/6db83f84-183a-40bc-82e8-ef5fdaa4ddb2" />


