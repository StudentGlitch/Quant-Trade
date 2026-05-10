"""
crawler_v2/schema/fallback_router.py — Automatically routes to backup
data sources when the primary source fails or changes.
"""

from typing import Dict, List, Optional

from loguru import logger


# Default fallback chains — configurable per data type.
SOURCE_FALLBACK_CHAIN: Dict[str, List[str]] = {
    "company_profile": [
        "idx_source",
        "yfinance_source",
        "stockbit_source",
    ],
    "financials": [
        "yfinance_source",
        "idx_source",
        "pdf_source",
    ],
    "stock_prices": [
        "yfinance_source",
    ],
    "executives": [
        "idx_source",
        "stockbit_source",
    ],
    "news": [
        "bisnis_source",
        "idx_source",
    ],
    "esg": [
        "idx_source",
        "pdf_source",
    ],
}


class EmptyResult:
    """Placeholder returned when every source in the chain fails."""

    def __init__(self, ticker: str, data_type: str):
        self.ticker = ticker
        self.data_type = data_type
        self.source_name = "none"
        self.data: dict = {}

    def has_data(self) -> bool:
        return False


class FallbackRouter:
    """Tries each source in the fallback chain until one succeeds."""

    def __init__(
        self,
        sources: Optional[Dict] = None,
        chains: Optional[Dict[str, List[str]]] = None,
    ):
        self.sources: Dict = sources or {}
        self.chains: Dict[str, List[str]] = chains or SOURCE_FALLBACK_CHAIN

    async def fetch_with_fallback(
        self,
        ticker: str,
        data_type: str,
        session_mgr=None,
    ):
        """Walk the fallback chain for *data_type*, returning the first
        successful result.  Returns an ``EmptyResult`` if all fail."""
        chain = self.chains.get(data_type, [])

        for source_name in chain:
            source = self.sources.get(source_name)
            if source is None:
                continue
            try:
                result = await source.fetch(ticker, session_mgr=session_mgr)
                if result and hasattr(result, "has_data") and result.has_data():
                    result.source_name = source_name
                    return result
            except Exception as exc:
                logger.warning(
                    f"{source_name} failed for "
                    f"{ticker}/{data_type}: {exc}"
                )
                continue

        logger.error(f"All sources failed for {ticker}/{data_type}")
        return EmptyResult(ticker, data_type)
