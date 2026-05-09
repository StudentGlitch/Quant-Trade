import asyncio
from loguru import logger
from ..data.duckdb_repo import DuckDBRepo
from ..data.idx_universe import UniverseManager
from ..data.async_yf_client import AsyncYFinanceClient
from ..features.feature_registry import FeatureRegistry

class SwarmDaemon:
    """
    Background daemon that manages the lifecycle of the Quant Swarm pipeline.
    Handles universe updates, data ingestion, and feature plugin application.
    """
    def __init__(self, db_path: str = "storage/db/quant_data.duckdb"):
        self.db_path = db_path
        self.repo = DuckDBRepo(self.db_path)

    def start(self, min_adv: int = 500000000, min_market_cap: int = 1000000000000, start_date: str = '2015-01-01'):
        """Runs the pipeline execution loops."""
        logger.info("Starting SwarmDaemon...")

        with self.repo:
            # 1. Update Universe
            logger.info("Phase 1: Updating Universe")
            universe_mgr = UniverseManager(self.repo)
            universe_mgr.update_universe(min_adv=min_adv, min_market_cap=min_market_cap)

            # 2. Asynchronous Ingestion (Checkpoint/Resume)
            logger.info("Phase 2: Asynchronous Data Ingestion to Parquet")
            ingestor = AsyncYFinanceClient(self.repo)
            asyncio.run(ingestor.run_ingestion(start_date=start_date))

            # 3. Create Parquet View
            logger.info("Phase 3: Building Analytical Views")
            ingestor.load_parquets_to_duckdb()

            # 4. Feature Engineering via Plugins
            logger.info("Phase 4: Applying Feature Plugins")
            feature_registry = FeatureRegistry(self.repo)
            feature_registry.apply_plugins()

            logger.success("SwarmDaemon execution cycle complete.")

if __name__ == "__main__":
    daemon = SwarmDaemon()
    daemon.start()
