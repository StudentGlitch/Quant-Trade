
import duckdb
import pandas as pd
from pathlib import Path
import time
import os
import sys
from datetime import datetime

# Setup paths
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "storage" / "db" / "quant_data.duckdb"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_stats():
    """Fetch latest statistics from DuckDB."""
    try:
        con = duckdb.connect(str(DB_PATH), read_only=True)
        
        # 1. Data Ingestion Status
        ohlcv_count = con.execute("SELECT count(*) FROM ohlcv_daily").fetchone()[0]
        tickers = con.execute("SELECT count(DISTINCT ticker) FROM ohlcv_daily").fetchone()[0]
        
        # 2. Feature Store Status
        feature_count = con.execute("SELECT count(*) FROM feature_store").fetchone()[0]
        
        # 3. Latest Paper Trades (Janus Signals)
        trades_df = con.execute("""
            SELECT ticker, signal_date, ml_weight, llm_weight, final_blended_signal, final_direction 
            FROM paper_trades 
            ORDER BY signal_date DESC 
            LIMIT 5
        """).df()
        
        con.close()
        return {
            "ohlcv_count": ohlcv_count,
            "tickers": tickers,
            "feature_count": feature_count,
            "latest_trades": trades_df
        }
    except Exception as e:
        return {"error": str(e)}

def run_dashboard():
    """Main dashboard loop."""
    while True:
        stats = get_stats()
        clear_screen()
        
        print("="*60)
        print(f" ⚕ NOUS HERMES - DARWINIAN QUANT SWARM MONITOR ⚕")
        print(f" Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        if "error" in stats:
            print(f" [!] Error connecting to DuckDB: {stats['error']}")
            print("     (The engine might be currently writing to the database)")
        else:
            print(f" [DATA] Tickers Tracked: {stats['tickers']}")
            print(f" [DATA] OHLCV Rows:      {stats['ohlcv_count']:,}")
            print(f" [DATA] Feature Rows:    {stats['feature_count']:,}")
            print("-"*60)
            
            print(" [LATEST SIGNALS - JANUS BLENDER]")
            if stats['latest_trades'].empty:
                print(" No trades recorded yet. Engine is likely in Phase 1-3.")
            else:
                print(f" {'TICKER':<10} | {'DATE':<12} | {'ML WT':<6} | {'LLM WT':<6} | {'SIGNAL':<6} | {'DIR'}")
                print("-" * 60)
                for _, row in stats['latest_trades'].iterrows():
                    dir_str = "LONG" if row['final_direction'] == 1 else ("SHORT" if row['final_direction'] == -1 else "HOLD")
                    print(f" {row['ticker']:<10} | {str(row['signal_date']):<12} | {row['ml_weight']:<6.2f} | {row['llm_weight']:<6.2f} | {row['final_blended_signal']:<6.2f} | {dir_str}")
        
        print("\n" + "="*60)
        print(" [CTRL+C to Exit] | Refreshing every 10 seconds...")
        
        try:
            time.sleep(10)
        except KeyboardInterrupt:
            print("\nExiting Dashboard.")
            sys.exit(0)

if __name__ == "__main__":
    run_dashboard()
