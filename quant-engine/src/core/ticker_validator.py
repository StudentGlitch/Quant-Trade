"""Ticker validation helpers for explicit IDX ticker inputs."""

from __future__ import annotations

import re


TICKER_PATTERN = re.compile(r"^[A-Z]{4}$")


def normalize_ticker(raw: str) -> str:
    return raw.strip().upper()


def is_valid_ticker(raw: str) -> bool:
    return bool(TICKER_PATTERN.fullmatch(normalize_ticker(raw)))


def filter_valid_tickers(values: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        ticker = normalize_ticker(value)
        if not is_valid_ticker(ticker):
            continue
        if ticker in seen:
            continue
        seen.add(ticker)
        output.append(ticker)
    return output
