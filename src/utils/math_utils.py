import pandas as pd

def check_stationarity(series: pd.Series) -> bool:
    """Placeholder for ADF test logic if needed for PRD 5."""
    from statsmodels.tsa.stattools import adfuller
    try:
        res = adfuller(series.dropna())
        return res[1] < 0.05
    except:
        return False

def cap_outliers(series: pd.Series, threshold: float = 3.0) -> pd.Series:
    """Cap extreme returns as per PRD 8 Outliers."""
    return series.clip(lower=-threshold, upper=threshold)

def remove_zero_variance(df: pd.DataFrame, threshold: float = 1e-6) -> pd.DataFrame:
    """Filter out near-zero variance features (PRD 8 Collinearity)."""
    variances = df.var()
    low_variance_cols = variances[variances < threshold].index
    if len(low_variance_cols) > 0:
        from loguru import logger
        logger.info(f"Dropping near-zero variance features: {list(low_variance_cols)}")
    return df.drop(columns=low_variance_cols)
