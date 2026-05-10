"""
crawler_v2/gap/gap_queue.py — Priority queue for gap-fill tasks.

Higher-priority gaps are processed first.  Each gap is mapped to the
appropriate data types for re-crawling.
"""

import asyncio
from typing import List

from loguru import logger

from crawler_v2.gap.gap_detector import GapRecord

_GAP_TYPE_MAP = {
    "null_metric": ["financials"],
    "stale_data": ["all"],
    "missing_type": ["stock_prices", "executives"],
}


class GapQueue:
    """Async priority queue that processes data gaps in priority order."""

    def __init__(self):
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue()

    async def load_gaps(self, gaps: List[GapRecord]) -> None:
        """Enqueue all *gaps*.  Priority is negated so highest value
        is dequeued first (max-heap behaviour)."""
        for gap in gaps:
            await self.queue.put((
                -gap.priority,
                gap.ticker,
                gap.gap_type,
                gap.missing_fields,
            ))
        logger.info(f"Loaded {len(gaps)} gaps into queue")

    async def process(self, orchestrator) -> int:
        """Drain the queue, dispatching each gap to the orchestrator.

        Returns the number of gaps processed.
        """
        processed = 0
        while not self.queue.empty():
            priority, ticker, gap_type, fields = await self.queue.get()
            logger.info(
                f"Gap fill: {ticker} | type: {gap_type} | fields: {fields}"
            )
            try:
                data_types = self._map_gap(gap_type)
                await orchestrator.crawl_specific(
                    ticker=ticker, data_types=data_types
                )
                processed += 1
            except Exception as exc:
                logger.error(f"Gap fill failed for {ticker}: {exc}")
            finally:
                self.queue.task_done()
        return processed

    @staticmethod
    def _map_gap(gap_type: str) -> list:
        """Map a gap type to the data types that should be re-crawled."""
        return _GAP_TYPE_MAP.get(gap_type, ["all"])
