from fastapi import APIRouter, Depends
from loguru import logger
import duckdb
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from .portfolio_schemas import PortfolioResponse, HoldingTarget, PortfolioExposure

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
DB_PATH = BASE_DIR / "quant-engine" / "storage" / "db" / "quant_data.duckdb"

def get_duckdb_conn():
    try:
        con = duckdb.connect(str(DB_PATH), read_only=True)
        yield con
    except duckdb.IOException as e:
        logger.error(f"Failed to connect to DuckDB for portfolio: {e}")
        yield None
    finally:
        if 'con' in locals() and con is not None:
            con.close()

@router.get("/portfolio/current", response_model=PortfolioResponse)
def get_current_portfolio(con: duckdb.DuckDBPyConnection = Depends(get_duckdb_conn)):
    """
    Phase 3.2: FastAPI Portfolio Route.
    Reads portfolio_targets and constructs PortfolioResponse.
    """
    if con is None:
        return PortfolioResponse(
            timestamp=datetime.now().isoformat(),
            holdings=[],
            exposure=PortfolioExposure(sector_allocations={}, cash_drag_pct=1.0),
            estimated_annual_yield=0.0,
            portfolio_sharpe=0.0
        )

    portfolio_value = 100_000_000.0  # Simulated 100M IDR portfolio
    
    query = """
        SELECT 
            pt.ticker, 
            m.company_name, 
            m.sector, 
            -- Approximate current price from recent parquet data or paper_trades
            COALESCE((SELECT p.close FROM read_parquet('storage/parquet_data/ticker=*/data.parquet', hive_partitioning=1) p WHERE p.ticker = pt.ticker ORDER BY p.date DESC LIMIT 1), 0.0) as current_price,
            pt.target_weight_pct, 
            pt.llm_conviction, 
            pt.volatility_30d
        FROM portfolio_targets pt
        LEFT JOIN idx_metadata m ON pt.ticker = m.ticker
        WHERE pt.date = (SELECT MAX(date) FROM portfolio_targets)
    """
    
    try:
        df = con.execute(query).df()
        
        holdings = []
        sector_allocations = defaultdict(float)
        total_weight = 0.0
        
        for _, row in df.iterrows():
            weight = row['target_weight_pct']
            holdings.append(HoldingTarget(
                ticker=row['ticker'],
                company_name=row.get('company_name', 'Unknown') or 'Unknown',
                sector=row.get('sector', 'Unknown') or 'Unknown',
                current_price=float(row['current_price']),
                target_weight_pct=weight,
                notional_value_idr=weight * portfolio_value,
                llm_conviction=float(row['llm_conviction']),
                volatility_30d=float(row['volatility_30d'])
            ))
            sector_allocations[row.get('sector', 'Unknown') or 'Unknown'] += weight
            total_weight += weight
            
        cash_drag = max(0.0, 1.0 - total_weight)
        
        # In a real system, these would be calculated based on historical performance of the actual portfolio weights
        estimated_annual_yield = 0.12 # Mock value
        portfolio_sharpe = 1.5 # Mock value
        
        return PortfolioResponse(
            timestamp=datetime.now().isoformat(),
            holdings=holdings,
            exposure=PortfolioExposure(
                sector_allocations=dict(sector_allocations),
                cash_drag_pct=cash_drag
            ),
            estimated_annual_yield=estimated_annual_yield,
            portfolio_sharpe=portfolio_sharpe
        )
        
    except Exception as e:
        logger.error(f"Error fetching portfolio targets: {e}")
        return PortfolioResponse(
            timestamp=datetime.now().isoformat(),
            holdings=[],
            exposure=PortfolioExposure(sector_allocations={}, cash_drag_pct=1.0),
            estimated_annual_yield=0.0,
            portfolio_sharpe=0.0
        )
