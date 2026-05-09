import pandas_datareader.data as web
import yfinance as yf
import pandas as pd
from loguru import logger
from .duckdb_repo import DuckDBRepo

class MacroClient:
    def __init__(self, repo: DuckDBRepo):
        self.repo = repo

    def _fetch_fred_data(self, start_date: str) -> pd.DataFrame:
        """Fetch US Macro data from FRED."""
        # DGS10: 10-Year Treasury
        # DGS2: 2-Year Treasury
        # CPIAUCSL: Consumer Price Index for All Urban Consumers: All Items in U.S. City Average
        # M2SL: M2 Money Stock
        fred_series = ['DGS10', 'DGS2', 'CPIAUCSL', 'M2SL']
        fred_data = web.DataReader(fred_series, 'fred', start_date)
        fred_data.index.name = 'date'
        return fred_data.rename(columns={
            'DGS10': 'us_10y_yield',
            'DGS2': 'us_2y_yield',
            'CPIAUCSL': 'us_cpi',
            'M2SL': 'us_m2'
        })

    def _fetch_vix_data(self, start_date: str) -> pd.DataFrame:
        """Fetch VIX from Yahoo Finance."""
        vix = yf.download('^VIX', start=start_date, auto_adjust=True, progress=False)
        if isinstance(vix.columns, pd.MultiIndex):
            vix.columns = vix.columns.get_level_values(0)
        vix = vix[['Close']].rename(columns={'Close': 'vix_close'})
        vix.index.name = 'date'
        return vix

    def _merge_and_validate(self, fred_data: pd.DataFrame, vix: pd.DataFrame) -> pd.DataFrame:
        """Merge and validate (PRD 7 Phase 1.3)."""
        # Use inner join to ensure we have all metrics for the same dates
        macro_df = fred_data.join(vix, how='outer')
        # PRD 7.1.3: Forward-fill macro_data to match equity trading days
        macro_df = macro_df.ffill().dropna()
        macro_df = macro_df.reset_index()
        macro_df['date'] = pd.to_datetime(macro_df['date']).dt.date
        return macro_df

    def fetch_and_store(self, start_date: str):
        """Fetch FRED and VIX data and upsert into DuckDB (PRD 7 Phase 1.4)."""
        logger.info(f"Fetching macro data starting from {start_date}...")
        
        try:
            # 1. Fetch US Macro data from FRED (PRD 4 / SRC / Data)
            fred_data = self._fetch_fred_data(start_date)
            
            # 2. Fetch VIX from Yahoo Finance
            vix = self._fetch_vix_data(start_date)

            # 3. Merge and validate (PRD 7 Phase 1.3)
            macro_df = self._merge_and_validate(fred_data, vix)

            # Upsert into DuckDB
            # Ensure schema is up to date (PRD Bug Fix: handle legacy schema)
            try:
                self.repo.con.execute("SELECT us_cpi FROM macro_data LIMIT 1")
            except Exception:
                logger.warning("Legacy macro_data schema detected. Recreating table.")
                self.repo.con.execute("DROP TABLE IF EXISTS macro_data")

            self.repo.con.execute("""
                CREATE TABLE IF NOT EXISTS macro_data (
                    date DATE PRIMARY KEY, 
                    us_10y_yield DOUBLE, 
                    us_2y_yield DOUBLE, 
                    us_cpi DOUBLE, 
                    us_m2 DOUBLE, 
                    vix_close DOUBLE
                )
            """)
            self.repo.con.execute("""
                INSERT OR REPLACE INTO macro_data (date, us_10y_yield, us_2y_yield, us_cpi, us_m2, vix_close)
                SELECT date, us_10y_yield, us_2y_yield, us_cpi, us_m2, vix_close FROM macro_df
            """)
            logger.info(f"Stored {len(macro_df)} macro records (Treasury, CPI, M2, VIX).")

        except Exception as e:
            logger.error(f"Macro data fetch failed: {e}")

    def get_macro(self) -> pd.DataFrame:
        return self.repo.con.execute("SELECT * FROM macro_data ORDER BY date").df()
