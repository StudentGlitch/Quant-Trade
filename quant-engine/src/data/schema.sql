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
    status VARCHAR,
    cross_sectional_z_score DOUBLE
);

-- QA Code Profiling Logs
CREATE TABLE IF NOT EXISTS code_profiling_logs (
    execution_id VARCHAR PRIMARY KEY,
    module_name VARCHAR,
    function_name VARCHAR,
    avg_execution_time_ms DOUBLE,
    peak_memory_mb DOUBLE,
    call_count BIGINT,
    last_profiled TIMESTAMP
);

CREATE TABLE IF NOT EXISTS identified_anomalies (
    anomaly_id VARCHAR PRIMARY KEY,
    file_path VARCHAR,
    line_number INT,
    anomaly_type VARCHAR,
    severity VARCHAR,
    description TEXT,
    git_branch_name VARCHAR,
    commit_hash VARCHAR,
    pr_url VARCHAR,
    status VARCHAR
);

-- Multi-Modal Perception Ledgers (Phase 16)
CREATE TABLE IF NOT EXISTS audio_perception_ledger (
    media_id VARCHAR PRIMARY KEY,
    ticker VARCHAR,
    date DATE,
    event_type VARCHAR,
    transcript TEXT,
    hesitation_index DOUBLE,
    audio_sentiment_score DOUBLE,
    analyzed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vision_perception_ledger (
    image_id VARCHAR PRIMARY KEY,
    ticker VARCHAR,
    date DATE,
    source_document VARCHAR,
    extracted_text TEXT,
    visual_insight_summary TEXT,
    bullish_confidence DOUBLE
);

-- DRL Execution Microstructure Ledgers (Phase 17)
CREATE TABLE IF NOT EXISTS parent_orders (
    parent_id VARCHAR PRIMARY KEY,
    ticker VARCHAR,
    order_type VARCHAR,
    total_quantity BIGINT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    target_vwap DOUBLE,
    actual_average_price DOUBLE,
    drl_slippage_savings DOUBLE
);

CREATE TABLE IF NOT EXISTS child_orders (
    child_id VARCHAR PRIMARY KEY,
    parent_id VARCHAR,
    execution_time TIMESTAMP,
    executed_quantity BIGINT,
    executed_price DOUBLE,
    market_impact_incurred DOUBLE
);

-- Global Multi-Asset & FX Hedging Ledgers (Phase 18)
CREATE TABLE IF NOT EXISTS global_market_metadata (
    ticker VARCHAR PRIMARY KEY,
    asset_class VARCHAR,
    exchange_code VARCHAR,
    currency VARCHAR,
    timezone VARCHAR
);

CREATE TABLE IF NOT EXISTS fx_hedging_ledger (
    date DATE,
    portfolio_id VARCHAR,
    base_currency VARCHAR,
    target_currency VARCHAR,
    gross_exposure DOUBLE,
    hedge_ratio DOUBLE,
    realized_fx_pnl DOUBLE,
    PRIMARY KEY (date, portfolio_id, target_currency)
);

-- Derivatives & Volatility Ledgers (Phase 20)
CREATE TABLE IF NOT EXISTS options_chain_ledger (
    contract_symbol VARCHAR PRIMARY KEY,
    underlying_ticker VARCHAR,
    expiration_date DATE,
    strike_price DOUBLE,
    option_type VARCHAR,
    last_price DOUBLE,
    implied_volatility DOUBLE,
    delta DOUBLE,
    gamma DOUBLE,
    theta DOUBLE,
    vega DOUBLE,
    last_updated TIMESTAMP
);

CREATE TABLE IF NOT EXISTS portfolio_greeks (
    date DATE PRIMARY KEY,
    portfolio_id VARCHAR,
    net_delta DOUBLE,
    net_gamma DOUBLE,
    net_theta DOUBLE,
    net_vega DOUBLE
);

CREATE TABLE IF NOT EXISTS portfolio_targets_multi (
    date DATE,
    ticker VARCHAR,
    target_weight_pct DOUBLE,
    llm_conviction DOUBLE,
    strategy_name VARCHAR,
    PRIMARY KEY (date, ticker, strategy_name)
);

-- Federated Learning Ledgers (Phase 19)
CREATE TABLE IF NOT EXISTS federated_nodes_ledger (
    node_id VARCHAR PRIMARY KEY,
    client_user_id VARCHAR,
    ip_address VARCHAR,
    status VARCHAR,
    total_training_rounds BIGINT DEFAULT 0,
    alpha_contribution_score DOUBLE,
    last_ping TIMESTAMP
);

CREATE TABLE IF NOT EXISTS training_rounds_ledger (
    round_id BIGINT PRIMARY KEY,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    nodes_participated INT,
    global_model_loss_before DOUBLE,
    global_model_loss_after DOUBLE
);

-- Time Machine Sandbox Simulations (Phase 29)
CREATE TABLE IF NOT EXISTS sandbox_simulations (
    job_id VARCHAR PRIMARY KEY,
    user_id VARCHAR,
    strategy_name VARCHAR,
    graph_payload JSON,
    status VARCHAR DEFAULT 'QUEUED',
    cagr DOUBLE,
    max_drawdown DOUBLE,
    sharpe_ratio DOUBLE,
    equity_curve_json JSON,
    completed_at TIMESTAMP
);

-- MLOps & Drift Monitoring Ledgers (Phase 24)
CREATE TABLE IF NOT EXISTS feature_drift_ledger (
    date DATE,
    feature_name VARCHAR,
    reference_mean DOUBLE,
    current_mean DOUBLE,
    psi_score DOUBLE,
    drift_detected BOOLEAN,
    PRIMARY KEY (date, feature_name)
);

-- Econometric Forecasting Ledgers (Phase 25)
CREATE TABLE IF NOT EXISTS econometric_forecasts (
    date DATE,
    macro_indicator VARCHAR,
    forecast_horizon INT,
    predicted_value DOUBLE,
    lower_confidence_bound DOUBLE,
    upper_confidence_bound DOUBLE,
    PRIMARY KEY (date, macro_indicator, forecast_horizon)
);

-- Autonomous War Room Ledgers (Phase 26)
CREATE TABLE IF NOT EXISTS war_room_transcripts (
    debate_id VARCHAR PRIMARY KEY,
    ticker VARCHAR,
    date DATE,
    transcript JSON,
    final_decision VARCHAR,
    blended_conviction DOUBLE,
    cio_summary TEXT
);

CREATE TABLE IF NOT EXISTS persona_track_records (
    persona_name VARCHAR PRIMARY KEY,
    total_votes BIGINT DEFAULT 0,
    correct_calls BIGINT DEFAULT 0,
    historical_accuracy DOUBLE DEFAULT 0.5
);

-- Apex Sentience Ledgers (Phase 30)
CREATE TABLE IF NOT EXISTS autonomous_pr_ledger (
    pr_id VARCHAR PRIMARY KEY,
    feature_name VARCHAR,
    generated_code TEXT,
    simulated_sharpe DOUBLE,
    base_model_sharpe DOUBLE,
    improvement_pct DOUBLE,
    git_branch_name VARCHAR,
    status VARCHAR DEFAULT 'PENDING_REVIEW'
);

CREATE TABLE IF NOT EXISTS lp_commitments (
    commitment_id VARCHAR PRIMARY KEY,
    user_id VARCHAR,
    committed_capital_usd DOUBLE,
    kyc_status VARCHAR DEFAULT 'PENDING',
    signed_date TIMESTAMP
);

-- Proprietary LLM Fine-Tuning Ledgers (Phase 27)
CREATE TABLE IF NOT EXISTS llm_finetuning_runs (
    run_id VARCHAR PRIMARY KEY,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    base_model VARCHAR,
    adapter_name VARCHAR,
    dataset_size INT,
    final_loss DOUBLE,
    status VARCHAR
);

CREATE TABLE IF NOT EXISTS dpo_preference_dataset (
    pair_id VARCHAR PRIMARY KEY,
    ticker VARCHAR,
    prompt TEXT,
    chosen_response TEXT,
    rejected_response TEXT,
    margin_of_victory DOUBLE
);

-- Adversarial "Red Team" Swarm Ledgers (Phase 31)
CREATE TABLE IF NOT EXISTS synthetic_market_universes (
    universe_id VARCHAR PRIMARY KEY,
    scenario_description TEXT,
    generation_date TIMESTAMP,
    gan_loss DOUBLE,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS adversarial_wargame_ledger (
    battle_id VARCHAR PRIMARY KEY,
    universe_id VARCHAR,
    main_swarm_version VARCHAR,
    red_team_version VARCHAR,
    simulated_sharpe DOUBLE,
    max_drawdown DOUBLE,
    survival_status VARCHAR,
    evolved_countermeasure TEXT
);

-- Quantum-Inspired Portfolio Optimization Ledgers (Phase 32)
CREATE TABLE IF NOT EXISTS quantum_optimization_ledger (
    optimization_id VARCHAR PRIMARY KEY,
    date TIMESTAMP,
    assets_evaluated INT,
    synthetic_universes_sampled INT,
    qubo_variables INT,
    annealing_time_ms DOUBLE,
    global_minimum_energy DOUBLE,
    classical_solver_time_ms DOUBLE
);


