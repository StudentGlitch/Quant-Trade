from pydantic import BaseModel
from typing import List

class AlphaFeature(BaseModel):
    feature_id: str
    formula_snippet: str
    oos_sharpe: float
    xgboost_importance: float
    status: str

class EvolutionResponse(BaseModel):
    active_features: List[AlphaFeature]
    rejected_count: int
    decayed_features: List[AlphaFeature]
    overall_ensemble_correlation: float
