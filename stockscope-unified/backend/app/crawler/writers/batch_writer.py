"""
crawler_v2/writers/batch_writer.py — Batch database writer.

Groups INSERT/UPDATE operations into batches of BATCH_SIZE to avoid
per-row overhead.  Also provides the crawl-log helper that writes in
the exact same format as the v1 crawler so the pipeline watcher
continues to trigger correctly.
"""

import time
from typing import Any, Dict, List, Optional

from loguru import logger

from crawler_v2.config import BATCH_SIZE


class BatchWriter:
    """Accumulates rows and flushes them in batches."""

    def __init__(self, session_factory, batch_size: int = BATCH_SIZE):
        self._session_factory = session_factory
        self._batch_size = batch_size
        self._buffer: Dict[str, List[Any]] = {}

    def add(self, model_class, data: dict) -> None:
        """Add a single row to the buffer for *model_class*."""
        table = model_class.__tablename__
        if table not in self._buffer:
            self._buffer[table] = []
        self._buffer[table].append((model_class, data))
        if len(self._buffer[table]) >= self._batch_size:
            self._flush_table(table)

    def flush_all(self) -> Dict[str, int]:
        """Flush every buffered table.  Returns ``{table: rows_written}``."""
        counts: Dict[str, int] = {}
        for table in list(self._buffer):
            counts[table] = self._flush_table(table)
        return counts

    def _flush_table(self, table: str) -> int:
        items = self._buffer.pop(table, [])
        if not items:
            return 0
        try:
            with self._session_factory() as session:
                for model_cls, data in items:
                    session.add(model_cls(**data))
                session.commit()
            logger.debug(f"Flushed {len(items)} rows to {table}")
            return len(items)
        except Exception as exc:
            logger.error(f"Batch write to {table} failed: {exc}")
            return 0


def log_crawl(
    session_factory,
    ticker: str,
    phase: str,
    status: str,
    inserted: int = 0,
    updated: int = 0,
    error: Optional[str] = None,
    duration: float = 0.0,
    iteration: int = 1,
) -> None:
    """Write a crawl_log row in the exact same schema as the v1 crawler.

    The ``phase`` value is prefixed with ``v2_`` so the dashboard can
    distinguish v1 from v2 entries while the pipeline watcher still
    sees them as valid crawl events.
    """
    try:
        from sqlalchemy import text

        with session_factory() as session:
            session.execute(
                text("""
                    INSERT INTO crawl_log
                    (ticker, phase, status,
                     records_inserted, records_updated,
                     error_message, duration_seconds,
                     iteration, crawled_at)
                    VALUES
                    (:ticker, :phase, :status,
                     :inserted, :updated,
                     :error, :duration,
                     :iteration, NOW())
                """),
                {
                    "ticker": ticker,
                    "phase": phase,
                    "status": status,
                    "inserted": inserted,
                    "updated": updated,
                    "error": error,
                    "duration": round(duration, 2),
                    "iteration": iteration,
                },
            )
            session.commit()
    except Exception as exc:
        logger.warning(f"Could not write crawl_log entry: {exc}")
