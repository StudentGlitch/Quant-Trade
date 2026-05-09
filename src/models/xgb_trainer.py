import xgboost as xgb
import optuna
import pandas as pd
import numpy as np
from loguru import logger
from typing import Dict, Any, List
import joblib
from datetime import datetime
from pathlib import Path

class XGBTrainer:
    def __init__(self, feature_cols: List[str], target_col: str):
        self.feature_cols = feature_cols
        self.target_col = target_col
        self.best_params = None
        self.model = None

    def optimize(self, train_df: pd.DataFrame, val_df: pd.DataFrame, n_trials: int = 50):
        """Optuna hyperparameter optimization (PRD 7 Phase 3.2)."""
        logger.info(f"Starting hyperparameter optimization with {n_trials} trials...")

        def objective(trial):
            # PRD 7.3.2 Search Space
            params = {
                'max_depth': trial.suggest_int('max_depth', 3, 9),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.1),
                'subsample': trial.suggest_float('subsample', 0.6, 0.9),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 0.9),
                'n_estimators': 1000,
                'objective': 'reg:squarederror',
                'early_stopping_rounds': 50,
                'random_state': 42,
                'tree_method': 'hist'
            }

            model = xgb.XGBRegressor(**params)
            model.fit(
                train_df[self.feature_cols], train_df[self.target_col],
                eval_set=[(val_df[self.feature_cols], val_df[self.target_col])],
                verbose=False
            )

            # Strategy: Calculate Sharpe on Validation Set (PRD 7.3.2)
            # Use model predictions as simple signals
            preds = model.predict(val_df[self.feature_cols])
            # Signal: Long if prediction > 0.002, Short if < -0.002
            signals = np.where(preds > 0.002, 1, np.where(preds < -0.002, -1, 0))
            
            # Simplified return calculation for Sharpe
            # We assume we enter at val_df['open_next_1'] (implicitly handled by target definition)
            # Strategy returns = signals * target_returns
            strat_returns = signals * val_df[self.target_col]
            
            if strat_returns.std() == 0:
                return -1.0
            
            sharpe = (strat_returns.mean() / strat_returns.std()) * np.sqrt(252 / 5) # Annualized for 5-day horizon
            return sharpe

        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=n_trials)

        self.best_params = study.best_params
        logger.info(f"Optimization complete. Best Sharpe: {study.best_value:.4f}")
        logger.info(f"Best Params: {self.best_params}")

    def train_final(self, df: pd.DataFrame):
        """Train the final model on all provided data using best params (PRD 7 Phase 3.3)."""
        if not self.best_params:
            logger.error("Must run optimize() before train_final().")
            return

        logger.info("Training final model...")
        params = {**self.best_params, 'n_estimators': 1000, 'tree_method': 'hist'}
        self.model = xgb.XGBRegressor(**params)
        self.model.fit(df[self.feature_cols], df[self.target_col])
        logger.info("Final model training complete.")

    def save(self, path: str) -> None:
        """Serialize model (PRD 7 Phase 3.3)."""
        save_path = Path(path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, save_path)
        logger.info(f"Model saved to {save_path}")
