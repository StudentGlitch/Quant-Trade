-- Analytical Metadata (PRD v1.2)
CREATE TABLE IF NOT EXISTS idx_metadata (
    ticker VARCHAR PRIMARY KEY,
    company_name VARCHAR,
    sector VARCHAR,
    index_membership VARCHAR[],
    status VARCHAR DEFAULT 'ACTIVE',
    avg_daily_volume BIGINT,
    last_updated TIMESTAMP
);

-- Drop legacy monolithic price data
DROP TABLE IF EXISTS ohlcv_daily;

-- Macro Economic Indicators
CREATE TABLE IF NOT EXISTS macro_data (
    date DATE PRIMARY KEY,
    us_10y_yield DOUBLE,
    us_2y_yield DOUBLE,
    us_cpi DOUBLE,
    us_m2 DOUBLE,
    vix_close DOUBLE
);

-- Alternative Data
CREATE TABLE IF NOT EXISTS alt_google_trends (
    date DATE,
    ticker VARCHAR,
    google_trends_score DOUBLE,
    PRIMARY KEY (ticker, date)
);

CREATE TABLE IF NOT EXISTS alt_wiki_views (
    date DATE,
    ticker VARCHAR,
    wiki_views BIGINT,
    PRIMARY KEY (ticker, date)
);

-- Intelligent Scrape Store (ScrapeGraphAI)
CREATE TABLE IF NOT EXISTS alt_scraped_sentiment (
    date DATE,
    ticker VARCHAR,
    sentiment_score DOUBLE,
    source_url VARCHAR,
    PRIMARY KEY (ticker, date)
);

-- Feature Store
CREATE TABLE IF NOT EXISTS feature_store (
    ticker VARCHAR,
    date DATE,
    ret_1d DOUBLE,
    volatility_20d DOUBLE,
    rsi_14 DOUBLE,
    macd_hist DOUBLE,
    atr_14_pct DOUBLE,
    z_score_ret_1m DOUBLE,
    feat_wiki_spike_20d DOUBLE,
    feat_google_momentum_20d DOUBLE,
    feat_google_roc_5d DOUBLE,
    target_fwd_ret_5d DOUBLE,
    target_fwd_ret_5d_bin INT,
    PRIMARY KEY (ticker, date)
);

-- Backtest Execution Ledger (Updated for Janus + Vibe-Trading)
CREATE TABLE IF NOT EXISTS paper_trades (
    trade_id UUID PRIMARY KEY,
    ticker VARCHAR,
    signal_date DATE,
    execution_date DATE,
    ml_signal DOUBLE,
    llm_signal DOUBLE,
    ml_weight DOUBLE,
    llm_weight DOUBLE,
    final_blended_signal DOUBLE,
    final_direction INT,
    vibe VARCHAR,
    chain_of_thought TEXT,
    execution_price DOUBLE,
    position_size DOUBLE,
    transaction_cost DOUBLE,
    status VARCHAR
);
