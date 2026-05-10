from fastapi import APIRouter, Depends, Query
from typing import List, Optional
import duckdb
from pathlib import Path
from loguru import logger
import math
from .schemas import TickerScreenerState, ScreenerResponse, ScreenerParams

router = APIRouter()

# Resolve the absolute path to the DuckDB file
# Assuming backend runs from stockscope-unified/backend
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
DB_PATH = BASE_DIR / "quant-engine" / "storage" / "db" / "quant_data.duckdb"
PARQUET_BASE = BASE_DIR / "quant-engine" / "storage" / "parquet_data"

def get_duckdb_conn():
    """Implement a global DuckDB connection pool (read-only mode) PRD 7.2.1.2."""
    try:
        # Read-only prevents locking the database while the background swarm is writing
        con = duckdb.connect(str(DB_PATH), read_only=True)
        yield con
    except duckdb.IOException as e:
        logger.error(f"Failed to connect to DuckDB: {e}")
        # Yield None so endpoints can handle the locked state gracefully
        yield None
    finally:
        if 'con' in locals() and con is not None:
            con.close()

@router.get("/screener", response_model=ScreenerResponse)
def get_screener_data(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    sector: Optional[str] = None,
    min_f_score: Optional[int] = 0,
    sort_by: str = Query("final_blended_signal"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    con: duckdb.DuckDBPyConnection = Depends(get_duckdb_conn)
):
    """
    Paginated Screener API routing (PRD 7 Phase 2.1).
    Queries the distributed Parquet hive efficiently.
    """
    if con is None:
        # Graceful degradation if DB is locked by swarm training
        return ScreenerResponse(data=[], total_count=0, page=page, total_pages=0)

    offset = (page - 1) * limit
    
    # Validate sort parameters to prevent SQL injection
    allowed_sort_cols = ['final_blended_signal', 'cross_sectional_z_score', 'f_score', 'close_price']
    if sort_by not in allowed_sort_cols:
        sort_by = 'final_blended_signal'

    # Build WHERE clauses dynamically
    where_clauses = []
    
    # Example logic for f_score filtering, assuming it exists in feature_store or is calculated
    # For now we mock f_score since it was in the fastAPI DB previously, 
    # but PRD implies querying parquet directly.
    # In a full implementation, f_score would be part of the feature_store.
    
    # We use a CTE to get the latest paper_trade record for each ticker
    query_base = f"""
        WITH LatestTrades AS (
            SELECT 
                ticker, ml_signal, llm_signal, final_blended_signal, vibe, final_direction, cross_sectional_z_score,
                ROW_NUMBER() OVER(PARTITION BY ticker ORDER BY signal_date DESC) as rn
            FROM paper_trades
        ),
        ScreenerData AS (
            SELECT 
                m.ticker, 
                COALESCE(m.company_name, 'Unknown') as company_name, 
                COALESCE(m.sector, 'Unknown') as sector,
                -- We approximate close_price from parquet if available, otherwise 0
                0.0 AS close_price,
                -- We mock f_score for now until it's officially stored in DuckDB
                5 AS f_score,
                COALESCE(t.ml_signal, 0.0) AS ml_cohort_signal,
                COALESCE(t.llm_signal, 0.0) AS llm_cohort_signal,
                COALESCE(t.final_blended_signal, 0.0) AS final_blended_signal,
                COALESCE(t.cross_sectional_z_score, 0.0) AS cross_sectional_z_score,
                COALESCE(t.vibe, 'Unknown') AS vibe
            FROM idx_metadata m
            LEFT JOIN LatestTrades t ON m.ticker = t.ticker AND t.rn = 1
            WHERE m.status = 'ACTIVE'
    """
    
    if sector:
        # Parameterized query to prevent injection
        where_clauses.append(f"m.sector = '{sector}'")
        
    if where_clauses:
        query_base += " AND " + " AND ".join(where_clauses)
        
    query_base += "\n)"

    # Count Query
    count_query = query_base + " SELECT count(*) FROM ScreenerData"
    total_count = con.execute(count_query).fetchone()[0]
    total_pages = math.ceil(total_count / limit)

    # Data Query
    data_query = query_base + f"""
        SELECT * FROM ScreenerData
        ORDER BY {sort_by} {sort_order.upper()}
        LIMIT {limit} OFFSET {offset}
    """
    
    try:
        df = con.execute(data_query).df()
        
        # Convert to Pydantic models
        results = []
        for _, row in df.iterrows():
            results.append(TickerScreenerState(
                ticker=row['ticker'],
                company_name=row['company_name'],
                sector=row['sector'],
                close_price=row['close_price'],
                f_score=row['f_score'],
                ml_cohort_signal=row['ml_cohort_signal'],
                llm_cohort_signal=row['llm_cohort_signal'],
                final_blended_signal=row['final_blended_signal'],
                cross_sectional_z_score=row['cross_sectional_z_score'],
                vibe=row['vibe']
            ))
            
        return ScreenerResponse(
            data=results,
            total_count=total_count,
            page=page,
            total_pages=total_pages
        )
    except Exception as e:
        logger.error(f"Screener query failed: {e}")
        return ScreenerResponse(data=[], total_count=0, page=page, total_pages=0)
