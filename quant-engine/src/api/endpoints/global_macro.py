from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from src.data.duckdb_repo import DuckDBRepo
import random

router = APIRouter()

class CrossMarketSignal(BaseModel):
    source_market: str
    target_market: str
    lagged_correlation: float
    predictive_shock_direction: str

class FxExposure(BaseModel):
    currency: str
    gross_exposure_base_ccy: float
    hedge_ratio: float
    net_risk_base_ccy: float

class GlobalMacroResponse(BaseModel):
    active_sessions: List[str]
    fx_exposures: List[FxExposure]
    contagion_signals: List[CrossMarketSignal]

def get_repo() -> DuckDBRepo:
    return DuckDBRepo("storage/db/quant_data.duckdb")

@router.get("/", response_model=GlobalMacroResponse)
def get_global_macro_insights():
    repo = get_repo()
    
    # Fetch active sessions (Mocking for now)
    active_sessions = ["NASDAQ", "CRYPTO"]
    
    # Fetch FX Exposures
    fx_df = repo.con.execute("""
        SELECT target_currency, gross_exposure, hedge_ratio
        FROM fx_hedging_ledger
        WHERE date = (SELECT MAX(date) FROM fx_hedging_ledger)
    """).df()
    
    fx_exposures = []
    if not fx_df.empty:
        for _, row in fx_df.iterrows():
            gross = float(row['gross_exposure'])
            hedge = float(row['hedge_ratio'])
            fx_exposures.append(FxExposure(
                currency=row['target_currency'],
                gross_exposure_base_ccy=gross,
                hedge_ratio=hedge,
                net_risk_base_ccy=gross * (1 - hedge)
            ))
    else:
        # Fallback dummy data if empty
        fx_exposures = [
            FxExposure(currency="USD", gross_exposure_base_ccy=2500000.0, hedge_ratio=0.85, net_risk_base_ccy=375000.0),
            FxExposure(currency="EUR", gross_exposure_base_ccy=500000.0, hedge_ratio=0.90, net_risk_base_ccy=50000.0)
        ]
        
    # Generate Contagion Signals (Mocking DB fetch for Phase 18 MVP)
    contagion_signals = [
        CrossMarketSignal(
            source_market="NASDAQ Tech (QQQ)",
            target_market="IDX Tech (GOTO.JK)",
            lagged_correlation=0.68,
            predictive_shock_direction="BULLISH"
        ),
        CrossMarketSignal(
            source_market="Bitcoin (BTC)",
            target_market="MicroStrategy (MSTR)",
            lagged_correlation=0.82,
            predictive_shock_direction="BULLISH"
        )
    ]
    
    return GlobalMacroResponse(
        active_sessions=active_sessions,
        fx_exposures=fx_exposures,
        contagion_signals=contagion_signals
    )
