import pandas as pd
from pytrends.request import TrendReq
import pageviewapi
from loguru import logger
from typing import List, Optional
from datetime import datetime
import time
from .duckdb_repo import DuckDBRepo
from requests.exceptions import ConnectionError, Timeout


WIKI_MAPPING = {
    "BBCA.JK": "Bank_Central_Asia",
    "TLKM.JK": "Telkom_Indonesia",
    "ASII.JK": "Astra_International",
    "BMRI.JK": "Bank_Mandiri",
    "AAPL": "Apple_Inc.",
    "MSFT": "Microsoft",
    "NVDA": "Nvidia",
    "GOOGL": "Alphabet_Inc."
}

class AltDataClient:
    """
    Client for fetching Alternative Data (PRD Phase 1).
    Google Trends (Retail Interest) and Wikipedia Pageviews (Public Attention).
    """
    def __init__(self, repo: DuckDBRepo):
        self.repo = repo
        self._pytrends = None
        self.google_rate_limited = False

    def _get_pytrends(self) -> Optional[TrendReq]:
        """Lazy load pytrends with retry logic for network blips (PRD Bug Fix)."""
        if self._pytrends is None:
            retries = 3
            for attempt in range(retries):
                try:
                    # Timeout as tuple: (connect timeout, read timeout)
                    self._pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 25))
                    return self._pytrends
                except (ConnectionError, Timeout) as e:
                    logger.warning(f"Network error initializing pytrends (Attempt {attempt+1}/{retries}): {e}")
                    if attempt < retries - 1:
                        time.sleep(5 * (attempt + 1)) # Backoff
            logger.error("Failed to initialize pytrends after retries. Alt-data will be skipped.")
            return None
        return self._pytrends


    def _fetch_and_store_google_trends(self, ticker: str, keyword: str, start_date: str):
        if self.google_rate_limited:
            logger.warning(f"Google Trends circuit breaker active, skipping {keyword}")
            return

        try:
            pytrends = self._get_pytrends()
            if pytrends:
                logger.info(f"Pulling Google Trends for '{keyword}'...")
                pytrends.build_payload([keyword], cat=0, timeframe=f"{start_date} {datetime.now().strftime('%Y-%m-%d')}")
                trends_df = pytrends.interest_over_time()

                if not trends_df.empty:
                    trends_df = trends_df[[keyword]].rename(columns={keyword: 'google_trends_score'})
                    trends_df.index.name = 'date'
                    trends_df = trends_df.reset_index()
                    trends_df['ticker'] = ticker
                    trends_df['date'] = pd.to_datetime(trends_df['date']).dt.date  # noqa: F841

                    # Upsert Trends
                    self.repo.con.execute("CREATE TABLE IF NOT EXISTS alt_google_trends (date DATE, ticker VARCHAR, google_trends_score DOUBLE, PRIMARY KEY (ticker, date))")
                    self.repo.con.execute("""
                        INSERT OR REPLACE INTO alt_google_trends (date, ticker, google_trends_score)
                        SELECT date, ticker, google_trends_score FROM trends_df
                    """)
            else:
                logger.warning(f"Skipping Google Trends for {ticker} due to initialization failure.")
        except Exception as e:
            if "429" in str(e):
                self.google_rate_limited = True
                logger.warning("Google Trends circuit breaker tripped for this cycle. Skipping Trends fetching for remaining tickers.")
            else:
                logger.error(f"Failed to fetch Google Trends for {ticker}: {e}")

    def _fetch_and_store_wiki_pageviews(self, ticker: str, keyword: str, start_date: str):
        wiki_start = start_date.replace("-", "")
        wiki_end = datetime.now().strftime("%Y%m%d")

        wiki_entity = WIKI_MAPPING.get(ticker, keyword)
        logger.info(f"Pulling Wiki Pageviews for '{wiki_entity}' (original ticker: {ticker})...")
        # We use 'en.wikipedia' as a proxy for global attention
        try:
            views = pageviewapi.per_article('en.wikipedia', wiki_entity, wiki_start, wiki_end,
                                          access='all-access', agent='all-agents', granularity='daily')

            wiki_data = []
            for item in views.get('items', []):
                wiki_data.append({
                    'date': datetime.strptime(item['timestamp'], "%Y%m%d%H").date(),
                    'wiki_views': item['views'],
                    'ticker': ticker
                })
        except Exception as wiki_exc:
            logger.warning(f"Wiki fetch failed for {wiki_entity}: {wiki_exc}")
            wiki_data = []

        if wiki_data:
            wiki_df = pd.DataFrame(wiki_data)  # noqa: F841
            self.repo.con.execute("CREATE TABLE IF NOT EXISTS alt_wiki_views (date DATE, ticker VARCHAR, wiki_views BIGINT, PRIMARY KEY (ticker, date))")
            self.repo.con.execute("""
                INSERT OR REPLACE INTO alt_wiki_views (date, ticker, wiki_views)
                SELECT date, ticker, wiki_views FROM wiki_df
            """)

    def fetch_and_store(self, tickers: List[str], start_date: str):
        """Fetch Google Trends and Wiki Pageviews (PRD 7 Phase 1)."""
        logger.info(f"Fetching Alternative Data for {len(tickers)} tickers...")

        # Simplified mapping for search keywords
        ticker_keywords = {t: t.split('.')[0] for t in tickers}

        for ticker, keyword in ticker_keywords.items():
            self._fetch_and_store_google_trends(ticker, keyword, start_date)
            self._fetch_and_store_wiki_pageviews(ticker, keyword, start_date)

            # Increased delay to respect rate limits (Google is sensitive)
            time.sleep(10)

    def get_merged_alt_data(self, ticker: str) -> pd.DataFrame:
        """Merge trends and views from DuckDB."""
        return self.repo.con.execute("""
            SELECT t.date, t.ticker, t.google_trends_score, v.wiki_views
            FROM alt_google_trends t
            LEFT JOIN alt_wiki_views v ON t.date = v.date AND t.ticker = v.ticker
            WHERE t.ticker = ?
            ORDER BY t.date
        """, [ticker]).df()

    def get_all_merged_alt_data(self) -> pd.DataFrame:
        """Merge trends and views from DuckDB for all tickers."""
        return self.repo.con.execute("""
            SELECT t.date, t.ticker, t.google_trends_score, v.wiki_views
            FROM alt_google_trends t
            LEFT JOIN alt_wiki_views v ON t.date = v.date AND t.ticker = v.ticker
            ORDER BY t.ticker, t.date
        """).df()
