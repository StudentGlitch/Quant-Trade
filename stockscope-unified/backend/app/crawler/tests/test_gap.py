"""
Tests for crawler_v2/gap/ modules.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from crawler_v2.gap.gap_detector import GapDetector, GapRecord
from crawler_v2.gap.gap_queue import GapQueue


class TestGapDetector:
    def test_empty_when_no_session(self):
        detector = GapDetector(db_session_factory=None)
        gaps = detector.detect_gaps()
        assert gaps == []

    def test_priority_fields_from_config(self):
        detector = GapDetector()
        assert "pe_ratio" in detector.PRIORITY_FIELDS or len(detector.PRIORITY_FIELDS) > 0


class TestGapQueue:
    @pytest.mark.asyncio
    async def test_load_and_process(self):
        gaps = [
            GapRecord(ticker="BBCA", gap_type="null_metric", priority=10),
            GapRecord(ticker="TLKM", gap_type="missing_type", priority=15),
        ]
        queue = GapQueue()
        await queue.load_gaps(gaps)
        assert queue.queue.qsize() == 2

    @pytest.mark.asyncio
    async def test_process_calls_orchestrator(self):
        gaps = [
            GapRecord(ticker="ASII", gap_type="stale_data", priority=5),
        ]
        queue = GapQueue()
        await queue.load_gaps(gaps)

        mock_orch = AsyncMock()
        processed = await queue.process(mock_orch)
        assert processed == 1
        mock_orch.crawl_specific.assert_called_once()

    @pytest.mark.asyncio
    async def test_highest_priority_first(self):
        gaps = [
            GapRecord(ticker="LOW", gap_type="stale_data", priority=5),
            GapRecord(ticker="HIGH", gap_type="missing_type", priority=15),
        ]
        queue = GapQueue()
        await queue.load_gaps(gaps)

        # The first item dequeued should be the highest priority (negated)
        item = await queue.queue.get()
        assert item[1] == "HIGH"  # ticker of highest priority
