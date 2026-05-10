from pydantic import BaseModel
from typing import List, Optional

class GraphNode(BaseModel):
    id: str
    group: str
    sentiment_30d: float

class GraphEdge(BaseModel):
    source: str
    target: str
    type: str
    value: float

class KnowledgeGraphResponse(BaseModel):
    nodes: List[GraphNode]
    links: List[GraphEdge]

class SentimentSnapshot(BaseModel):
    date: str
    sentiment_score: float
    insight: str

class OHLCVData(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int

class TickerTearsheet(BaseModel):
    ticker: str
    company_name: str
    market_cap: float
    pe_ratio: float
    pb_ratio: float
    roe: float
    dividend_yield: float
    ohlcv_history: List[OHLCVData]
