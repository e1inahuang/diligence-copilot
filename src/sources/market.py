"""Market data via yfinance."""
from __future__ import annotations
from dataclasses import dataclass, field
import yfinance as yf


@dataclass
class MarketSnapshot:
    price: float | None
    market_cap: float | None
    pe_ratio: float | None
    forward_pe: float | None
    revenue_ttm: float | None
    revenue_growth: float | None
    profit_margin: float | None
    return_on_equity: float | None
    debt_to_equity: float | None
    free_cash_flow: float | None
    fifty_two_week_high: float | None
    fifty_two_week_low: float | None
    one_year_return: float | None
    beta: float | None
    raw: dict = field(default_factory=dict)


def fetch_market(ticker: str) -> MarketSnapshot:
    t = yf.Ticker(ticker)
    info = t.info or {}

    one_year_return = None
    try:
        hist = t.history(period="1y")
        if len(hist) > 0:
            one_year_return = (hist["Close"].iloc[-1] / hist["Close"].iloc[0]) - 1
    except Exception:
        pass

    return MarketSnapshot(
        price=info.get("currentPrice") or info.get("regularMarketPrice"),
        market_cap=info.get("marketCap"),
        pe_ratio=info.get("trailingPE"),
        forward_pe=info.get("forwardPE"),
        revenue_ttm=info.get("totalRevenue"),
        revenue_growth=info.get("revenueGrowth"),
        profit_margin=info.get("profitMargins"),
        return_on_equity=info.get("returnOnEquity"),
        debt_to_equity=info.get("debtToEquity"),
        free_cash_flow=info.get("freeCashflow"),
        fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
        fifty_two_week_low=info.get("fiftyTwoWeekLow"),
        one_year_return=one_year_return,
        beta=info.get("beta"),
        raw=info,
    )
