import pandas as pd
import numpy as np
from scipy.interpolate import griddata
from loguru import logger
from typing import List, Tuple

class VolatilitySurfaceMapper:
    """
    Phase 20.2: 3D Volatility Surface Mapper.
    Maps Implied Volatility across strike/expiration and detects smiles.
    """

    def __init__(self, repo):
        self.repo = repo

    def generate_surface_matrix(self, ticker: str) -> Tuple[List[str], List[float], List[List[float]]]:
        """Extract IV data from DuckDB and interpolate into a clean mesh grid."""
        logger.info(f"Generating IV surface matrix for {ticker}...")
        
        # 1. Fetch data from DuckDB
        df = self.repo.con.execute("""
            SELECT expiration_date, strike_price, implied_volatility 
            FROM options_chain_ledger
            WHERE underlying_ticker = ? AND implied_volatility IS NOT NULL
        """, [ticker]).df()
        
        if df.empty:
            logger.warning(f"No options data found for {ticker}")
            return [], [], []

        # 2. Prepare coordinates
        # Days to Expiration (DTE) on Y axis
        df['dte'] = (pd.to_datetime(df['expiration_date']) - pd.Timestamp.now()).dt.days
        df = df[df['dte'] > 0]
        
        points = df[['strike_price', 'dte']].values
        values = df['implied_volatility'].values

        # 3. Create Grid for Interpolation
        unique_strikes = np.sort(df['strike_price'].unique())
        unique_dtes = np.sort(df['dte'].unique())
        
        # Filter for reasonable ranges
        strike_grid = np.linspace(unique_strikes.min(), unique_strikes.max(), 30)
        dte_grid = np.linspace(unique_dtes.min(), unique_dtes.max(), 20)
        
        X, Y = np.meshgrid(strike_grid, dte_grid)

        # 4. Interpolate (Linear or Cubic)
        Z = griddata(points, values, (X, Y), method='linear')
        
        # Replace NaNs (outside of convex hull) with edge values or a floor
        Z = np.nan_to_num(Z, nan=np.nanmean(values))
        
        # 5. Format for UI (Plotly)
        expirations = [str(int(d)) + " DTE" for d in dte_grid]
        strikes = strike_grid.tolist()
        iv_matrix = Z.tolist()
        
        logger.success(f"Surface generated with {len(points)} data points.")
        return expirations, strikes, iv_matrix

    def detect_volatility_smile(self, ticker: str, expiration_date: str):
        """Analyzes a specific expiration to identify structural skew/smile."""
        # Conceptually: Compare OTM Call IV vs OTM Put IV
        pass
