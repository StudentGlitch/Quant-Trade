import csv
import sqlite3
import requests
from loguru import logger
from .duckdb_repo import DuckDBRepo
from .ticker_validator import TickerValidator

class UniverseManager:
    """
    Manages the IDX universe. Fetches active tickers (with CSV fallback),
    applies filters, populates DuckDB metadata, and initializes the SQLite job queue.
    """
    def __init__(self, duckdb_repo: DuckDBRepo, job_queue_path: str = "storage/db/job_queue.sqlite", fallback_csv_path: str = "config/default_idx_universe.csv"):
        self.repo = duckdb_repo
        self.job_queue_path = job_queue_path
        self.fallback_csv_path = fallback_csv_path
        self._init_job_queue()
        self._init_metadata_schema()

    def _init_job_queue(self):
        """Initializes the SQLite job queue schema."""
        conn = sqlite3.connect(self.job_queue_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fetch_jobs (
                ticker VARCHAR PRIMARY KEY,
                status VARCHAR DEFAULT 'PENDING',
                last_attempt TIMESTAMP,
                error_log TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def _init_metadata_schema(self):
        self.repo.con.execute('''
            CREATE TABLE IF NOT EXISTS idx_metadata (
                ticker VARCHAR PRIMARY KEY,
                sector VARCHAR,
                listing_date DATE,
                status VARCHAR,
                avg_daily_volume BIGINT,
                market_cap BIGINT
            )
        ''')

    def fetch_listed_companies(self) -> list[dict]:
        """
        Attempts to fetch listed companies from the IDX JSON endpoint.
        Falls back to a static CSV if blocked by Cloudflare or network issues.
        """
        url = "https://www.idx.co.id/primary/ListedCompany/GetCompanyProfiles"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.idx.co.id/en/listed-companies/company-profiles"
        }

        try:
            logger.info("Attempting to fetch listed companies from IDX API...")
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            companies = []
            # Parse response, assuming structure has a 'data' array or similar.
            # This parsing might need adjustment based on exact real API structure.
            raw_profiles = data.get("data", [])
            if not raw_profiles and isinstance(data, list):
                raw_profiles = data

            for profile in raw_profiles:
                # Map fields defensively. Some might be missing.
                companies.append({
                    "ticker": profile.get("TickerCode", "") or profile.get("Symbol", ""),
                    "sector": profile.get("Sector", "Unknown"),
                    "listing_date": profile.get("ListingDate", "1900-01-01")[:10], # Truncate time if present
                    "status": "Active", # Assume active if listed
                    "avg_daily_volume": 0, # Often separate API, fallback to 0 to bypass filter or we'd need another call
                    "market_cap": 0
                })

            if companies:
                logger.success(f"Successfully fetched {len(companies)} companies from API.")
                return companies
            else:
                logger.warning("API returned empty data.")

        except Exception as e:
            logger.warning(f"Failed to fetch from IDX API: {e}. Falling back to CSV.")

        return self._fetch_from_csv()

    def _fetch_from_csv(self) -> list[dict]:
        """Reads the fallback CSV."""
        companies = []
        try:
            with open(self.fallback_csv_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    companies.append({
                        "ticker": row.get("ticker", ""),
                        "sector": row.get("sector", "Unknown"),
                        "listing_date": row.get("listing_date", "1900-01-01"),
                        "status": row.get("status", "Active"),
                        "avg_daily_volume": int(row.get("avg_daily_volume", 0)),
                        "market_cap": int(row.get("market_cap", 0))
                    })
            logger.success(f"Loaded {len(companies)} companies from fallback CSV.")
        except Exception as e:
            logger.error(f"Failed to load fallback CSV: {e}")
        return companies

    def update_universe(self, min_adv: int, min_market_cap: int):
        """
        Populates the DuckDB metadata table and pushes jobs to the SQLite queue.
        """
        companies = self.fetch_listed_companies()

        valid_tickers = []
        for comp in companies:
            ticker = TickerValidator.format_to_idx(comp['ticker'])
            if not TickerValidator.is_valid_idx_ticker(ticker):
                logger.warning(f"Invalid ticker format: {comp['ticker']}, skipping.")
                continue

            # Note: API might not provide adv/mcap immediately. In a real system, we might
            # do a secondary fetch for volume/mcap. For this phase, if ADV/MCAP is 0 (from API),
            # we might inadvertently filter them out. If using CSV, they will pass.
            if comp.get('avg_daily_volume', 0) < min_adv and comp.get('avg_daily_volume', 0) != 0:
                logger.debug(f"Skipping {ticker}: ADV {comp.get('avg_daily_volume')} < {min_adv}")
                continue

            if comp.get('market_cap', 0) < min_market_cap and comp.get('market_cap', 0) != 0:
                logger.debug(f"Skipping {ticker}: Market Cap {comp.get('market_cap')} < {min_market_cap}")
                continue

            valid_tickers.append({
                'ticker': ticker,
                'sector': comp.get('sector', 'Unknown'),
                'listing_date': comp.get('listing_date', '1900-01-01'),
                'status': comp.get('status', 'Active'),
                'avg_daily_volume': comp.get('avg_daily_volume', 0),
                'market_cap': comp.get('market_cap', 0)
            })

        if not valid_tickers:
            logger.warning("No valid tickers found after filtering.")
            return

        logger.info(f"Populating DuckDB metadata with {len(valid_tickers)} valid tickers...")

        for t in valid_tickers:
            self.repo.con.execute('''
                INSERT OR REPLACE INTO idx_metadata
                (ticker, sector, listing_date, status, avg_daily_volume, market_cap)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', [t['ticker'], t['sector'], t['listing_date'], t['status'], t['avg_daily_volume'], t['market_cap']])

        logger.info("Initializing jobs in SQLite queue...")
        conn = sqlite3.connect(self.job_queue_path)
        cursor = conn.cursor()

        for t in valid_tickers:
            cursor.execute('''
                INSERT OR IGNORE INTO fetch_jobs (ticker, status)
                VALUES (?, 'PENDING')
            ''', (t['ticker'],))

        conn.commit()
        conn.close()
        logger.success(f"Universe update complete. {len(valid_tickers)} tickers queued for ingestion.")
