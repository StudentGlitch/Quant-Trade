from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from src.data.duckdb_repo import DuckDBRepo
from src.derivatives.vol_surface import VolatilitySurfaceMapper
import pandas as pd

router = APIRouter()

class OptionContract(BaseModel):
    strike: float
    option_type: str
    implied_volatility: float
    delta: float
    vega: float
    bid: float
    ask: float

class VolatilitySurfaceData(BaseModel):
    ticker: str
    expirations: List[str]
    strikes: List[float]
    iv_matrix: List[List[float]]

class DerivativesResponse(BaseModel):
    surface: VolatilitySurfaceData
    chain: List[OptionContract]
    net_portfolio_greeks: dict

def get_repo() -> DuckDBRepo:
    return DuckDBRepo("storage/db/quant_data.duckdb")

@router.get("/{ticker}", response_model=DerivativesResponse)
def get_derivatives_analytics(ticker: str):
    repo = get_repo()
    mapper = VolatilitySurfaceMapper(repo)
    
    # 1. Generate Surface
    expirations, strikes, iv_matrix = mapper.generate_surface_matrix(ticker)
    surface = VolatilitySurfaceData(
        ticker=ticker,
        expirations=expirations,
        strikes=strikes,
        iv_matrix=iv_matrix
    )
    
    # 2. Fetch Latest Chain
    chain_df = repo.con.execute("""
        SELECT strike_price, option_type, implied_volatility, delta, vega, last_price 
        FROM options_chain_ledger 
        WHERE underlying_ticker = ?
        ORDER BY strike_price ASC
        LIMIT 50
    """, [ticker]).df()
    
    chain = []
    for _, row in chain_df.iterrows():
        chain.append(OptionContract(
            strike=float(row['strike_price']),
            option_type=row['option_type'],
            implied_volatility=float(row['implied_volatility']),
            delta=float(row['delta']),
            vega=float(row['vega']),
            bid=float(row['last_price']) * 0.98, # Mock bid
            ask=float(row['last_price']) * 1.02  # Mock ask
        ))
        
    # 3. Fetch Portfolio Greeks
    greeks_df = repo.con.execute("""
        SELECT net_delta, net_gamma, net_theta, net_vega 
        FROM portfolio_greeks 
        ORDER BY date DESC LIMIT 1
    """).df()
    
    net_greeks = {}
    if not greeks_df.empty:
        net_greeks = greeks_df.iloc[0].to_dict()
    else:
        net_greeks = {"net_delta": 0.0, "net_gamma": 0.0, "net_theta": 0.0, "net_vega": 0.0}
        
    return DerivativesResponse(
        surface=surface,
        chain=chain,
        net_portfolio_greeks=net_greeks
    )
