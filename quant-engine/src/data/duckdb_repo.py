import duckdb
from pathlib import Path
from loguru import logger
import os

class DuckDBRepo:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.con = None

    def __enter__(self):
        """Strict Context Manager initialization (PRD Bug Fix)."""
        if self.con is None:
            use_s3 = os.getenv("USE_S3_DATALAKE", "false").lower() == "true"
            
            if use_s3:
                logger.info("Initializing DuckDB with S3 Data Lake support (:memory:)...")
                self.con = duckdb.connect(database=':memory:')
                
                # S3 setup per PRD 6.2/9.2
                self.con.execute("INSTALL httpfs;")
                self.con.execute("LOAD httpfs;")
                s3_endpoint = os.getenv("S3_ENDPOINT_URL", "minio:9000").replace("http://", "").replace("https://", "")
                self.con.execute(f"SET s3_endpoint='{s3_endpoint}';")
                self.con.execute(f"SET s3_access_key_id='{os.getenv('S3_ACCESS_KEY_ID', 'swarm_admin')}';")
                self.con.execute(f"SET s3_secret_access_key='{os.getenv('S3_SECRET_ACCESS_KEY', 'swarm_secret')}';")
                use_ssl = 'true' if os.getenv("S3_USE_SSL", "false").lower() == "true" else 'false'
                self.con.execute(f"SET s3_use_ssl={use_ssl};")
                self.con.execute("SET s3_url_style='path';")
                
                self._init_schema() # Needs to recreate in memory
            else:
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
        
        schema_path = Path(__file__).parent / "schema.sql"
        try:
            with open(schema_path, "r") as f:
                schema_sql = f.read()
            self.con.execute(schema_sql)
        except Exception as e:
            logger.error(f"Failed to initialize schema from {schema_path}: {e}")
            raise

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

    def get_parquet_data(self, base_dir: Path) -> 'pd.DataFrame':
        """
        Query the Hive-partitioned Parquet directory as a virtual table (PRD Phase 0.5).
        """
        import pandas as pd
        use_s3 = os.getenv("USE_S3_DATALAKE", "false").lower() == "true"
        
        try:
            if use_s3:
                logger.info("Streaming Parquet from S3 bucket: quant-market-data")
                return self.execute("SELECT * FROM read_parquet('s3://quant-market-data/ticker=*/data.parquet', hive_partitioning=1)").df()
            else:
                parquet_path = str(base_dir / "storage" / "parquet_data" / "ticker=*" / "data.parquet")
                # Ensure path uses forward slashes for DuckDB globbing
                parquet_path = parquet_path.replace('\\', '/')
                
                # Check if any parquets exist yet
                if not list((base_dir / "storage" / "parquet_data").glob("ticker=*/data.parquet")):
                    return pd.DataFrame()
                    
                query = f"SELECT * FROM read_parquet('{parquet_path}', hive_partitioning=1)"
                return self.execute(query).df()
        except Exception as e:
            logger.error(f"Error querying parquet data: {e}")
            return pd.DataFrame()
