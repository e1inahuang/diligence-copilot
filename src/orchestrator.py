"""Parallel agent orchestration."""
from __future__ import annotations
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from .resolver import Entity, resolve
from .sources.market import fetch_market, MarketSnapshot
from .sources.filings import fetch_latest_filings, FilingSummary
from .sources.news import search_news, search_litigation, NewsItem
from .agents import financial as financial_agent
from .agents import market as market_agent
from .agents import risk as risk_agent
from .agents import news as news_agent
from .agents.base import AgentReport
from .scoring import consense, Consensus
from .validator import verify_report


@dataclass
class DiligenceBundle:
    entity: Entity
    market: MarketSnapshot
    filings: list[FilingSummary]
    news: list[NewsItem]
    litigation: list[NewsItem]
    reports: list[AgentReport]
    consensus: Consensus


async def _gather_data(entity: Entity):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=4) as pool:
        market_f = loop.run_in_executor(pool, fetch_market, entity.ticker)
        filings_f = loop.run_in_executor(pool, fetch_latest_filings, entity.ticker)
        news_f = loop.run_in_executor(pool, search_news, entity.name)
        lit_f = loop.run_in_executor(pool, search_litigation, entity.name)
        return await asyncio.gather(market_f, filings_f, news_f, lit_f)


async def _run_agents(entity, market, filings, news, litigation) -> list[AgentReport]:
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks = [
            loop.run_in_executor(pool, financial_agent.run, entity.name, market, filings),
            loop.run_in_executor(pool, market_agent.run, entity.name, entity.sector, entity.industry, news),
            loop.run_in_executor(pool, risk_agent.run, entity.name, filings, litigation),
            loop.run_in_executor(pool, news_agent.run, entity.name, news),
        ]
        return list(await asyncio.gather(*tasks))


async def run_diligence(query: str) -> DiligenceBundle:
    entity = resolve(query)
    market, filings, news, litigation = await _gather_data(entity)
    reports = await _run_agents(entity, market, filings, news, litigation)
    reports = [verify_report(r) for r in reports]
    consensus = consense(reports)
    return DiligenceBundle(
        entity=entity,
        market=market,
        filings=filings,
        news=news,
        litigation=litigation,
        reports=reports,
        consensus=consensus,
    )
