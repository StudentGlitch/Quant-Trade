import numpy as np
import pandas as pd

def calculate_sharpe(returns: pd.Series, risk_free_rate: float = 0.04) -> float:
    """Annualized Sharpe Ratio (PRD 5.2 class BacktestMetrics)."""
    excess_returns = returns - (risk_free_rate / 252)
    if excess_returns.std() == 0:
        return 0.0
    return (excess_returns.mean() / excess_returns.std()) * np.sqrt(252)

def calculate_max_drawdown(equity_curve: pd.Series) -> float:
    """Max Drawdown calculation (PRD 5.2)."""
    rolling_max = equity_curve.cummax()
    drawdown = (equity_curve - rolling_max) / rolling_max
    return drawdown.min()

def calculate_calmar(returns: pd.Series, max_drawdown: float) -> float:
    """Calmar Ratio (PRD 4 /metrics.py)."""
    if max_drawdown == 0:
        return 0.0
    annualized_return = returns.mean() * 252
    return annualized_return / abs(max_drawdown)

def calculate_sortino(returns: pd.Series, risk_free_rate: float = 0.04) -> float:
    """Sortino Ratio (PRD 4 /metrics.py)."""
    excess_returns = returns - (risk_free_rate / 252)
    downside_std = excess_returns[excess_returns < 0].std()
    if downside_std == 0 or pd.isna(downside_std):
        return 0.0
    return (excess_returns.mean() / downside_std) * np.sqrt(252)
