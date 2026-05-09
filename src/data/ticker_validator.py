class TickerValidator:
    """
    Validates ticker symbols to ensure they meet the IDX standard.
    Specifically checks for the `.JK` suffix required for Yahoo Finance mapping.
    """

    @staticmethod
    def is_valid_idx_ticker(ticker: str) -> bool:
        """
        Check if a given ticker is a valid IDX ticker format.
        Valid formats are typically 4 uppercase letters followed by '.JK'.
        """
        if not isinstance(ticker, str):
            return False

        # Match exactly 4 letters, optionally followed by more characters, then '.JK'
        # Or more simply, just ensure it ends with '.JK' and has some base ticker
        if not ticker.endswith('.JK'):
            return False

        base = ticker[:-3]
        if not base.isalpha() or not base.isupper():
            return False

        return True

    @staticmethod
    def format_to_idx(ticker: str) -> str:
        """
        Takes a raw ticker and attempts to format it to the IDX standard (e.g., adding .JK).
        """
        if not isinstance(ticker, str):
            return ""

        ticker = ticker.strip().upper()
        if not ticker.endswith('.JK'):
            ticker += '.JK'

        return ticker
