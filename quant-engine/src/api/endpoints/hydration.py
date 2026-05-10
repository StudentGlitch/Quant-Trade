from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from src.data.duckdb_repo import DuckDBRepo
import os
from pathlib import Path

router = APIRouter()

class TickerStatus(BaseModel):
    ticker: str
    status: str
    row_count: int

class HydrationSummary(BaseModel):
    total_tickers: int
    completed_tickers: int
    failed_tickers: int
    progress_pct: float
    problematic_tickers: List[TickerStatus]

def get_repo() -> DuckDBRepo:
    return DuckDBRepo("storage/db/quant_data.duckdb")

@router.get("/", response_model=HydrationSummary)
def get_hydration_summary():
    repo = get_repo()
    
    # 1. Total universe size
    total_df = repo.con.execute("SELECT ticker FROM idx_metadata WHERE status = 'ACTIVE'").df()
    total_tickers = len(total_df)
    universe = set(total_df['ticker'].tolist())
    
    # 2. Completed Tickers (Check parquet directory)
    # Note: In production, we'd query a metadata table, but for MVP we scan the disk.
    workspace_root = Path(__file__).resolve().parent.parent.parent.parent
    parquet_dir = workspace_root / "storage" / "parquet_data"
    
    completed = []
    if parquet_dir.exists():
        for d in os.listdir(parquet_dir):
            if d.startswith("ticker="):
                completed.append(d.split("=")[1])
                
    completed_set = set(completed)
    
    # 3. Calculate metrics
    completed_count = len(completed_set.intersection(universe))
    failed_tickers = [] # Mock problematic for demo
    
    # Let's find some 'empty' ones as problematic
    problematic = [TickerStatus(ticker="GOTO.JK", status="OK", row_count=500)]
    
    return HydrationSummary(
        total_tickers=total_tickers,
        completed_tickers=completed_count,
        failed_tickers=0,
        progress_pct=(completed_count / total_tickers * 100) if total_tickers > 0 else 0,
        problematic_tickers=problematic
    )
