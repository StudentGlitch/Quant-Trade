import os
import sys
import importlib
import inspect
from pathlib import Path
import pandas as pd
from loguru import logger
from .plugins.base_plugin import BaseFeaturePlugin
from ..data.duckdb_repo import DuckDBRepo

class FeatureRegistry:
    """
    Dynamically loads and applies all BaseFeaturePlugins found in the plugins directory.
    Enforces the rule to skip calculations for tickers with < 2 years of data.
    """
    def __init__(self, repo: DuckDBRepo, plugins_dir: str = "src/features/plugins"):
        self.repo = repo
        self.plugins_dir = Path(plugins_dir)
        self.plugins: list[BaseFeaturePlugin] = []
        self._load_plugins()

    def _load_plugins(self):
        """Discovers and imports all plugins from the plugins directory."""
        if not self.plugins_dir.exists():
            logger.warning(f"Plugins directory not found: {self.plugins_dir}")
            return

        # Add parent of plugins_dir to sys.path to allow relative imports inside plugins
        sys.path.insert(0, str(self.plugins_dir.parent.parent.parent))

        for filename in os.listdir(self.plugins_dir):
            if filename.endswith(".py") and filename != "__init__.py" and filename != "base_plugin.py":
                module_name = f"src.features.plugins.{filename[:-3]}"
                try:
                    module = importlib.import_module(module_name)
                    # Find classes in the module that inherit from BaseFeaturePlugin
                    for name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj) and issubclass(obj, BaseFeaturePlugin) and obj != BaseFeaturePlugin:
                            self.plugins.append(obj())
                            logger.info(f"Loaded feature plugin: {obj.__name__} from {filename}")
                except Exception as e:
                    logger.error(f"Failed to load plugin {filename}: {e}")

    def apply_plugins(self):
        """
        Reads from ohlcv_daily_parquet, groups by ticker, applies plugins,
        and saves results to feature_store.
        Skips tickers with less than 2 years of data (~504 trading days).
        """
        if not self.plugins:
            logger.warning("No feature plugins loaded. Skipping plugin execution.")
            return

        logger.info("Applying feature plugins to Parquet dataset...")

        try:
            # First, check if the view exists
            res = self.repo.con.execute("SELECT count(*) FROM ohlcv_daily_parquet").fetchone()
            if not res or res[0] == 0:
                 logger.warning("No data in ohlcv_daily_parquet to process.")
                 return

            # Query all parquet data
            df = self.repo.con.execute("SELECT * FROM ohlcv_daily_parquet ORDER BY ticker, date").df()
        except Exception as e:
            logger.error(f"Error querying parquet view: {e}")
            return

        if df.empty:
            logger.warning("Parquet view is empty.")
            return

        processed_dfs = []
        grouped = df.groupby('ticker')

        # 2 years of trading days ~ 252 * 2 = 504
        MIN_TRADING_DAYS = 504

        for ticker, group_df in grouped:
            if len(group_df) < MIN_TRADING_DAYS:
                logger.info(f"Skipping plugin calculation for {ticker}: Only {len(group_df)} days of data (< 2 years).")
                continue

            ticker_df = group_df.copy()

            for plugin in self.plugins:
                try:
                    # Check if required columns exist
                    missing_cols = [c for c in plugin.required_columns if c not in ticker_df.columns]
                    if missing_cols:
                        logger.warning(f"Plugin {plugin.plugin_name} missing columns {missing_cols} for {ticker}. Skipping this plugin.")
                        continue

                    ticker_df = plugin.apply(ticker_df)
                except Exception as e:
                    logger.error(f"Error applying plugin {plugin.plugin_name} to {ticker}: {e}")

            processed_dfs.append(ticker_df)

        if not processed_dfs:
            logger.warning("No tickers met the minimum data requirements. Feature store not updated.")
            return

        final_features_df = pd.concat(processed_dfs, ignore_index=True)

        # Merge back into feature_store or create it
        # Assuming we might want to store plugin features in the main feature_store or a separate table
        # Let's drop and recreate a temporary table for plugin features
        self.repo.con.execute("DROP TABLE IF EXISTS plugin_features")
        self.repo.con.execute("CREATE TABLE plugin_features AS SELECT * FROM final_features_df")
        logger.success(f"Plugin feature execution complete. Added {len(final_features_df)} rows to plugin_features.")
