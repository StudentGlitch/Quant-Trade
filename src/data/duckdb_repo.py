import duckdb
from pathlib import Path
from loguru import logger

class DuckDBRepo:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.con = None

    def __enter__(self):
        """Strict Context Manager initialization (PRD Bug Fix)."""
        if self.con is None:
            logger.info(f"Opening DuckDB connection: {self.db_path}")
            self.con = duckdb.connect(str(self.db_path))
            self._init_schema()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Strict Context Manager teardown (PRD Bug Fix)."""
        self.close()

    def _init_schema(self):
        """Initialize the DuckDB schema as per PRD 5.1."""
        logger.info("Initializing DuckDB schema...")
        

        # IDX Metadata
        self.con.execute('''
            CREATE TABLE IF NOT EXISTS idx_metadata (
                ticker VARCHAR PRIMARY KEY,
                sector VARCHAR,
                listing_date DATE,
                status VARCHAR,
                avg_daily_volume BIGINT,
                market_cap BIGINT
            );
        ''')

        # Core Price Data
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv_daily (
                ticker VARCHAR,
                date DATE,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                adj_close DOUBLE,
                volume BIGINT,
                PRIMARY KEY (ticker, date)
            );
        """)

        # Macro Economic Indicators
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS macro_data (
                date DATE PRIMARY KEY, 
                us_10y_yield DOUBLE, 
                us_2y_yield DOUBLE, 
                us_cpi DOUBLE, 
                us_m2 DOUBLE, 
                vix_close DOUBLE
            )
        """)

        # Alternative Data
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS alt_google_trends (
                date DATE,
                ticker VARCHAR,
                google_trends_score DOUBLE,
                PRIMARY KEY (ticker, date)
            );
        """)
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS alt_wiki_views (
                date DATE,
                ticker VARCHAR,
                wiki_views BIGINT,
                PRIMARY KEY (ticker, date)
            );
        """)

        # Intelligent Scrape Store (ScrapeGraphAI)
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS alt_scraped_sentiment (
                date DATE,
                ticker VARCHAR,
                sentiment_score DOUBLE,
                source_url VARCHAR,
                PRIMARY KEY (ticker, date)
            );
        """)

        # Feature Store
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS feature_store (
                ticker VARCHAR,
                date DATE,
                ret_1d DOUBLE,
                volatility_20d DOUBLE,
                rsi_14 DOUBLE,
                macd_hist DOUBLE,
                atr_14_pct DOUBLE,
                z_score_ret_1m DOUBLE,
                feat_wiki_spike_20d DOUBLE,
                feat_google_momentum_20d DOUBLE,
                feat_google_roc_5d DOUBLE,
                target_fwd_ret_5d DOUBLE,
                target_fwd_ret_5d_bin INT,
                PRIMARY KEY (ticker, date)
            );
        """)

        # Backtest Execution Ledger (Updated for Janus + Vibe-Trading)
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS paper_trades (
                trade_id UUID PRIMARY KEY,
                ticker VARCHAR,
                signal_date DATE,
                execution_date DATE,
                ml_signal DOUBLE,
                llm_signal DOUBLE,
                ml_weight DOUBLE,
                llm_weight DOUBLE,
                final_blended_signal DOUBLE,
                final_direction INT,
                vibe VARCHAR,
                chain_of_thought TEXT,
                execution_price DOUBLE,
                position_size DOUBLE,
                transaction_cost DOUBLE,
                status VARCHAR
            );
        """)
        logger.info("DuckDB schema initialized.")

    def execute(self, query: str, params: list = None):
        if self.con is None:
            raise RuntimeError("Database connection is not open. Use 'with DuckDBRepo(...) as repo:'")
        return self.con.execute(query, params)

    def close(self):
        """Explicitly close the DuckDB connection to release the file lock (PRD Bug Fix)."""
        if hasattr(self, 'con') and self.con is not None:
            try:
                self.con.close()
                self.con = None
                logger.info("DuckDB connection closed successfully.")
            except Exception as e:
                logger.warning(f"Failed to close DuckDB connection cleanly: {e}")
