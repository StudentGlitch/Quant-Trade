"""Shared utility helpers for the IDX annual report crawler."""

from __future__ import annotations

import csv
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

from .ticker_validator import filter_valid_tickers


CSV_FIELDS = (
    "ticker",
    "year",
    "file_path",
    "status",
    "checksum",
    "timestamp",
)


def parse_years(raw_years: str) -> list[int]:
    years: list[int] = []
    for part in raw_years.split(","):
        value = part.strip()
        if not value:
            continue
        if "-" in value:
            start_text, end_text = value.split("-", 1)
            start = int(start_text.strip())
            end = int(end_text.strip())
            step = 1 if end >= start else -1
            years.extend(range(start, end + step, step))
        else:
            years.append(int(value))
    return years


def load_tickers_from_sources(
    tickers: list[str] | None = None,
    tickers_file: str | None = None,
) -> list[str]:
    raw_tickers = list(tickers or [])
    if tickers_file:
        with open(tickers_file, encoding="utf-8") as handle:
            for line in handle:
                value = line.strip().split(",", 1)[0].strip()
                if value and not value.startswith("#"):
                    raw_tickers.append(value)
    cleaned = filter_valid_tickers(raw_tickers)
    if not cleaned:
        raise ValueError("Provide at least one valid 4-letter IDX ticker.")
    return cleaned


def ensure_parent_dir(path: str | Path) -> Path:
    resolved = Path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def ensure_dir(path: str | Path) -> Path:
    resolved = Path(path)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def checksum_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 128), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sanitize_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._ -]+", "_", value.strip()).strip(" ._") or "file"


def read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    csv_path = Path(path)
    if not csv_path.exists():
        return []
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def append_csv_row(path: str | Path, row: dict[str, str]) -> None:
    csv_path = ensure_parent_dir(path)
    write_header = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)
