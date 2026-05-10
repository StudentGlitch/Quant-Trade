import numpy as np
import pandas as pd
from scipy.stats import entropy
from loguru import logger
from datetime import datetime
from ..data.duckdb_repo import DuckDBRepo

class DriftMonitor:
    """
    Phase 24.3: Feature Drift Detection.
    Calculates Population Stability Index (PSI) to detect regime shifts.
    """

    def __init__(self, repo: DuckDBRepo):
        self.repo = repo

    def calculate_psi(self, expected: np.ndarray, actual: np.ndarray, buckets: int = 10) -> float:
        """
        Calculates PSI between training (expected) and live (actual) distributions.
        PSI = sum((Actual% - Expected%) * ln(Actual% / Expected%))
        """
        # 1. Define buckets based on expected distribution
        breakpoints = np.percentile(expected, np.arange(0, 100, 100 / buckets))
        breakpoints = np.append(breakpoints, [np.inf])
        breakpoints[0] = -np.inf # Ensure full coverage

        # 2. Count samples in each bucket
        expected_counts = np.histogram(expected, bins=breakpoints)[0]
        actual_counts = np.histogram(actual, bins=breakpoints)[0]

        # 3. Convert to percentages (avoid zero to prevent ln(0) error)
        expected_percents = expected_counts / len(expected)
        actual_percents = actual_counts / len(actual)
        
        # Small epsilon for numerical stability
        expected_percents = np.where(expected_percents == 0, 1e-6, expected_percents)
        actual_percents = np.where(actual_percents == 0, 1e-6, actual_percents)

        # 4. Calculate PSI
        psi_value = np.sum((actual_percents - expected_percents) * np.log(actual_percents / expected_percents))
        
        return float(psi_value)

    def monitor_all_features(self, live_df: pd.DataFrame, reference_df: pd.DataFrame):
        """Sweeps all features and logs drift to DuckDB."""
        logger.info("Running daily Feature Drift sweep...")
        
        features = [col for col in live_df.columns if col.startswith(('rsi_', 'macd_', 'feat_', 'ratio_', 'z_score_'))]
        
        for feat in features:
            if feat not in reference_df.columns:
                continue
                
            expected = reference_df[feat].dropna().values
            actual = live_df[feat].dropna().values
            
            if len(expected) == 0 or len(actual) == 0:
                continue
                
            psi = self.calculate_psi(expected, actual)
            drift_detected = psi > 0.2
            
            # Upsert into DuckDB
            self.repo.con.execute("""
                INSERT OR REPLACE INTO feature_drift_ledger 
                (date, feature_name, reference_mean, current_mean, psi_score, drift_detected)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [datetime.now().date(), feat, float(np.mean(expected)), float(np.mean(actual)), psi, drift_detected])
            
            if drift_detected:
                logger.warning(f"DRIFT DETECTED: Feature '{feat}' has PSI={psi:.4f}")

        logger.success("Drift sweep complete.")
