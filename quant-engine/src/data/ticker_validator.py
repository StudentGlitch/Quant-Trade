import re

TICKER_PATTERN = re.compile(r"^[A-Z]{4}$")

def normalize_ticker(raw: str) -> str:
    """Extract 4-letter stock code and append Yahoo Finance suffix (PRD 0.1.3)."""
    clean = raw.strip().upper()
    if TICKER_PATTERN.fullmatch(clean):
        return f"{clean}.JK"
    # If it already has a suffix, just return uppercase
    return clean

def is_idx_ticker(ticker: str) -> bool:
    return ticker.endswith(".JK")
