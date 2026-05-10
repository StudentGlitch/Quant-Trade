
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger
import sys
from pathlib import Path

# Add src to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.features.technical import TechnicalFeatures
from src.features.statistical import StatisticalFeatures
from src.features.alternative import AlternativeFeatures
from src.features.labelling import Labelling
from src.data.data_standardizer import DataStandardizer

def test_pipeline():
    logger.info("Starting local feature engineering validation...")
    
    # 1. Create mock data for 2 tickers, 50 days
    dates = [datetime.now().date() - timedelta(days=i) for i in range(50)]
    tickers = ["AAPL", "MSFT"]
    
    data = []
    for ticker in tickers:
        for date in dates:
            data.append({
                "ticker": ticker,
                "date": date,
                "open": 100 + np.random.randn(),
                "high": 110 + np.random.randn(),
                "low": 90 + np.random.randn(),
                "close": 105 + np.random.randn(),
                "adj_close": 105 + np.random.randn(),
                "volume": 1000000 + np.random.randint(0, 100000),
                "google_trends_score": np.random.randint(10, 100),
                "wiki_views": np.random.randint(1000, 5000)
            })
    
    df = pd.DataFrame(data)
    
    # 2. Run standardizer
    logger.info("Testing DataStandardizer...")
    df = DataStandardizer.calculate_fundamental_ratios(df, "AAPL") # Logic is ticker-agnostic for price
    
    # 3. Run technicals
    logger.info("Testing TechnicalFeatures...")
    df = TechnicalFeatures.add_all(df)
    
    # 4. Run statistical
    logger.info("Testing StatisticalFeatures (Returns/Vol)...")
    df = StatisticalFeatures.add_returns_and_vol(df)
    
    # 5. Run Alternative
    logger.info("Testing AlternativeFeatures...")
    df = AlternativeFeatures.add_attention_spikes(df)
    
    # 6. Run Z-Score (The likely culprit)
    logger.info("Testing StatisticalFeatures (Z-Score)...")
    df = StatisticalFeatures.add_cross_sectional_zscore(df, 'ret_1d', 'z_score_ret_1m')
    
    # 7. Run Labelling
    logger.info("Testing Labelling...")
    df = Labelling.add_target(df)
    
    logger.success("Feature Engineering Pipeline Validation PASSED.")
    print(df.tail())

if __name__ == "__main__":
    test_pipeline()
