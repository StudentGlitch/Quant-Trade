import collections
import collections.abc
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any

# Python 3.12 Compatibility Patch for attrdict/pageviewapi
if not hasattr(collections, 'Mapping'):
    collections.Mapping = collections.abc.Mapping
if not hasattr(collections, 'MutableMapping'):
    collections.MutableMapping = collections.abc.MutableMapping
if not hasattr(collections, 'Sequence'):
    collections.Sequence = collections.abc.Sequence

# Add project root to path (PRD 4 modularity)
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import yaml
import numpy as np
from loguru import logger
import pandas as pd
from datetime import datetime

from src.data.duckdb_repo import DuckDBRepo
from src.data.yf_client import YFinanceClient
from src.data.macro_client import MacroClient
from src.data.alt_client import AltDataClient
from src.data.scrape_client import ScrapeGraphClient
from src.data.data_standardizer import DataStandardizer
from src.features.technical import TechnicalFeatures
from src.features.statistical import StatisticalFeatures
from src.features.alternative import AlternativeFeatures
from src.features.labelling import Labelling
from src.models.xgb_trainer import XGBTrainer
from src.execution.vectorbt_engine import VectorBTEngine
from src.models.janus_blender import JanusBlender
from src.execution.llm_agent import LLMAgentCohort
from src.utils.contracts import TradeSignal
from pydantic import ValidationError

