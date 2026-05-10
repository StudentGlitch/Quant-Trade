from pydantic import BaseModel
from typing import List, Optional

class AutonomousScraper(BaseModel):
    dataset_id: str
    target_url: str
    frequency: str
    last_successful_run: Optional[str]
    status: str
    consecutive_failures: int

class OSINTResponse(BaseModel):
    active_scrapers: List[AutonomousScraper]
    total_data_points_collected: int
    alpha_contribution_pct: float
