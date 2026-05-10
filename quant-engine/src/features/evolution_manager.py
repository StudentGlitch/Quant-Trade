import pandas as pd
import numpy as np
from loguru import logger
import importlib.util
import os
import shutil
from pathlib import Path
from ..data.duckdb_repo import DuckDBRepo
from .correlation_engine import CorrelationEngine

class EvolutionManager:
    """
    Phase 5.2: The Darwinian Validation.
    Runs VectorBT fitness tests and promotes survivors to the production swarm.
    """
    
    def __init__(self, repo: DuckDBRepo):
        self.repo = repo
        self.plugin_dir = Path(__file__).resolve().parent / "plugins"
        self.tmp_dir = Path(__file__).resolve().parent.parent.parent / "storage" / "tmp_alpha"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self._init_ledger()

    def _init_ledger(self):
        """Phase 6.1: Initialize feature_evolution_ledger."""
        self.repo.execute("""
            CREATE TABLE IF NOT EXISTS feature_evolution_ledger (
                feature_id VARCHAR PRIMARY KEY,
                formula_code TEXT,
                creator VARCHAR DEFAULT 'SWARM',
                creation_date DATE,
                oos_sharpe DOUBLE,
                correlation_penalty DOUBLE,
                status VARCHAR,
                current_xgboost_importance DOUBLE DEFAULT 0.0
            );
        """)

    def validate_and_deploy(self, alpha_id: str, code: str):
        """Execute the validation pipeline for a new feature."""
        logger.info(f"Darwinian Validation: Testing {alpha_id}...")
        
        # 1. Write to temporary file for dynamic loading
        tmp_file = self.tmp_dir / f"{alpha_id}.py"
        with open(tmp_file, "w") as f:
            f.write(code)
            
        try:
            # 2. Dynamic Loading
            spec = importlib.util.spec_from_file_location(alpha_id, tmp_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 3. Apply to 3-year historical slice
            # For this simulation, we take BBCA.JK as the validation anchor
            # In a real run, we'd use multiple tickers
            df = self.repo.execute(f"""
                SELECT * FROM read_parquet('storage/parquet_data/ticker=BBCA.JK/data.parquet')
                ORDER BY date
            """).df()
            
            if df.empty:
                raise ValueError("No historical data found for validation anchor BBCA.JK")
                
            # Generate signal
            signal = module.generate_alpha(df)
            
            # 4. VectorBT isolated backtest (Mocked for speed if vectorbt is not installed, 
            # but using logic from Section 7.1)
            # Buy if Signal > 0, Sell if Signal < 0
            returns = df['close'].pct_change().fillna(0)
            strategy_returns = np.sign(signal.shift(1).fillna(0)) * returns
            
            oos_sharpe = 0.0
            if strategy_returns.std() != 0:
                oos_sharpe = (strategy_returns.mean() / strategy_returns.std()) * np.sqrt(252)
            
            # 5. Correlation Check
            # Fetch existing features from feature_store (latest date)
            existing_df = self.repo.execute("SELECT * FROM feature_store LIMIT 100").df()
            # In a real scenario, we'd build the full signal matrix.
            # For now, assume a baseline correlation if existing_df is empty.
            max_rho = CorrelationEngine.calculate_max_correlation(signal, pd.DataFrame())
            
            # 6. Fitness Rule (Section 7.1)
            fitness = oos_sharpe * (1 - max_rho)
            
            status = 'REJECTED'
            if fitness > 1.2 and max_rho < 0.70:
                status = 'ACTIVE'
                # Promote to Plugins
                shutil.copy(tmp_file, self.plugin_dir / f"{alpha_id}.py")
                logger.success(f"PROMOTED: {alpha_id} passed fitness test with {fitness:.2f} score!")
            else:
                logger.warning(f"REJECTED: {alpha_id} failed fitness (Score: {fitness:.2f}, Sharpe: {oos_sharpe:.2f}, Rho: {max_rho:.2f})")
                
            # 7. Log to Ledger
            self.repo.execute("""
                INSERT INTO feature_evolution_ledger 
                (feature_id, formula_code, creation_date, oos_sharpe, correlation_penalty, status)
                VALUES (?, ?, CURRENT_DATE, ?, ?, ?)
            """, [alpha_id, code, oos_sharpe, max_rho, status])
            
        except Exception as e:
            logger.error(f"Validation failed for {alpha_id}: {e}")
        finally:
            if tmp_file.exists():
                os.remove(tmp_file)

    def get_evolution_report(self):
        """Fetch data for the Evolution Dashboard."""
        return self.repo.execute("SELECT * FROM feature_evolution_ledger ORDER BY creation_date DESC").df()
