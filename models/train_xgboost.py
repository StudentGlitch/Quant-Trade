
import duckdb
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_squared_error, r2_score
import joblib
import logging
from pathlib import Path

# Setup paths
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "storage" / "raw_data" / "quant_engine.db"
MODEL_PATH = BASE_DIR / "storage" / "artifacts" / "xgboost_model.pkl"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("model_training")

def train_model():
    """Load features, split chronologically, and train XGBoost."""
    con = duckdb.connect(str(DB_PATH))
    df = con.execute("SELECT * FROM market_data_features").df()
    con.close()
    
    if df.empty:
        logger.error("No data found in market_data_features.")
        return

    # Drop rows with NaN targets/features
    feature_cols = [col for col in df.columns if col.startswith('feat_')]
    target_col = 'target_fwd_return_5d'
    
    df = df.dropna(subset=feature_cols + [target_col])
    
    # Chronological Split (No random shuffling!)
    df = df.sort_values('timestamp')
    unique_dates = df['timestamp'].unique()
    
    train_size = int(len(unique_dates) * 0.7)
    val_size = int(len(unique_dates) * 0.15)
    
    train_dates = unique_dates[:train_size]
    val_dates = unique_dates[train_size:train_size + val_size]
    test_dates = unique_dates[train_size + val_size:]
    
    train_df = df[df['timestamp'].isin(train_dates)]
    val_df = df[df['timestamp'].isin(val_dates)]
    test_df = df[df['timestamp'].isin(test_dates)]
    
    X_train, y_train = train_df[feature_cols], train_df[target_col]
    X_val, y_val = val_df[feature_cols], val_df[target_col]
    X_test, y_test = test_df[feature_cols], test_df[target_col]
    
    logger.info(f"Training on {len(X_train)} rows, validating on {len(X_val)}, testing on {len(X_test)}...")
    
    # XGBoost Hyperparameters
    params = {
        'objective': 'reg:squarederror',
        'n_estimators': 500,
        'learning_rate': 0.05,
        'max_depth': 6,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'random_state': 42,
        'early_stopping_rounds': 50 # Moved to constructor
    }
    
    model = xgb.XGBRegressor(**params)
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False
    )
    
    # Evaluate
    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    logger.info(f"Test Results - MSE: {mse:.6f}, R2: {r2:.4f}")
    
    # Save Artifacts
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, str(MODEL_PATH))
    logger.info(f"Model saved to {MODEL_PATH}")

if __name__ == "__main__":
    train_model()
