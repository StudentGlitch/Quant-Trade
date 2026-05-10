from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
import duckdb
from pathlib import Path
from datetime import datetime

from .live_trading_schemas import LiveTradingResponse, LiveOrder, ReconciliationState

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
DB_PATH = BASE_DIR / "quant-engine" / "storage" / "db" / "quant_data.duckdb"

def get_duckdb_conn():
    try:
        # NOTE: Not read_only=True here if we want to allow emergency updates,
        # but standard endpoints should generally be read-only.
        # For the emergency halt, we might need write access.
        con = duckdb.connect(str(DB_PATH))
        yield con
    except duckdb.IOException as e:
        logger.error(f"Failed to connect to DuckDB for live trading: {e}")
        yield None
    finally:
        if 'con' in locals() and con is not None:
            con.close()

@router.get("/live-trading/status", response_model=LiveTradingResponse)
def get_live_trading_status(con: duckdb.DuckDBPyConnection = Depends(get_duckdb_conn)):
    """
    Phase 10.3: Reconciliation & Fast API.
    Serve the LiveTradingResponse schema to the frontend.
    """
    if con is None:
        return LiveTradingResponse(
            is_live_mode_active=False,
            recent_orders=[],
            reconciliation=ReconciliationState(date=datetime.now().isoformat(), drift_percentage=0.0, sync_status="ERROR")
        )

    try:
        # Check Kill Switch
        risk_row = con.execute("SELECT cio_override_active FROM risk_metrics_ledger ORDER BY date DESC LIMIT 1").fetchone()
        is_live_active = not (risk_row[0] if risk_row else False)

        # Get Recent Orders
        orders_df = con.execute("SELECT * FROM live_order_blotter ORDER BY timestamp DESC LIMIT 20").df()
        recent_orders = []
        for _, row in orders_df.iterrows():
            recent_orders.append(LiveOrder(
                order_id=row['order_id'],
                ticker=row['ticker'],
                order_type=row['order_type'],
                quantity=int(row['quantity']),
                status=row['status'],
                executed_price=float(row['executed_price'])
            ))

        # Get Reconciliation State
        recon_row = con.execute("SELECT * FROM ledger_reconciliation ORDER BY date DESC LIMIT 1").fetchone()
        if recon_row:
            recon_state = ReconciliationState(
                date=str(recon_row[0]),
                drift_percentage=float(recon_row[3]),
                sync_status=recon_row[4]
            )
        else:
            recon_state = ReconciliationState(date=datetime.now().isoformat(), drift_percentage=0.0, sync_status="UNKNOWN")

        return LiveTradingResponse(
            is_live_mode_active=is_live_active,
            recent_orders=recent_orders,
            reconciliation=recon_state
        )

    except Exception as e:
        logger.error(f"Error fetching live trading status: {e}")
        return LiveTradingResponse(
            is_live_mode_active=False,
            recent_orders=[],
            reconciliation=ReconciliationState(date=datetime.now().isoformat(), drift_percentage=0.0, sync_status="ERROR")
        )

@router.post("/live-trading/emergency-halt")
def trigger_emergency_halt(con: duckdb.DuckDBPyConnection = Depends(get_duckdb_conn)):
    """
    Phase 10.3: Emergency Halt Endpoint.
    Manually terminate all active execution logic.
    """
    if con is None:
        raise HTTPException(status_code=503, detail="Database connection failed.")

    try:
        logger.critical("EMERGENCY HALT INITIATED VIA API.")
        con.execute("""
            INSERT OR REPLACE INTO risk_metrics_ledger (date, portfolio_var_99, portfolio_cvar_99, volatility_regime, cio_override_active, target_cash_buffer)
            VALUES (CURRENT_DATE, -1.0, -1.0, 'CRISIS', TRUE, 1.0)
        """)
        return {"status": "success", "message": "Emergency Kill Switch Engaged. Portfolio liquidation to 100% Cash initiated."}
    except Exception as e:
        logger.error(f"Failed to engage emergency halt: {e}")
        raise HTTPException(status_code=500, detail="Failed to engage Kill Switch.")
