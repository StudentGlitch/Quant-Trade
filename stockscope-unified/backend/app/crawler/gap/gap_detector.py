"""
crawler_v2/gap/gap_detector.py — Detects data gaps after each batch:
  1. NULL critical fields (pe_ratio, roe, net_margin)
  2. Stale data (older than GAP_STALE_DAYS)
  3. Missing data types entirely (e.g. no stock_prices)

Results are returned as GapRecord objects sorted by priority.
"""

from dataclasses import dataclass
from typing import List, Optional

from loguru import logger

from crawler_v2.config import GAP_FILL_PRIORITY_FIELDS, GAP_STALE_DAYS

# SQL templates used by GapDetector.  These are executed via SQLAlchemy text().
_NULL_GAPS_SQL = """
    SELECT c.ticker, c.company_name,
           'null_metric' AS gap_type,
           10 AS priority
    FROM companies c
    LEFT JOIN (
        SELECT company_id,
               price_to_earnings, roe, eps
        FROM financials f1
        WHERE fiscal_year = (
            SELECT MAX(fiscal_year) FROM financials f2
            WHERE f2.company_id = f1.company_id
        )
    ) f ON c.id = f.company_id
    WHERE f.price_to_earnings IS NULL
       OR f.roe IS NULL
       OR f.eps IS NULL
"""

_STALE_GAPS_SQL = """
    SELECT c.ticker,
           'stale_data' AS gap_type,
           DATEDIFF(NOW(), MAX(cl.crawled_at)) AS days_stale,
           5 AS priority
    FROM companies c
    LEFT JOIN crawl_log cl
      ON c.ticker = cl.ticker
      AND cl.status = 'success'
    GROUP BY c.ticker
    HAVING days_stale > :stale_days
        OR days_stale IS NULL
"""

_MISSING_TYPE_SQL = """
    SELECT c.ticker,
           'missing_type' AS gap_type,
           15 AS priority
    FROM companies c
    WHERE c.id NOT IN (
        SELECT DISTINCT company_id
        FROM stock_prices
    )
"""


@dataclass
class GapRecord:
    ticker: str
    gap_type: str
    priority: int
    missing_fields: Optional[str] = None
    days_stale: Optional[int] = None


class GapDetector:
    """Scans the database for data gaps that need filling."""

    PRIORITY_FIELDS = GAP_FILL_PRIORITY_FIELDS.split(",")

    def __init__(self, db_session_factory=None):
        self._session_factory = db_session_factory

    def detect_gaps(self) -> List[GapRecord]:
        """Return all detected gaps, sorted by priority (highest first)."""
        gaps: List[GapRecord] = []

        if self._session_factory is None:
            logger.warning("No DB session factory — returning empty gaps")
            return gaps

        try:
            from sqlalchemy import text

            with self._session_factory() as session:
                # Gap type 1: NULL critical fields
                for row in session.execute(text(_NULL_GAPS_SQL)).fetchall():
                    gaps.append(GapRecord(
                        ticker=row.ticker,
                        gap_type="null_metric",
                        priority=10,
                        missing_fields=",".join(self.PRIORITY_FIELDS),
                    ))

                # Gap type 2: stale data
                for row in session.execute(
                    text(_STALE_GAPS_SQL), {"stale_days": GAP_STALE_DAYS}
                ).fetchall():
                    gaps.append(GapRecord(
                        ticker=row.ticker,
                        gap_type="stale_data",
                        priority=5,
                        days_stale=getattr(row, "days_stale", None),
                    ))

                # Gap type 3: missing data types
                for row in session.execute(text(_MISSING_TYPE_SQL)).fetchall():
                    gaps.append(GapRecord(
                        ticker=row.ticker,
                        gap_type="missing_type",
                        priority=15,
                    ))

        except Exception as exc:
            logger.error(f"Gap detection failed: {exc}")

        gaps.sort(key=lambda g: g.priority, reverse=True)
        logger.info(f"Detected {len(gaps)} gaps")
        return gaps
