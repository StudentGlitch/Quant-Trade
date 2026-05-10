from fastapi import APIRouter, Depends
from loguru import logger
import duckdb
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from .cio_schemas import CIODeskResponse, RiskState, ShareholderReport

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
DB_PATH = BASE_DIR / "quant-engine" / "storage" / "db" / "quant_data.duckdb"

def get_duckdb_conn():
    try:
        con = duckdb.connect(str(DB_PATH), read_only=True)
        yield con
    except duckdb.IOException as e:
        logger.error(f"Failed to connect to DuckDB for CIO Desk: {e}")
        yield None
    finally:
        if 'con' in locals() and con is not None:
            con.close()

@router.get("/cio/desk", response_model=CIODeskResponse)
def get_cio_desk_data(con: duckdb.DuckDBPyConnection = Depends(get_duckdb_conn)):
    """
    Phase 6.4: CIO Desk API.
    Aggregates risk metrics and shareholder reports.
    """
    if con is None:
        return CIODeskResponse(
            current_risk=RiskState(date="", var_99=0, cvar_99=0, regime="UNKNOWN", kill_switch_engaged=False, recommended_cash_pct=0),
            historical_risk_series=[],
            latest_report=None,
            recent_reports=[]
        )

    try:
        # 1. Fetch Risk Metrics
        risk_df = con.execute("SELECT * FROM risk_metrics_ledger ORDER BY date DESC").df()
        
        historical_risk = []
        for _, row in risk_df.iterrows():
            historical_risk.append(RiskState(
                date=str(row['date']),
                var_99=float(row['portfolio_var_99']),
                cvar_99=float(row['portfolio_cvar_99']),
                regime=row['volatility_regime'],
                kill_switch_engaged=bool(row['cio_override_active']),
                recommended_cash_pct=float(row['target_cash_buffer'])
            ))
            
        current_risk = historical_risk[0] if historical_risk else RiskState(
            date=datetime.now().isoformat(), var_99=0, cvar_99=0, regime="NORMAL", kill_switch_engaged=False, recommended_cash_pct=0
        )
        
        # 2. Fetch Shareholder Reports
        reports_df = con.execute("SELECT * FROM shareholder_reports ORDER BY publish_date DESC").df()
        
        recent_reports = []
        for _, row in reports_df.iterrows():
            recent_reports.append(ShareholderReport(
                report_id=row['report_id'],
                publish_date=str(row['publish_date']),
                markdown_content=row['markdown_content'],
                prev_week_pnl=float(row['prev_week_pnl'])
            ))
            
        latest_report = recent_reports[0] if recent_reports else None
        
        return CIODeskResponse(
            current_risk=current_risk,
            historical_risk_series=historical_risk[:30], # Last 30 days
            latest_report=latest_report,
            recent_reports=recent_reports[1:6] # Last 5 excluding latest
        )
        
    except Exception as e:
        logger.error(f"Error building CIO Desk response: {e}")
        return CIODeskResponse(
            current_risk=RiskState(date="", var_99=0, cvar_99=0, regime="ERROR", kill_switch_engaged=False, recommended_cash_pct=0),
            historical_risk_series=[],
            latest_report=None,
            recent_reports=[]
        )
