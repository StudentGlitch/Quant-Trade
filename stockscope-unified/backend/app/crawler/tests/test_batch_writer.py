"""
Tests for crawler_v2/writers/batch_writer.py
"""

from unittest.mock import MagicMock, patch

import pytest

from crawler_v2.writers.batch_writer import BatchWriter


class FakeModel:
    __tablename__ = "fake_table"

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestBatchWriter:
    def test_add_and_flush(self):
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        def session_factory():
            return mock_session

        writer = BatchWriter(session_factory, batch_size=10)
        writer.add(FakeModel, {"name": "test"})
        assert "fake_table" in writer._buffer

        counts = writer.flush_all()
        assert counts.get("fake_table", 0) == 1

    def test_auto_flush_at_batch_size(self):
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        def session_factory():
            return mock_session

        writer = BatchWriter(session_factory, batch_size=2)
        writer.add(FakeModel, {"name": "a"})
        assert "fake_table" in writer._buffer
        writer.add(FakeModel, {"name": "b"})
        # Auto-flushed at batch_size=2
        assert "fake_table" not in writer._buffer
