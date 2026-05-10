from fastapi import APIRouter, Depends
from loguru import logger
import duckdb
from pathlib import Path
from datetime import datetime
import numpy as np

from .performance_schemas import PerformanceResponse, PerformanceMetrics, DailyEquitySnapshot
# We import the attribution logic from quant-engine if possible, 
# or we re-implement a light version here if pathing is tricky.
# Given the project structure, we'll implement the logic directly in the endpoint 
# querying the same DuckDB to keep it decoupled from the swarm daemon.

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
DB_PATH = BASE_DIR / "quant-engine" / "storage" / "db" / "quant_data.duckdb"

def get_duckdb_conn():
    try:
        con = duckdb.connect(str(DB_PATH), read_only=True)
        yield con
    except duckdb.IOException as e:
        logger.error(f"Failed to connect to DuckDB for performance: {e}")
        yield None
    finally:
        if 'con' in locals() and con is not None:
            con.close()

@router.get("/performance/tearsheet", response_model=PerformanceResponse)
def get_performance_tearsheet(con: duckdb.DuckDBPyConnection = Depends(get_duckdb_conn)):
    """
    Phase 4.3: Performance Attribution API.
    Calculates metrics and equity curve from daily_pnl_ledger.
    """
    if con is None:
        # Return empty metrics if DB locked
        return PerformanceResponse(
            metrics=PerformanceMetrics(cumulative_return_pct=0, cagr_pct=0, max_drawdown_pct=0, beta_to_ihsg=0, alpha_annualized=0, information_ratio=0, win_rate_pct=0),
            equity_curve=[],
            last_updated=datetime.now().isoformat()
        )

    try:
        df = con.execute("SELECT * FROM daily_pnl_ledger ORDER BY date").df()
        if df.empty or len(df) < 2:
             return PerformanceResponse(
                metrics=PerformanceMetrics(cumulative_return_pct=0, cagr_pct=0, max_drawdown_pct=0, beta_to_ihsg=0, alpha_annualized=0, information_ratio=0, win_rate_pct=0),
                equity_curve=[],
                last_updated=datetime.now().isoformat()
            )

        # Basic Returns
        df['rp'] = df['total_equity'].pct_change().fillna(0)
        df['rb'] = df['benchmark_value'].pct_change().fillna(0)
        
        # Max Drawdown Calculation
        equity = df['total_equity'].values
        peak = np.maximum.accumulate(equity)
        df['drawdown_pct'] = (peak - equity) / peak * 100
        
        # Metrics Calculation
        total_return_p = (equity[-1] / equity[0]) - 1
        n_days = len(df)
        ann_factor = 252 / n_days if n_days > 0 else 0
        
        rp_arr = df['rp'].values
        rb_arr = df['rb'].values
        beta = np.cov(rp_arr, rb_arr)[0, 1] / np.var(rb_arr) if np.var(rb_arr) != 0 else 1.0
        
        # Alpha
        alpha_ann = ((1 + total_return_p)**ann_factor) - (0.06 + beta * (((df['benchmark_value'].iloc[-1] / df['benchmark_value'].iloc[0])**ann_factor) - 0.06))
        
        # IR
        active_ret = rp_arr - rb_arr
        te = np.std(active_ret) * np.sqrt(252)
        ir = (np.mean(active_ret) * 252) / (te if te != 0 else 1.0)
        
        metrics = PerformanceMetrics(
            cumulative_return_pct=total_return_p * 100,
            cagr_pct=(((1 + total_return_p)**ann_factor) - 1) * 100,
            max_drawdown_pct=np.max(df['drawdown_pct']),
            beta_to_ihsg=beta,
            alpha_annualized=alpha_ann,
            information_ratio=ir,
            win_rate_pct=(len(df[df['rp'] > 0]) / len(df)) * 100
        )
        
        equity_curve = []
        for _, row in df.iterrows():
            equity_curve.append(DailyEquitySnapshot(
                date=str(row['date']),
                portfolio_value=float(row['total_equity']),
                benchmark_value=float(row['benchmark_value']),
                drawdown_pct=float(row['drawdown_pct'])
            ))
            
        return PerformanceResponse(
            metrics=metrics,
            equity_curve=equity_curve,
            last_updated=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"Error building performance tearsheet: {e}")
        return PerformanceResponse(
            metrics=PerformanceMetrics(cumulative_return_pct=0, cagr_pct=0, max_drawdown_pct=0, beta_to_ihsg=0, alpha_annualized=0, information_ratio=0, win_rate_pct=0),
            equity_curve=[],
            last_updated=datetime.now().isoformat()
        )
