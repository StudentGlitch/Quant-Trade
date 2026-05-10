"""CLI entry point for the IDX annual report crawler."""

from __future__ import annotations

import argparse
import os
import sys

from .core import IDXError, run_crawl
from .utils import load_tickers_from_sources, parse_years


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="idx-annual-reports",
        description="Download IDX annual report PDFs sequentially.",
    )
    parser.add_argument("tickers", nargs="*", help="Explicit 4-letter IDX tickers")
    parser.add_argument("--tickers-file", help="File with one ticker per line")
    parser.add_argument("--years", required=True, help="Year list or range, e.g. 2023 or 2020-2024")
    parser.add_argument(
        "--metadata-path",
        default="data/metadata.csv",
        help="CSV metadata state file",
    )
    parser.add_argument(
        "--reports-dir",
        default="data/reports",
        help="Directory for downloaded PDF files",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Use isolated smoke-test paths under data/reports_smoke and data/reports_smoke.csv",
    )
    parser.add_argument(
        "--cookie",
        default=os.getenv("IDX_COOKIE", ""),
        help="Manual browser cookie header",
    )
    parser.add_argument(
        "--no-browser-fallback",
        action="store_true",
        help="Disable Playwright fallback when requests is blocked or reset",
    )
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        tickers = load_tickers_from_sources(args.tickers, args.tickers_file)
        years = parse_years(args.years)
    except ValueError as exc:
        print(f"idx-annual-reports: {exc}", file=sys.stderr)
        return 2

    metadata_path = args.metadata_path
    reports_dir = args.reports_dir
    if args.smoke:
        metadata_path = "data/reports_smoke.csv"
        reports_dir = "data/reports_smoke"

    try:
        results = run_crawl(
            tickers,
            years,
            metadata_path=metadata_path,
            reports_dir=reports_dir,
            cookie_header=args.cookie,
            timeout=args.timeout,
            use_browser_fallback=not args.no_browser_fallback,
        )
    except KeyboardInterrupt:
        print("idx-annual-reports: interrupted by user", file=sys.stderr)
        return 130
    except IDXError as exc:
        print(f"idx-annual-reports: {exc}", file=sys.stderr)
        return 1

    success = sum(1 for item in results if item.status == "Success")
    skipped = sum(1 for item in results if item.status == "Skipped")
    blocked = sum(1 for item in results if item.status.startswith("Blocked"))
    failed = sum(1 for item in results if item.status.startswith("Failed") or item.status == "File_Not_Found")
    print(
        "completed="
        f"{len(results)} success={success} skipped={skipped} blocked={blocked} failed={failed}"
    )
    return 0
