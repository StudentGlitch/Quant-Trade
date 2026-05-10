from pydantic import BaseModel
from typing import List, Optional

class ScreenerParams(BaseModel):
    page: int = 1
    limit: int = 50
    sector: Optional[str] = None
    min_f_score: Optional[int] = 0
    sort_by: str = "final_blended_signal" # e.g., 'sharpe_ratio', 'ml_signal'
    sort_order: str = "desc"

class TickerScreenerState(BaseModel):
    ticker: str
    company_name: str
    sector: str
    close_price: float
    f_score: int
    ml_cohort_signal: float
    llm_cohort_signal: float
    final_blended_signal: float
    cross_sectional_z_score: float
    vibe: str

class ScreenerResponse(BaseModel):
    data: List[TickerScreenerState]
    total_count: int
    page: int
    total_pages: int
