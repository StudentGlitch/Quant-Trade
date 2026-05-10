from fastapi import APIRouter, Depends, HTTPException, Security, Request
from fastapi.security import APIKeyHeader
from loguru import logger
import duckdb
from pathlib import Path
from typing import List
from datetime import datetime

from .auth_schemas import SignalPayload
from ...core.security_vault import SecurityVault
from ..core.rate_limiter import limiter

router = APIRouter()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
DB_PATH = BASE_DIR / "quant-engine" / "storage" / "db" / "quant_data.duckdb"

def get_duckdb_conn():
    try:
        con = duckdb.connect(str(DB_PATH), read_only=True)
        yield con
    except duckdb.IOException as e:
        logger.error(f"Failed to connect to DuckDB for external API: {e}")
        yield None
    finally:
        if 'con' in locals() and con is not None:
            con.close()

def verify_api_key(api_key: str = Security(api_key_header), con: duckdb.DuckDBPyConnection = Depends(get_duckdb_conn)):
    """Validate the provided X-API-Key header."""
    if con is None:
        raise HTTPException(status_code=503, detail="Database connection failed")
        
    try:
        # Check all active keys (In a real system, you'd look up by prefix first for speed)
        keys_df = con.execute("SELECT hashed_key, user_id FROM api_keys WHERE status = 'ACTIVE'").df()
        
        for _, row in keys_df.iterrows():
            if SecurityVault.verify_password(api_key, row['hashed_key']):
                return row['user_id']
                
        raise HTTPException(status_code=403, detail="Could not validate credentials")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API Key validation error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/signals/current", response_model=List[SignalPayload])
@limiter.limit("60/minute")
def get_current_signals(request: Request, user_id: str = Depends(verify_api_key), con: duckdb.DuckDBPyConnection = Depends(get_duckdb_conn)):
    """
    Phase 11.3: Client-facing signal distribution API.
    Returns the latest SWARM signals for the authenticated institutional client.
    """
    if con is None:
        raise HTTPException(status_code=503, detail="Database connection failed")
        
    try:
        # We query the targets multi table for the market neutral baseline
        df = con.execute("""
            SELECT ticker, target_weight_pct, llm_conviction 
            FROM portfolio_targets_multi 
            WHERE date = (SELECT MAX(date) FROM portfolio_targets_multi)
            AND strategy_name = 'SWARM_MARKET_NEUTRAL'
        """).df()
        
        signals = []
        for _, row in df.iterrows():
            if row['ticker'] == 'CASH': continue
            
            direction = "BUY" if row['target_weight_pct'] > 0 else "SELL"
            
            signals.append(SignalPayload(
                ticker=row['ticker'],
                signal_direction=direction,
                conviction_score=float(row['llm_conviction']),
                timestamp=datetime.now().isoformat()
            ))
            
        logger.info(f"API Gateway: Served {len(signals)} signals to client {user_id[:8]}...")
        return signals
        
    except Exception as e:
        logger.error(f"Failed to fetch signals for external API: {e}")
        return []
