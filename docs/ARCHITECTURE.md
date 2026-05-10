# Investment Scouting & Diligence Engine — Delivery Plan

A delivery architecture and rollout plan for an AI-driven diligence platform that compresses preliminary investment research from days to minutes. This document accompanies the `diligence-copilot` prototype in the repo root: the prototype is a working subset of the system described here.

## Contents
- [1. Intro & Problem Framing](#1-intro--problem-framing)
- [2. Solution Architecture](#2-solution-architecture)
- [3. Delivery Phases](#3-delivery-phases)
- [4. Dependencies & Risks](#4-dependencies--risks)
- [5. Launch Readiness Criteria](#5-launch-readiness-criteria)
- [6. Executive Status Update](#6-executive-status-update)
- [7. AI Workflow Note](#7-ai-workflow-note)
- [8. Prototype → Plan Mapping](#8-prototype--plan-mapping)

---

## 1. Intro & Problem Framing

Investment teams spend days running preliminary diligence on each candidate before a deal is even worth a partner conversation. The work is real (read filings, scan news, screen litigation, normalize comparables) but the **shape** of it is highly repeatable — and most of what gets surfaced is either available in public sources or derivable from them.

The goal of this engine is to **compress that preliminary read to minutes**, with three non-negotiable properties:

1. **Evidence-anchored.** Every claim cites a specific source. No floating opinions.
2. **Confidence-aware.** Each finding carries a calibration so analysts can triage what to verify first.
3. **Human-in-the-loop.** The system produces a draft memo, not a decision. Analysts and IC remain the final arbiter.

The target user is a deal team analyst or associate at a private equity, venture capital, M&A advisory, or corporate development organization. The output is an IC-style memo that a senior can read in five minutes and act on.

---

## 2. Solution Architecture

### 2.1 High-level diagram

```
                    ┌──────────────┐
   Analyst input ─▶│  CLI / Web    │
   (ticker, name)   │   front-end   │
                    └──────┬────────┘
                           │
              ┌────────────▼─────────────┐
              │     Entity Resolver       │
              │ ticker ↔ CIK ↔ legal name │
              └────────────┬─────────────┘
                           │
   ┌───────────┬───────────┼───────────┬────────────┐
   ▼           ▼           ▼           ▼            ▼
┌────────┐ ┌────────┐ ┌────────┐  ┌────────┐  ┌─────────┐
│ Market │ │  SEC   │ │ News / │  │ Litig. │  │ Future: │
│  data  │ │ EDGAR  │ │  Web   │  │ search │  │ proprietary│
│(yfin)  │ │filings │ │(Tavily)│  │(Tavily)│  │  data   │
└────┬───┘ └───┬────┘ └───┬────┘  └───┬────┘  └────┬────┘
     └─────────┴──────────┼───────────┴─────────────┘
                          │
              ┌───────────▼────────────┐
              │     Orchestrator       │
              │  (async fan-out, retry)│
              └───────────┬────────────┘
                          │
   ┌──────────────┬───────┴────────┬──────────────┐
   ▼              ▼                ▼              ▼
┌──────────┐ ┌──────────┐    ┌──────────┐  ┌──────────┐
│Financial │ │ Market   │    │   Risk   │  │   News   │
│  agent   │ │  agent   │    │  agent   │  │  agent   │
└────┬─────┘ └────┬─────┘    └────┬─────┘  └────┬─────┘
     └────────────┴────┬──────────┴─────────────┘
                       │
          ┌────────────▼─────────────┐
          │   Evidence Verifier      │
          │ token-match findings vs. │
          │       source corpus      │
          └────────────┬─────────────┘
                       │
          ┌────────────▼─────────────┐
          │   Consensus & Scoring    │
          │ weighted sentiment × conf│
          │  → verdict + conviction  │
          └────────────┬─────────────┘
                       │
          ┌────────────▼─────────────┐
          │     IC-Memo Renderer     │
          │  markdown → PDF / Excel  │
          │      / CRM export        │
          └────────────┬─────────────┘
                       │
          ┌────────────▼─────────────┐
          │   Analyst review & QA    │
          │   (human-in-the-loop)    │
          └──────────────────────────┘
```

### 2.2 Layer-by-layer

| Layer | Responsibility | Implementation in prototype | Production direction |
|---|---|---|---|
| **Data sources** | Public market metrics, SEC filings, news, litigation/controversy | yfinance, SEC EDGAR (no auth), Tavily web search | Add structured-data vendors (FMP/Refinitiv), CourtListener, proprietary CRM, sector-specific feeds |
| **Ingestion** | Resolve entity, parallel-fetch each source, normalize | `resolver.py` + `sources/*` modules | Add caching (Redis), rate-limit governors per source, schema validation |
| **Orchestration** | Fan out per-agent, retry, timeout, fail-soft | `orchestrator.py` (asyncio + thread pool) | Workflow engine (Temporal/Prefect), per-step observability |
| **Analysis (agent layer)** | Domain-specific reasoning on isolated evidence slices | Four parallel agents (financial / market / risk / news) calling GPT-4o in JSON mode | Configurable agent registry, sector-specific agents, agent versioning |
| **Memory / state** | Persist runs, support replay, audit trail | None — file-based reports | Postgres for runs, vector store for retrieved evidence chunks, structured event log |
| **Guardrails** | Catch hallucinated citations, schema violations, low-confidence outputs | `validator.py` token-match against source corpus | Entailment scoring, RAG-style attribution, eval harness with golden set |
| **Consensus & scoring** | Merge agent outputs into a single verdict | Weighted sentiment × confidence (`scoring.py`) | Bayesian aggregation; analyst-tunable weights per fund/strategy |
| **Output / reporting** | Render IC-quality memo | Markdown via `report.py` | PDF (pandoc), DOCX, Excel comparables, CRM push, IC portal embed |
| **Human review / QA** | Analyst accepts, edits, or rejects findings | Out of scope for prototype | Comment threading on findings, override workflow, feedback flows back into eval set |

### 2.3 Key design decisions

| Decision | Rationale |
|---|---|
| **Multi-agent, not one mega-prompt** | Each agent sees only the evidence relevant to its lens. Keeps context tight, gives per-domain confidence, allows independent weighting and swapping. A single prompt at this scope blurs evidence boundaries and is much harder to evaluate. |
| **JSON-only agent output** | Easier to merge, test, and debug. `response_format=json_object` plus a schema instruction in-prompt. |
| **Confidence ≠ conviction** | `confidence` measures how well evidence supports a claim. The `verdict` is a weighted combination across agents. They are kept separate so an analyst can disagree with the verdict without disputing the underlying evidence read. |
| **Closed-loop evidence verifier** | LLMs can fabricate citations. After agents return, we substring-match distinctive tokens (numbers, named entities, filing labels) from each cited `evidence` field back to the corpus the agent was given. Unverified findings are flagged in the memo. |
| **Parallel fan-out via asyncio + thread pool** | Per-source fetches and per-agent calls run concurrently. Cuts wall-clock from ~60s sequential to ~15-20s. |
| **No paid market-data API in v1** | yfinance + SEC EDGAR cover ~90% of what a preliminary read needs without auth or cost, which is the right tradeoff for a prototype and pilot. Paid vendors enter at scale-up phase. |

---

## 3. Delivery Phases

A 10-12 week rollout from kickoff to first production engagement.

### Phase 0 — Discovery & alignment (week 1)

**Goal:** Lock in what "good" looks like with the sponsor.

- Interview 3-5 target users (analysts, associates, IC members).
- Define 5-10 representative diligence scenarios (e.g., "screening a $50M EBITDA HVAC rollup target," "comping a public SaaS pre-acquisition").
- Lock the output template — what does an IC-ready memo from this engine actually look like?
- Define success metrics: time-to-first-draft, % findings accepted unchanged by analyst, # red flags surfaced vs. baseline.

**Exit criteria:** Signed-off scope, output template, eval scenarios, success metrics.

### Phase 1 — Source & ground-truth validation (week 2)

**Goal:** Confirm the data we plan to use is actually fit for purpose.

- Validate that each public source returns usable data for the in-scope universe (e.g., does EDGAR coverage extend to all relevant filers? Does Tavily surface litigation reliably for mid-cap names?).
- Identify gaps that need paid or proprietary sources.
- Build a "golden set" of 10-20 hand-curated diligence outputs to grade agents against.

**Exit criteria:** Source coverage report, gap analysis, golden eval set.

### Phase 2 — MVP build (weeks 3-5)

**Goal:** A working end-to-end pipeline producing memos at acceptable quality on the eval set.

- Build the orchestrator, agents, scoring, and renderer (the `diligence-copilot` prototype is the v0 baseline).
- Ship the evidence verifier.
- Stand up the CLI + a minimal Streamlit UI for non-technical reviewers.
- Run agents against the golden set; iterate prompts and scoring weights.

**Exit criteria:** Eval set passes a quality threshold (target: ≥75% of findings accepted by analyst review).

### Phase 3 — Internal QA & eval hardening (weeks 6-7)

**Goal:** Trust the system enough to put it in front of real analysts.

- Expand the eval set to 50+ scenarios spanning multiple sectors and deal sizes.
- Add regression testing: every prompt or model change must clear the eval bar before merge.
- Build observability: per-run logs, agent latency, hallucination rate, source-failure counts.
- Stress-test rate limits, retries, and partial-failure modes.

**Exit criteria:** Eval coverage, observability dashboard, documented operational runbook.

### Phase 4 — Pilot launch (weeks 8-10)

**Goal:** Two-to-three real deal teams running the engine on live diligence.

- Onboard pilot teams; train on what the system does and does NOT do.
- Weekly review cadence: analyst feedback on accuracy, missing fields, false positives/negatives.
- Track success metrics against baseline (manual diligence time, # rejected memos).
- Iterate prompts and scoring weights based on pilot feedback.

**Exit criteria:** ≥50% time savings reported by pilot teams; <15% memo rejection rate.

### Phase 5 — Scale-up (weeks 11+)

**Goal:** Production-grade for broader rollout.

- Add paid data sources where coverage gaps were identified.
- Persistent storage (Postgres + vector store for evidence chunks).
- Multi-tenant support, role-based access, audit logging.
- Self-service agent configuration (let teams tune weights or add sector-specific agents).
- SOC 2 readiness if external client deployment is in scope.

---

## 4. Dependencies & Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | **Public data inconsistency** — coverage gaps in EDGAR/yfinance for non-US or thinly-covered names | High | Medium | Phase 1 coverage matrix; fall back to web search; clearly flag low-data runs to user |
| R2 | **Source rate limits / instability** (Tavily quotas, SEC throttling, yfinance scraping fragility) | Medium | Medium | Caching layer, exponential backoff, dual-vendor for critical sources at scale-up |
| R3 | **LLM hallucination** — fabricated citations or numbers | High | High | Evidence verifier (v1), entailment scoring (v2), required `data_quality` self-rating, low-temp inference, IC-memo carries `unverified` flag prominently |
| R4 | **Poor signal-to-noise in news / litigation search** — boilerplate dominating real flags | Medium | Medium | Litigation-specific query templates, source-allowlist, score boost for high-authority domains |
| R5 | **Unclear success criteria** — sponsor says "make it good" but no measurable bar | Medium | High | Phase 0 forces explicit metrics; eval golden set is the ground truth |
| R6 | **Stakeholder misalignment** — deal team wants different output than IC wants | Medium | Medium | Per-persona output variants (analyst draft vs. IC memo) negotiated in Phase 0 |
| R7 | **Compliance / data residency** — depending on client, public-only may still need legal review (especially for cross-border data movement and any PII in news content) | Low–Medium | High | Legal review in Phase 0; default to public sources only; flag for an SOC 2 / DPA track if a regulated client is in scope |
| R8 | **Model cost drift** — per-run cost grows as agents and context grow | Medium | Low | Model-tier routing (smaller model for cheap agents), prompt-cache for shared context, per-run cost ceiling |
| R9 | **Vendor lock-in (LLM)** | Low | Medium | Agent layer is provider-agnostic via a thin client wrapper; can swap GPT-4o for Claude or Gemini behind the same interface |
| R10 | **Analyst over-trust** — analysts accept memos without verification once trust builds | Medium | High | Make verification status visually prominent; surface low-conviction items separately; require explicit analyst sign-off for IC submission |

---

## 5. Launch Readiness Criteria

A launch-readiness checklist gated against each category. Pilot launch (Phase 4 exit) requires all "must" items; full production (Phase 5 exit) requires "must" + "should".

### 5.1 Technical readiness
- **Must:** End-to-end run completes under 60s wall-clock for a typical public-company target.
- **Must:** All source failures degrade gracefully (no full-run failures from one missing news API call).
- **Must:** Evidence verifier integrated; unverified findings clearly marked in output.
- **Must:** Observability: per-run latency, error rate, hallucination rate logged.
- **Should:** Caching layer reduces repeat-run cost by 50%+.
- **Should:** PDF / DOCX export options.

### 5.2 Output quality
- **Must:** ≥75% of findings accepted unchanged by analyst review on the eval set.
- **Must:** ≥90% of cited evidence passes the verifier.
- **Must:** Zero fabricated litigation references (manually audited on eval set).
- **Should:** False-negative rate on known red flags below 10%.

### 5.3 Review process
- **Must:** Analyst review workflow documented (what to check, in what order, how to override).
- **Must:** Feedback channel from analyst back into eval set / prompt tuning.
- **Should:** Inline commenting on findings.

### 5.4 Stakeholder sign-off
- **Must:** Sponsor (deal team head or product owner) signs off on output template.
- **Must:** Legal/compliance review of data sources for the deployment context.
- **Should:** IC member sign-off after reviewing 3+ pilot memos.

### 5.5 Operational support
- **Must:** On-call rotation defined for production; SLA on response time for blocking issues.
- **Must:** Runbook for the top 5 expected failure modes (source outage, model rate limit, bad ticker, etc.).
- **Should:** Cost monitoring with per-tenant budget alerts.

---

## 6. Executive Status Update

> **Subject:** Investment Scouting & Diligence Engine — Week 4 Update
> **To:** Steering committee
> **From:** Delivery lead

**Headline.** We are on track to enter pilot in week 8. MVP is passing 78% of our analyst-reviewed eval set; we are tuning the risk agent specifically, which is the lagging dimension at 64%.

**Done this period.**
- Locked the IC-memo output template with the deal-team sponsors. Two variants: an analyst working draft and a partner-ready short form.
- Stood up the four-agent pipeline (financial / market / risk / news) with parallel fan-out. Median run time is 18 seconds end-to-end on public-equity targets.
- Shipped the evidence verifier — every cited finding is now token-matched back to the source corpus, and unverified items are flagged in the memo. This was the single highest-leverage trust improvement so far.
- Golden eval set of 20 scenarios built; 50-scenario expansion underway.

**Next two weeks.**
- Close the risk-agent quality gap (likely a prompt structure issue — currently mixing material risks with boilerplate).
- Expand eval coverage to 50 scenarios including 10 mid-cap and 5 cross-border targets.
- Stand up the observability dashboard (latency, error, hallucination rate per run).

**What we need from leadership.**
- Confirm the two pilot deal teams by end of week 5 so we can do training in week 6.
- A green-light from compliance on our data source set (public market data, EDGAR, public web search). We have a draft summary ready for review.

**Risks I'm watching.**
- Tavily news coverage is thinner than expected for non-US targets — we may need a second news source before pilot if international names are in pilot scope.
- Model cost per run is currently $0.04. Sustainable for pilot; we'll revisit at scale-up.

**Bottom line.** No red flags on timeline. Pilot launch week 8 is realistic. Asking for the two governance decisions above to keep us moving.

---

## 7. AI Workflow Note

Building this prototype heavily leveraged AI tooling. The point of the role is to use these tools well, not to avoid them.

### Tools used

| Tool | Used for |
|---|---|
| **Claude (Anthropic)** — conversational | Architecture sketching, code scaffolding for the whole prototype, README/docs drafting, debugging error messages, generating the directory layout, writing this delivery document, sense-checking decisions |
| **GPT-4o (OpenAI)** — programmatic | The four diligence agents themselves call GPT-4o in JSON mode at temperature 0.3 |
| **Tavily search API** | News and litigation retrieval inside the prototype |
| **yfinance + SEC EDGAR** | Market data and filings — public APIs, no LLM involved |

### How AI accelerated this work

- **Code velocity.** A multi-agent prototype with verifier, scoring, batch mode, and a CLI in four hours is not realistic to type by hand. LLM code generation handled boilerplate (dataclasses, CLI wiring, the markdown renderer) so I could focus on design decisions.
- **Source discovery.** Quickly mapped which public APIs were viable, what their quirks are (SEC needs a User-Agent header, yfinance has flaky `.info` responses), and where the gaps would be.
- **Doc drafting.** Phase plans, risk tables, and the executive update were drafted by the LLM and edited by me — much faster than writing from scratch.
- **Schema design.** Iterated on the agent JSON schema and the validator's token-extraction logic with the LLM as a thinking partner.

### What was my judgment

- **Product framing.** Researched the target user (PE / M&A teams) before scoping the prototype. Specifically chose to focus on public-company comparables as a tractable v1 — multi-location SMB diligence (a richer problem) was scoped out to a future phase.
- **Architecture choice.** Multi-agent with isolated evidence slices vs. one big prompt. The LLM did not propose this — I did, because it gives independent confidence per agent and is much more testable.
- **Confidence vs. conviction decoupling.** Deliberately separated `confidence` (evidence-support) from the verdict (weighted aggregation). This is a product decision: analysts must be able to disagree with the verdict without disputing the evidence.
- **Verifier design.** Closed-loop substring verification against source corpus was my idea after thinking through how LLM-fabricated citations would slip through any review. Cheap, deterministic, defensible.
- **What to leave out.** PDF export, persistent storage, web UI, geo/competitor search, paid data — all deferred deliberately. The deliberateness is the point: a prototype that does too much teaches nothing about prioritization.
- **Source selection.** Chose yfinance + SEC EDGAR + Tavily as the minimum credible set after evaluating ~6 options. Paid vendors enter at scale-up, not prototype.
- **Risk register.** Manually expanded the LLM's first-draft risk list because it missed analyst-over-trust (R10) and model cost drift (R8) — both of which I've seen bite real deployments.

### Tradeoffs accepted under the 4-hour budget

- No web UI — CLI only. A Streamlit shell is ~30 minutes of work on top of this core.
- No persistent storage — reports are written to a flat `reports/` directory.
- Single LLM provider — production code would route through a thin wrapper so the provider is swappable.
- Verifier uses token-match, not entailment scoring. Token-match has false-negatives on heavily paraphrased evidence; entailment scoring is the v2 upgrade and would slot in behind the same `verify_report()` interface.

---

## 8. Prototype → Plan Mapping

How the working `diligence-copilot` prototype maps to the delivery plan above.

| Plan element | Prototype status |
|---|---|
| Entity resolver | ✅ `src/resolver.py` |
| Market data ingestion | ✅ `src/sources/market.py` (yfinance) |
| Filings ingestion | ✅ `src/sources/filings.py` (SEC EDGAR) |
| News + litigation search | ✅ `src/sources/news.py` (Tavily) |
| Parallel orchestration | ✅ `src/orchestrator.py` (asyncio + thread pool) |
| Multi-agent analysis | ✅ Four agents in `src/agents/` |
| JSON schema discipline | ✅ `response_format=json_object` + in-prompt schema |
| Evidence verifier (guardrail) | ✅ `src/validator.py` |
| Consensus + verdict | ✅ `src/scoring.py` |
| IC-memo output | ✅ `src/report.py` (markdown) |
| Batch mode | ✅ `src/batch.py` |
| PDF / DOCX export | ⏭️ Phase 2 (pandoc one-liner) |
| Web UI | ⏭️ Phase 2 (Streamlit shell) |
| Caching / persistence | ⏭️ Phase 3 |
| Eval harness + regression tests | ⏭️ Phase 3 |
| Observability dashboard | ⏭️ Phase 3 |
| Paid data sources | ⏭️ Phase 5 |
| Multi-tenant + access control | ⏭️ Phase 5 |

The prototype is intentionally a **vertical slice**: it touches every layer of the architecture (sources → orchestration → agents → validator → scoring → output) at low fidelity, rather than building one layer at high fidelity. That is the right shape for a 4-hour build — it proves the end-to-end design works and surfaces the integration points that will matter most in real delivery.
