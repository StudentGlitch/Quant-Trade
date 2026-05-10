from .celery_app import app
from .background_tasks import QuantTask
from ..execution.strategy_compiler import StrategyCompiler
from ..data.duckdb_repo import DuckDBRepo
from loguru import logger
import json
from datetime import datetime

@app.task(bind=True, base=QuantTask, queue='ml_training')
def run_visual_backtest(self, job_id: str, ticker: str, graph: dict, start_date: str, end_date: str):
    """
    Phase 29.2: Celery Task for long-running backtests.
    Accepts JSON graph and outputs metrics to DuckDB.
    """
    logger.info(f"Starting async backtest for job {job_id} [{ticker}]")
    
    db_path = "storage/db/quant_data.duckdb"
    repo = DuckDBRepo(db_path)
    
    try:
        # 1. Update status to RUNNING
        repo.con.execute("UPDATE sandbox_simulations SET status = 'RUNNING' WHERE job_id = ?", [job_id])
        
        # 2. Execute Compilation
        compiler = StrategyCompiler(repo)
        results = compiler.compile_and_run(ticker, graph, start_date, end_date)
        
        # 3. Finalize results in DuckDB
        repo.con.execute("""
            UPDATE sandbox_simulations 
            SET status = 'COMPLETED',
                sharpe_ratio = ?,
                cagr = ?,
                max_drawdown = ?,
                equity_curve_json = ?,
                completed_at = ?
            WHERE job_id = ?
        """, [
            results['sharpe_ratio'],
            results['cagr'],
            results['max_drawdown'],
            json.dumps(results['equity_curve']),
            datetime.now(),
            job_id
        ])
        
        logger.success(f"Backtest job {job_id} complete. Sharpe: {results['sharpe_ratio']:.2f}")
        return results

    except Exception as e:
        logger.error(f"Backtest job {job_id} failed: {e}")
        repo.con.execute("UPDATE sandbox_simulations SET status = 'FAILED' WHERE job_id = ?", [job_id])
        raise
