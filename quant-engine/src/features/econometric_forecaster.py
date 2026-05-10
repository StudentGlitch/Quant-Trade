import pandas as pd
import numpy as np
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.api import VAR
from loguru import logger
from datetime import datetime, timedelta
from ..data.duckdb_repo import DuckDBRepo

class EconometricForecaster:
    """
    Phase 25.1: Econometric Macro Forecasting using Vector Autoregression (VAR).
    Models interdependencies among multiple macro time series.
    """

    def __init__(self, repo: DuckDBRepo):
        self.repo = repo

    def forecast_macro_regime(self, horizon: int = 30):
        """Fetch macro data, diff until stationary, and fit VAR model."""
        logger.info(f"Starting econometric VAR forecasting for horizon={horizon}...")
        
        # 1. Fetch data from DuckDB
        df = self.repo.con.execute("SELECT * FROM macro_data ORDER BY date").df()
        if df.empty or len(df) < 60:
            logger.warning("Insufficient macro data for econometric forecasting.")
            return

        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        # Select target indicators
        cols = ['vix_close', 'us_cpi', 'us_m2', 'us_10y_yield']
        data = df[cols].dropna()

        # 2. Stationarity Check (ADF Test) & Differencing
        diff_order = 0
        working_data = data.copy()
        
        while diff_order < 2:
            all_stationary = True
            for col in cols:
                p_val = adfuller(working_data[col])[1]
                if p_val > 0.05:
                    all_stationary = False
                    break
            
            if all_stationary:
                break
            
            working_data = working_data.diff().dropna()
            diff_order += 1
            logger.info(f"Differencing applied. Current order: {diff_order}")

        # 3. Fit VAR Model
        try:
            model = VAR(working_data)
            results = model.fit(maxlags=15, ic='aic')
            
            # 4. Forecast
            lag_order = results.k_ar
            forecast_input = working_data.values[-lag_order:]
            forecast_diff = results.forecast(y=forecast_input, steps=horizon)
            
            # 5. Reverse Differencing to get absolute values
            final_forecasts = self._reintegrate(data, forecast_diff, diff_order, horizon)
            
            # 6. Store in DuckDB
            self._store_forecasts(cols, final_forecasts, horizon)
            
            logger.success("Econometric macro forecasting cycle complete.")
            
        except Exception as e:
            logger.error(f"VAR Model fitting failed: {e}")

    def _reintegrate(self, original_data: pd.DataFrame, diff_forecast: np.ndarray, diff_order: int, horizon: int) -> dict:
        """Inverts differencing to return forecasts to original scale."""
        forecast_dict = {}
        
        for i, col in enumerate(original_data.columns):
            last_val = original_data[col].iloc[-1]
            col_diff = diff_forecast[:, i]
            
            if diff_order == 1:
                # Cumulative sum of diffs added to last value
                abs_forecast = last_val + np.cumsum(col_diff)
            elif diff_order == 2:
                # Double reintegration
                # Note: Simplified for MVP
                abs_forecast = last_val + np.cumsum(np.cumsum(col_diff))
            else:
                abs_forecast = col_diff
                
            forecast_dict[col] = abs_forecast.tolist()
            
        return forecast_dict

    def _store_forecasts(self, indicators: list, forecasts: dict, horizon: int):
        """Upsert predictions into econometric_forecasts table."""
        today = datetime.now().date()
        insert_data = []
        
        for indicator in indicators:
            vals = forecasts[indicator]
            for h, val in enumerate(vals):
                insert_data.append((
                    today,
                    indicator.upper().replace('_CLOSE', ''),
                    h + 1,
                    float(val),
                    float(val * 0.95), # Mock lower bound
                    float(val * 1.05)  # Mock upper bound
                ))
                
        self.repo.con.executemany("""
            INSERT OR REPLACE INTO econometric_forecasts 
            (date, macro_indicator, forecast_horizon, predicted_value, lower_confidence_bound, upper_confidence_bound)
            VALUES (?, ?, ?, ?, ?, ?)
        """, insert_data)
