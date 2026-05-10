import pandas as pd
from loguru import logger
from typing import List
from .duckdb_repo import DuckDBRepo

class APIClientTemplate:
    """Standard template for new data ingestion clients."""
    
    def __init__(self, repo: DuckDBRepo):
        self.repo = repo

    def fetch_data(self, **kwargs) -> pd.DataFrame:
        """Fetch data from an external source."""
        logger.info("Fetching data...")
        # Implementation goes here
        return pd.DataFrame()

    def store_data(self, df: pd.DataFrame) -> None:
        """Upsert data into DuckDB."""
        logger.info(f"Storing {len(df)} records...")
        # Implementation goes here
        pass
