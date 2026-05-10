from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from src.data.duckdb_repo import DuckDBRepo
import uuid
import json

router = APIRouter()

class StrategyGraph(BaseModel):
    ticker: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    timeframe_start: str
    timeframe_end: str
    starting_capital: float

class SimulationStatusResponse(BaseModel):
    job_id: str
    status: str
    cagr: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    equity_curve: List[Dict[str, Any]] = []

def get_repo() -> DuckDBRepo:
    return DuckDBRepo("storage/db/quant_data.duckdb")

@router.post("/submit", response_model=Dict[str, str])
async def submit_backtest(graph: StrategyGraph):
    """Submit a visual strategy for async processing."""
    job_id = str(uuid.uuid4())
    repo = get_repo()
    
    # 1. Register job in DuckDB
    repo.con.execute("""
        INSERT INTO sandbox_simulations (job_id, strategy_name, graph_payload, status)
        VALUES (?, ?, ?, 'QUEUED')
    """, [job_id, f"TM-Strategy-{job_id[:8]}", json.dumps(graph.model_dump())])
    
    # 2. Dispatch Celery Task
    from src.workers.backtest_tasks import run_visual_backtest
    run_visual_backtest.delay(
        job_id, 
        graph.ticker, 
        graph.model_dump(), 
        graph.timeframe_start, 
        graph.timeframe_end
    )
    
    return {"job_id": job_id, "status": "QUEUED"}

@router.get("/status/{job_id}", response_model=SimulationStatusResponse)
def get_backtest_status(job_id: str):
    """Poll for backtest results."""
    repo = get_repo()
    
    res = repo.con.execute("""
        SELECT status, cagr, sharpe_ratio, max_drawdown, equity_curve_json 
        FROM sandbox_simulations 
        WHERE job_id = ?
    """, [job_id]).fetchone()
    
    if not res:
        raise HTTPException(status_code=404, detail="Job not found")
        
    status = res[0]
    equity_curve = []
    if res[4]:
        equity_curve = json.loads(res[4])
        
    return SimulationStatusResponse(
        job_id=job_id,
        status=status,
        cagr=res[1] or 0.0,
        sharpe_ratio=res[2] or 0.0,
        max_drawdown=res[3] or 0.0,
        equity_curve=equity_curve
    )
