"""Compatibility wrapper for the revised IDX annual report crawler."""

from __future__ import annotations

from .cli import main
from .core import (
    AnnualReport,
    IDXBlockedError,
    IDXError,
    absolute_idx_url,
    extract_result_rows,
    is_blocked_response,
    normalize_reports,
    parse_cookie_header,
)
from .core import build_session as build_session
from .core import run_crawl as run_crawl
from .utils import parse_years

_absolute_idx_url = absolute_idx_url
_extract_result_rows = extract_result_rows
_parse_years = parse_years
_reports_from_rows = lambda rows, fallback_ticker, fallback_year: normalize_reports(  # noqa: E731
    rows,
    fallback_ticker=fallback_ticker,
    fallback_year=fallback_year,
)

__all__ = [
    "AnnualReport",
    "IDXBlockedError",
    "IDXError",
    "build_session",
    "is_blocked_response",
    "main",
    "parse_cookie_header",
    "run_crawl",
]


if __name__ == "__main__":
    raise SystemExit(main())
