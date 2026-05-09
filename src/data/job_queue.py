import sqlite3
import logging
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger("job_queue")

class JobQueue:
    """Stateful tracking of the 900+ ticker queue (PRD 5.2)."""
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fetch_jobs (
                    ticker VARCHAR PRIMARY KEY,
                    priority INT DEFAULT 1,
                    status VARCHAR DEFAULT 'PENDING',
                    retry_count INT DEFAULT 0,
                    last_attempt TIMESTAMP,
                    error_log TEXT
                );
            """)
            conn.commit()

    def add_jobs(self, tickers: List[str], priority: int = 1):
        with sqlite3.connect(self.db_path) as conn:
            # We use INSERT OR IGNORE so we don't reset existing jobs
            conn.executemany(
                "INSERT OR IGNORE INTO fetch_jobs (ticker, priority) VALUES (?, ?)",
                [(t, priority) for t in tickers]
            )
            conn.commit()

    def get_pending_jobs(self, limit: int = 5) -> List[str]:
        with sqlite3.connect(self.db_path) as conn:
            # PRD 0.4.1: Order by priority ASC
            cursor = conn.execute(
                "SELECT ticker FROM fetch_jobs WHERE status = 'PENDING' ORDER BY priority ASC LIMIT ?",
                (limit,)
            )
            return [row[0] for row in cursor.fetchall()]

    def update_job_status(self, ticker: str, status: str, error_log: str = None):
        with sqlite3.connect(self.db_path) as conn:
            if status == 'FAIL':
                conn.execute("""
                    UPDATE fetch_jobs 
                    SET retry_count = retry_count + 1, last_attempt = CURRENT_TIMESTAMP, error_log = ? 
                    WHERE ticker = ?
                """, (error_log, ticker))
                
                # PRD 0.4.4: Set to PENDING if retries <= 3, else FAILED
                conn.execute("""
                    UPDATE fetch_jobs 
                    SET status = CASE WHEN retry_count > 3 THEN 'FAILED' ELSE 'PENDING' END
                    WHERE ticker = ?
                """, (ticker,))
            else:
                conn.execute(
                    "UPDATE fetch_jobs SET status = ?, last_attempt = CURRENT_TIMESTAMP WHERE ticker = ?",
                    (status, ticker)
                )
            conn.commit()
