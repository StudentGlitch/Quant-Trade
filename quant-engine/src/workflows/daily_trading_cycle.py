from celery import chain, chord
from loguru import logger
from ..workers.background_tasks import (
    scrape_ticker, 
    engineer_cross_sectional_features, 
    run_war_room_debate, 
    calculate_portfolio_weights, 
    dispatch_to_oms
)

def trigger_daily_trading_cycle(universe: list):
    """
    Phase 28.1: The Daily Trading DAG.
    Orchestrates the sequence: Scrape -> Features -> Debate -> Weights -> OMS.
    """
    logger.info(f"Triggering Daily Trading Cycle for {len(universe)} tickers.")
    
    workflow = chain(
        # 1. FAN-OUT: Scrape all tickers concurrently
        chord(
            [scrape_ticker.s(ticker) for ticker in universe], 
            # 2. REDUCE: Once all scraping is done, engineer features
            engineer_cross_sectional_features.s()
        ),
        # 3. LINEAR: Run the War Room Debate on the updated features
        run_war_room_debate.s(),
        # 4. LINEAR: Calculate optimal portfolio weights
        calculate_portfolio_weights.s(),
        # 5. LINEAR: Dispatch to the Phase 10 OMS
        dispatch_to_oms.s()
    )
    
    return workflow.apply_async()
