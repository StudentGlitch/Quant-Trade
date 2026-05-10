from fastapi import APIRouter, Depends
from loguru import logger
import duckdb
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from .osint_schemas import OSINTResponse, AutonomousScraper

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
DB_PATH = BASE_DIR / "quant-engine" / "storage" / "db" / "quant_data.duckdb"

def get_duckdb_conn():
    try:
        con = duckdb.connect(str(DB_PATH), read_only=True)
        yield con
    except duckdb.IOException as e:
        logger.error(f"Failed to connect to DuckDB for OSINT: {e}")
        yield None
    finally:
        if 'con' in locals() and con is not None:
            con.close()

@router.get("/osint/status", response_model=OSINTResponse)
def get_osint_status(con: duckdb.DuckDBPyConnection = Depends(get_duckdb_conn)):
    """
    Phase 8.4: OSINT Desk API.
    Returns status of autonomous scrapers and data coverage.
    """
    if con is None:
        return OSINTResponse(active_scrapers=[], total_data_points_collected=0, alpha_contribution_pct=0.0)

    try:
        # 1. Fetch Scrapers
        scrapers_df = con.execute("SELECT * FROM osint_datasets_ledger").df()
        
        active_scrapers = []
        for _, row in scrapers_df.iterrows():
            active_scrapers.append(AutonomousScraper(
                dataset_id=row['dataset_id'],
                target_url=row['target_url'],
                frequency=row['frequency'],
                last_successful_run=str(row['last_successful_run']) if row['last_successful_run'] else None,
                status=row['status'],
                consecutive_failures=int(row['consecutive_failures'])
            ))
            
        # 2. Fetch Collection Stats
        total_points = con.execute("SELECT count(*) FROM autonomous_timeseries_data").fetchone()[0]
        
        # 3. Alpha Contribution (Mock for now, normally queries Darwinian importance)
        alpha_contrib = 0.15 # 15% of active features
        
        return OSINTResponse(
            active_scrapers=active_scrapers,
            total_data_points_collected=total_points,
            alpha_contribution_pct=alpha_contrib
        )
        
    except Exception as e:
        logger.error(f"Error fetching OSINT status: {e}")
        return OSINTResponse(active_scrapers=[], total_data_points_collected=0, alpha_contribution_pct=0.0)