class QuantOrchestrator:
    def __init__(self, repo: DuckDBRepo, config_path: str = None):
        if config_path is None:
            config_path = str(BASE_DIR / "config" / "settings.yaml")

        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.repo = repo
        self.yf_client = YFinanceClient(self.repo)
        self.macro_client = MacroClient(self.repo)
        self.alt_client = AltDataClient(self.repo)
        self.scrape_client = ScrapeGraphClient()
        self.janus = JanusBlender()
        self.llm_agent = LLMAgentCohort()

    def run_ingestion(self):
        """Phase 1: Robust & Diverse Data Ingestion (PRD 7)."""
        logger.info("Starting Phase 1: Data Ingestion")
        tickers = self.config['universe']['tickers']
        start_date = self.config['data']['start_date']

        # 1. Core data fetch (Critical)
        self.yf_client.fetch_and_store(tickers, start_date)
        self.macro_client.fetch_and_store(start_date)

        # 2. Alternative data fetch (Non-Critical, PRD Bug Fix)
        try:
            self.alt_client.fetch_and_store(tickers, start_date)
        except Exception as e:
            logger.error(f"Graceful degradation: Alt Data ingestion failed: {e}")

        # 3. Intelligent Scraping (ScrapeGraphAI)
        self.run_intelligent_scraping(tickers)

    def run_intelligent_scraping(self, tickers: List[str]):
        """Gather data from any website using ScrapeGraphAI."""
        logger.info("Starting Intelligent Scraping Phase...")
        for ticker in tickers:
            try:
                sentiment_data = self.scrape_client.get_ticker_sentiment(ticker)
                if sentiment_data:
                    # Simplify sentiment to a single average score for the ledger
                    # In a real system, we would store individual headlines.
                    score = 0.0
                    # Expecting structured JSON from our prompt in scrape_client
                    # result is whatever smart_scraper.run() returns.
                    # Our prompt asked for top 5 news + sentiment.
                    # Assume the result might be a list or dict.

                    # For V1, we'll just log it and store a placeholder until
                    # we confirm the ScrapeGraphAI return format.
                    self.repo.con.execute("""
                        INSERT OR REPLACE INTO alt_scraped_sentiment (date, ticker, sentiment_score, source_url)
                        VALUES (CURRENT_DATE, ?, ?, ?)
                    """, [ticker, 0.5, f"https://finance.yahoo.com/quote/{ticker}/news"])
                    logger.info(f"Scraped sentiment for {ticker}")
            except Exception as e:
                logger.error(f"Failed to scrape news for {ticker}: {e}")

    def run_feature_engineering(self):
        """Phase 2: Feature Engineering & Target Labelling (PRD 7)."""
        logger.info("Starting Phase 2: Feature Engineering")

        # PRD Phase 0.5: Query active tickers from new analytical metadata
        try:
            all_tickers = self.repo.con.execute("SELECT DISTINCT ticker FROM idx_metadata WHERE status = 'ACTIVE'").df()['ticker'].tolist()
        except Exception:
            logger.warning("idx_metadata table not found. Using fallback universe.")
            all_tickers = self.config['universe']['tickers']

        # Load all data into memory upfront to avoid N+1 queries
        logger.info("Loading all OHLCV data into memory from Parquet Hive...")
        # PRD Phase 0.5: Read from Parquet directory
        all_df = self.repo.get_parquet_data(BASE_DIR)
        
        if all_df.empty:
            logger.error("No Parquet data found. Run the Async Queue Consumer first.")
            return
            
        logger.info("Loading all Alternative data into memory...")
        all_alt_df = self.alt_client.get_all_merged_alt_data()
        logger.info("Loading all Scraped Sentiment data into memory...")
        try:
            all_scraped_df = self.repo.con.execute("SELECT date, ticker, sentiment_score FROM alt_scraped_sentiment").df()
        except Exception:
            all_scraped_df = pd.DataFrame(columns=['date', 'ticker', 'sentiment_score'])

        processed_data = []

        # Group by ticker to filter in-memory
        grouped_df = all_df.groupby('ticker')
        grouped_alt_df = all_alt_df.groupby('ticker') if not all_alt_df.empty else None
        grouped_scraped_df = all_scraped_df.groupby('ticker') if not all_scraped_df.empty else None

        for ticker in all_tickers:
            # 1. Fetch raw data from in-memory groups
            if ticker not in grouped_df.groups:
                continue
            df = grouped_df.get_group(ticker).copy()

            if grouped_alt_df is not None and ticker in grouped_alt_df.groups:
                alt_df = grouped_alt_df.get_group(ticker).copy()
            else:
                alt_df = pd.DataFrame(columns=['date', 'google_trends_score', 'wiki_views'])

            # 2. Fetch Scraped Data from in-memory groups
            if grouped_scraped_df is not None and ticker in grouped_scraped_df.groups:
                scraped_df = grouped_scraped_df.get_group(ticker).copy()
            else:
                scraped_df = pd.DataFrame(columns=['date', 'sentiment_score'])

            # 3. Standardize & Calculate Fundamental Ratios (OpenBB style)
            df = DataStandardizer.calculate_fundamental_ratios(df, ticker)

            # 4. Merge Alternative Data
            df['date'] = pd.to_datetime(df['date']).dt.date
            if not alt_df.empty:
                alt_df['date'] = pd.to_datetime(alt_df['date']).dt.date
                df = df.merge(alt_df[['date', 'google_trends_score', 'wiki_views']], on='date', how='left')
            else:
                df['google_trends_score'] = np.nan
                df['wiki_views'] = np.nan

            # 5. Merge Scraped Sentiment
            if not scraped_df.empty:
                scraped_df['date'] = pd.to_datetime(scraped_df['date']).dt.date
                # drop ticker column to prevent collision on merge
                if 'ticker' in scraped_df.columns:
                    scraped_df = scraped_df.drop(columns=['ticker'])
                df = df.merge(scraped_df, on='date', how='left')
                df['sentiment_score'] = df['sentiment_score'].ffill().fillna(0.0)
            else:
                df['sentiment_score'] = 0.0

            # 6. Technical Features
            df = TechnicalFeatures.add_all(df)

            # 5. Statistical Features
            df = StatisticalFeatures.add_returns_and_vol(df)

            # 6. Alternative Features (Attention Spikes)
            df = AlternativeFeatures.add_attention_spikes(df)

            # 7. Target Labelling
            df = Labelling.add_target(df)

            processed_data.append(df)

        if not processed_data:
            logger.error("No data successfully processed for any ticker. Skipping feature engineering.")
            return

        final_df = pd.concat(processed_data)

        # Cross-Sectional Z-Scores
        final_df = StatisticalFeatures.add_cross_sectional_zscore(final_df, 'ret_1d', 'z_score_ret_1m')

        # Drop NaNs and Near-Zero Variance (PRD 8)
        # Added ratio columns to the dropna requirement
        final_df = final_df.dropna(subset=['rsi_14', 'macd_hist', 'target_fwd_ret_5d', 'feat_wiki_spike_20d', 'ratio_p_ma200'])

        # Store in Feature Store
        self.repo.con.execute("DROP TABLE IF EXISTS feature_store")
        self.repo.con.execute("CREATE TABLE feature_store AS SELECT * FROM final_df")
        logger.info(f"Feature Store updated with {len(final_df)} records.")

    def run_training(self) -> Tuple[str, List[str]]:
        """Phase 3: Model Training (XGBoost)."""
        logger.info("Starting Phase 3: Model Training")

        df = self.repo.con.execute("SELECT * FROM feature_store").df()

        feature_cols = [
            'rsi_14', 'macd_hist', 'atr_14_pct', 'volatility_20d',
            'z_score_ret_1m', 'feat_wiki_spike_20d', 'feat_google_momentum_20d',
            'feat_google_roc_5d', 'ratio_p_ma200', 'ratio_vol_ma20', 'sentiment_score'
        ]
        target_col = 'target_fwd_ret_5d'

        # Chronological Split as per PRD 7.3.1 (using pandas datetime comparison)
        val_start = pd.to_datetime(self.config['training']['val_start'])
        val_end = pd.to_datetime(self.config['training']['val_end'])

        df['date'] = pd.to_datetime(df['date'])

        train_df = df[df['date'] < val_start]
        val_df = df[(df['date'] >= val_start) & (df['date'] <= val_end)]

        trainer = XGBTrainer(feature_cols, target_col)
        trainer.optimize(train_df, val_df, n_trials=20)
        trainer.train_final(df)

        model_path = f"storage/artifacts/models/xgb_model_{datetime.now().strftime('%Y%m%d_%H%M')}.pkl"
        trainer.save(model_path)
        return model_path, feature_cols

    def run_backtest(self, model_path: str, feature_cols: list):
        """Phase 4: Vectorized Backtesting."""
        logger.info("Starting Phase 4: Vectorized Backtesting")

        df = self.repo.con.execute("SELECT * FROM feature_store ORDER BY date, ticker").df()

        import joblib
        model = joblib.load(model_path)

        df['pred'] = model.predict(df[feature_cols])
        df['signal'] = np.where(df['pred'] > 0.005, 1, np.where(df['pred'] < -0.005, -1, 0))

        close_prices = df.pivot(index='date', columns='ticker', values='adj_close')
        signals = df.pivot(index='date', columns='ticker', values='signal').shift(1).fillna(0)

        engine = VectorBTEngine(
            init_cash=self.config['backtest']['init_cash'],
            fees=self.config['backtest']['fees'],
            slippage=self.config['backtest']['slippage']
        )

        portfolio = engine.run(close_prices, signals)
        engine.report(portfolio)

    def _get_recent_reflections(self, ticker: str, limit: int = 5) -> str:
        """
        Extract 'reflections' from the historical paper_trades ledger (PRD 7 Phase 5.3).
        Analyzes past signals that resulted in loss/wrong direction.
        """
        try:
            # Note: In a real system, we'd join with actual returns.
            # For this MVP, we look for past trades that were CLOSED or have notes.
            # Since this is a fresh DB, we fallback to a structured message.
            query = f"SELECT signal_date, final_blended_signal, final_direction FROM paper_trades WHERE ticker = '{ticker}' ORDER BY signal_date DESC LIMIT {limit}"
            past_trades = self.repo.con.execute(query).df()

            if past_trades.empty:
                return ""

            reflections = "HISTORICAL PERFORMANCE SUMMARY:\n"
            for _, row in past_trades.iterrows():
                reflections += f"- Date: {row['signal_date']}, Signal: {row['final_blended_signal']:.2f}, Direction: {row['final_direction']}\n"

            return reflections
        except Exception:
            return ""

    def run_paper_trade(self, model_path: str, feature_cols: list[str]) -> None:
        """Phase 5: Autonomous Paper Trading (The ATLAS Janus Loop with Vibe-Trading reasoning)."""
        logger.info("Starting Phase 5: Paper Trading with Janus Blender & Vibe Reasoning")
        import joblib
        import uuid
        model = joblib.load(model_path)

        # Get latest data and macro
        df = self.repo.con.execute("SELECT * FROM feature_store ORDER BY date DESC, ticker").df()
        macro_df = self.macro_client.get_macro()

        if df.empty or macro_df.empty:
            logger.warning("No data for paper trading.")
            return

        latest_date = df['date'].iloc[0]
        latest_df = df[df['date'] == latest_date]
        latest_macro = macro_df.iloc[-1].to_dict()

        logger.info(f"Generating live signals for {latest_date}")

        # 1. Update Janus Weights based on 30-day performance (Darwinian Allocation)
        self.janus.update_weights(latest_date)

        # 2. ML Baseline Inference
        latest_df['ml_pred'] = model.predict(latest_df[feature_cols])

        for _, row in latest_df.iterrows():
            ticker = str(row['ticker'])
            ml_pred = row['ml_pred']
            # Statistical signal [-1.0, 1.0]
            ml_signal = float(np.clip(ml_pred * 10, -1.0, 1.0))

            # Alt context
            alt_context = {
                "google_trends": row.get('google_trends_score'),
                "wiki_spike": row.get('feat_wiki_spike_20d'),
                "google_momentum": row.get('feat_google_momentum_20d')
            }

            # 3. Macro Synthesis & Reflection Ingestion
            reflections = self._get_recent_reflections(ticker)

            # Vibe-Enhanced Swarm Signal
            llm_res = self.llm_agent.get_signal_data(ticker, str(latest_date), latest_macro, alt_context, ml_signal, reflections)
            llm_signal = llm_res["final_signal"]
            vibe = llm_res["vibe"]
            cot = llm_res["chain_of_thought"]

            # 4. Final Signal Synthesis (Darwinian Weighted)
            signals = {"ML_XGBoost": ml_signal, "LLM_Macro": llm_signal}
            final_signal = self.janus.blend_signals(signals)

            # 5. Ledger Execution
            w_ml = self.janus.cohort_weights["ML_XGBoost"]
            w_llm = self.janus.cohort_weights["LLM_Macro"]

            # Convert final signal to discrete direction (PRD 7.5.5)
            # Threshold: > 0.2 for Long, < -0.2 for Short
            direction = 1 if final_signal > 0.2 else (-1 if final_signal < -0.2 else 0)

            try:
                # PRD 5.2 Python Data Contracts validation
                trade_sig = TradeSignal(
                    ticker=ticker,
                    signal_date=latest_date,
                    ml_cohort_signal=ml_signal,
                    llm_cohort_signal=llm_signal,
                    ml_weight=w_ml,
                    llm_weight=w_llm,
                    final_blended_signal=final_signal,
                    direction=direction
                )
            except ValidationError as ve:
                logger.error(f"TradeSignal validation failed for {ticker}: {ve}")
                continue

            self.repo.con.execute("""
                INSERT INTO paper_trades
                (trade_id, ticker, signal_date, ml_signal, llm_signal, ml_weight, llm_weight,
                 final_blended_signal, final_direction, vibe, chain_of_thought, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')
            """, [uuid.uuid4(), trade_sig.ticker, trade_sig.signal_date, 
                  trade_sig.ml_cohort_signal, trade_sig.llm_cohort_signal, 
                  trade_sig.ml_weight, trade_sig.llm_weight,
                  trade_sig.final_blended_signal, trade_sig.direction, vibe, cot])

            logger.info(f"[{ticker}] CIO Final Signal: {final_signal:.2f} | Vibe: {vibe} -> {direction}")

        logger.info("Autonomous Paper Trading iteration complete.")

if __name__ == "__main__":
    db_path = str(BASE_DIR / "storage" / "db" / "quant_data.duckdb")

    # Strict Context Manager usage (PRD Bug Fix)
    with DuckDBRepo(db_path) as repo:
        orch = QuantOrchestrator(repo=repo)
        try:
            orch.run_ingestion()
            orch.run_feature_engineering()
            model_path, feature_cols = orch.run_training()
            orch.run_backtest(model_path, feature_cols)
            orch.run_paper_trade(model_path, feature_cols)
        except Exception as e:
            logger.error(f"Quant Pipeline failed: {e}")
            sys.exit(1)
