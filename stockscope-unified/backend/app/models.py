from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class FinancialReportBase(SQLModel):
    ticker: str = Field(index=True)
    year: int = Field(index=True)
    total_assets: Optional[int] = None
    net_income: Optional[int] = None
    outstanding_shares: Optional[int] = None

class FinancialReport(FinancialReportBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

class FinancialReportRead(FinancialReportBase):
    id: int

class LiveTickerResponse(SQLModel):
    ticker: str
    current_price: float
    timestamp: str

class FinancialFact(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(index=True)
    fact_key: str = Field(index=True) # e.g., "revenue", "pe_ratio"
    value: float
    period: str  # e.g., "2023-Q4", "2024-05-02"
    crawled_at: datetime = Field(default_factory=datetime.now)

class CrawlLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(index=True)
    phase: str
    status: str
    records_inserted: int = 0
    records_updated: int = 0
    error_message: Optional[str] = None
    duration_seconds: float = 0.0
    crawled_at: datetime = Field(default_factory=datetime.now)
