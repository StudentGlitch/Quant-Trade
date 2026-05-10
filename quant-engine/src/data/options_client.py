import yfinance as yf
import pandas as pd
from loguru import logger
from datetime import datetime
from .duckdb_repo import DuckDBRepo
from ..derivatives.pricer import OptionsPricer

class OptionsClient:
    """
    Phase 20.1: Options Data Ingestion.
    Fetches chains, calculates Greeks, and stores in DuckDB.
    """

    def __init__(self, repo: DuckDBRepo):
        self.repo = repo
        self.pricer = OptionsPricer()

    def fetch_and_store_chains(self, ticker: str):
        """Fetch all expirations for a ticker and price every contract."""
        logger.info(f"Ingesting options chains for {ticker}...")
        
        try:
            tk = yf.Ticker(ticker)
            underlying_price = tk.history(period="1d")['Close'].iloc[-1]
            expirations = tk.options
            
            risk_free_rate = 0.05 # Mocked for Phase 20
            
            all_contracts = []
            
            for exp in expirations[:5]: # Cap at 5 expirations for MVP speed
                chain = tk.option_chain(exp)
                
                # Process Calls
                for _, row in chain.calls.iterrows():
                    contract = self._process_contract(
                        row, ticker, exp, underlying_price, risk_free_rate, 'CALL'
                    )
                    if contract: all_contracts.append(contract)
                    
                # Process Puts
                for _, row in chain.puts.iterrows():
                    contract = self._process_contract(
                        row, ticker, exp, underlying_price, risk_free_rate, 'PUT'
                    )
                    if contract: all_contracts.append(contract)
                    
            # Bulk Insert
            if all_contracts:
                self.repo.con.executemany("""
                    INSERT OR REPLACE INTO options_chain_ledger 
                    (contract_symbol, underlying_ticker, expiration_date, strike_price, option_type, 
                     last_price, implied_volatility, delta, gamma, theta, vega, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, all_contracts)
                logger.success(f"Stored {len(all_contracts)} contracts for {ticker}")

        except Exception as e:
            logger.error(f"Failed to ingest options for {ticker}: {e}")

    def _process_contract(self, row, ticker, exp, S, r, otype):
        """Calculates Greeks and IV for a specific contract row."""
        K = row['strike']
        market_price = row['lastPrice']
        
        # Calculate Time to Maturity (Years)
        T = (pd.to_datetime(exp) - pd.Timestamp.now()).days / 365.0
        if T <= 0: return None
        
        # 1. Newton-Raphson for IV
        iv = self.pricer.implied_volatility(market_price, S, K, T, r, otype)
        if iv is None: iv = row.get('impliedVolatility', 0.0) # Fallback to yf IV
        
        # 2. Calculate Greeks using calculated IV
        greeks = self.pricer.calculate_greeks(S, K, T, r, iv, otype)
        
        return (
            row['contractSymbol'],
            ticker,
            exp,
            K,
            otype,
            market_price,
            iv,
            greeks['delta'],
            greeks['gamma'],
            greeks['theta'],
            greeks['vega'],
            datetime.now()
        )
