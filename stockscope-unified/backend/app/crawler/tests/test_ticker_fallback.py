"""Tests for robust all-mode ticker fallback behavior."""

from pathlib import Path

from crawler_v2 import main as crawler_main


def test_normalize_tickers_dedupes_and_uppercases():
    raw = ["bbca", " BBCA ", "tlkm", "", "  "]
    result = crawler_main._normalize_tickers(raw)
    assert result == ["BBCA", "TLKM"]


def test_is_strong_universe_threshold():
    strong = [f"T{i:04d}" for i in range(900)]
    weak = [f"T{i:04d}" for i in range(899)]
    assert crawler_main._is_strong_universe(strong, min_tickers=900)
    assert not crawler_main._is_strong_universe(weak, min_tickers=900)


def test_snapshot_roundtrip(tmp_path, monkeypatch):
    snapshot_path = tmp_path / "ticker_snapshot.json"
    monkeypatch.setattr(crawler_main, "TICKER_SNAPSHOT_PATH", snapshot_path)

    tickers = ["BBCA", "BBRI", "TLKM"]
    crawler_main._save_ticker_snapshot(tickers, source="unit_test")

    loaded = crawler_main._load_tickers_from_snapshot()
    assert loaded == tickers


def test_snapshot_missing_returns_empty(tmp_path, monkeypatch):
    snapshot_path = tmp_path / "missing_snapshot.json"
    monkeypatch.setattr(crawler_main, "TICKER_SNAPSHOT_PATH", snapshot_path)

    assert crawler_main._load_tickers_from_snapshot() == []
