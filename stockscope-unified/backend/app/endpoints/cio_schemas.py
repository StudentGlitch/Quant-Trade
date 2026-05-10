from pydantic import BaseModel
from typing import List, Optional

class RiskState(BaseModel):
    date: str
    var_99: float
    cvar_99: float
    regime: str
    kill_switch_engaged: bool
    recommended_cash_pct: float

class ShareholderReport(BaseModel):
    report_id: str
    publish_date: str
    markdown_content: str
    prev_week_pnl: float

class CIODeskResponse(BaseModel):
    current_risk: RiskState
    historical_risk_series: List[RiskState]
    latest_report: Optional[ShareholderReport]
    recent_reports: List[ShareholderReport]
