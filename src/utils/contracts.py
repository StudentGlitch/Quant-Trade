from pydantic import BaseModel, Field
from typing import Literal
import datetime

class LLMSynthesis(BaseModel):
    bull_case: str = Field(..., description="Simulated bullish researcher argument")
    bear_case: str = Field(..., description="Simulated bearish researcher argument")
    synthesized_signal: float = Field(..., ge=-1.0, le=1.0)

class TradeSignal(BaseModel):
    ticker: str
    signal_date: datetime.date
    ml_cohort_signal: float = Field(..., ge=-1.0, le=1.0)
    llm_cohort_signal: float = Field(..., ge=-1.0, le=1.0)
    ml_weight: float = Field(..., ge=0.2, le=0.8)
    llm_weight: float = Field(..., ge=0.2, le=0.8)
    final_blended_signal: float = Field(..., ge=-1.0, le=1.0)
    direction: Literal[1, 0, -1]
