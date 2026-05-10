from pydantic import BaseModel
from typing import List

class PerformanceMetrics(BaseModel):
    cumulative_return_pct: float
    cagr_pct: float
    max_drawdown_pct: float
    beta_to_ihsg: float
    alpha_annualized: float
    information_ratio: float
    win_rate_pct: float

class DailyEquitySnapshot(BaseModel):
    date: str
    portfolio_value: float
    benchmark_value: float
    drawdown_pct: float

class PerformanceResponse(BaseModel):
    metrics: PerformanceMetrics
    equity_curve: List[DailyEquitySnapshot]
    last_updated: str
