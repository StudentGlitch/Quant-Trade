from pydantic import BaseModel
from typing import List, Dict

class HoldingTarget(BaseModel):
    ticker: str
    company_name: str
    sector: str
    current_price: float
    target_weight_pct: float
    notional_value_idr: float
    llm_conviction: float
    volatility_30d: float

class PortfolioExposure(BaseModel):
    sector_allocations: Dict[str, float]
    cash_drag_pct: float

class PortfolioResponse(BaseModel):
    timestamp: str
    holdings: List[HoldingTarget]
    exposure: PortfolioExposure
    estimated_annual_yield: float
    portfolio_sharpe: float
