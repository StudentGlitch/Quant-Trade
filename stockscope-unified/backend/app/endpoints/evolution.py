from fastapi import APIRouter, Depends
from loguru import logger
import duckdb
from pathlib import Path
from typing import List

from .evolution_schemas import EvolutionResponse, AlphaFeature

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
DB_PATH = BASE_DIR / "quant-engine" / "storage" / "db" / "quant_data.duckdb"

def get_duckdb_conn():
    try:
        con = duckdb.connect(str(DB_PATH), read_only=True)
        yield con
    except duckdb.IOException as e:
        logger.error(f"Failed to connect to DuckDB for evolution: {e}")
        yield None
    finally:
        if 'con' in locals() and con is not None:
            con.close()

@router.get("/evolution/leaderboard", response_model=EvolutionResponse)
def get_evolution_status(con: duckdb.DuckDBPyConnection = Depends(get_duckdb_conn)):
    """
    Phase 5.3: Feature Tracking API.
    Returns Alpha feature lifecycle status.
    """
    if con is None:
        return EvolutionResponse(active_features=[], rejected_count=0, decayed_features=[], overall_ensemble_correlation=0.0)

    try:
        df = con.execute("SELECT * FROM feature_evolution_ledger").df()
        
        active = []
        decayed = []
        rejected_count = 0
        
        for _, row in df.iterrows():
            feat = AlphaFeature(
                feature_id=row['feature_id'],
                formula_snippet=row['formula_code'][:100] + "...", # Snippet for UI
                oos_sharpe=row['oos_sharpe'],
                xgboost_importance=row.get('current_xgboost_importance', 0.0),
                status=row['status']
            )
            
            if row['status'] == 'ACTIVE':
                active.append(feat)
            elif row['status'] == 'DECAYED':
                decayed.append(feat)
            else:
                rejected_count += 1
                
        # Mock ensemble correlation
        avg_rho = df[df['status'] == 'ACTIVE']['correlation_penalty'].mean() if not df.empty else 0.0
        
        return EvolutionResponse(
            active_features=active,
            rejected_count=rejected_count,
            decayed_features=decayed,
            overall_ensemble_correlation=avg_rho if not pd.isna(avg_rho) else 0.0
        )
        
    except Exception as e:
        logger.error(f"Error fetching evolution status: {e}")
        return EvolutionResponse(active_features=[], rejected_count=0, decayed_features=[], overall_ensemble_correlation=0.0)
