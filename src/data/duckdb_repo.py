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
