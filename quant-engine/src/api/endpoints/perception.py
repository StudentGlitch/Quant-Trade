from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from src.data.duckdb_repo import DuckDBRepo

router = APIRouter()

class AudioInsight(BaseModel):
    media_id: str
    ticker: str
    event_type: str
    hesitation_index: float
    audio_sentiment_score: float
    transcript: str

class VisionInsight(BaseModel):
    image_id: str
    ticker: str
    source_document: str
    visual_insight_summary: str
    bullish_confidence: float

class PerceptionResponse(BaseModel):
    audio_insights: List[AudioInsight]
    vision_insights: List[VisionInsight]

def get_repo() -> DuckDBRepo:
    return DuckDBRepo("storage/db/quant_data.duckdb")

@router.get("/{ticker}", response_model=PerceptionResponse)
def get_ticker_perception(ticker: str):
    repo = get_repo()
    
    # 1. Fetch Audio Insights
    audio_df = repo.con.execute("""
        SELECT media_id, ticker, event_type, hesitation_index, audio_sentiment_score, transcript
        FROM audio_perception_ledger
        WHERE ticker = ?
        ORDER BY date DESC
    """, [ticker]).df()
    
    audio_insights = []
    for _, row in audio_df.iterrows():
        audio_insights.append(AudioInsight(
            media_id=row['media_id'],
            ticker=row['ticker'],
            event_type=row['event_type'],
            hesitation_index=float(row['hesitation_index']),
            audio_sentiment_score=float(row['audio_sentiment_score']),
            transcript=row['transcript']
        ))

    # 2. Fetch Vision Insights
    vision_df = repo.con.execute("""
        SELECT image_id, ticker, source_document, visual_insight_summary, bullish_confidence
        FROM vision_perception_ledger
        WHERE ticker = ?
        ORDER BY date DESC
    """, [ticker]).df()
    
    vision_insights = []
    for _, row in vision_df.iterrows():
        vision_insights.append(VisionInsight(
            image_id=row['image_id'],
            ticker=row['ticker'],
            source_document=row['source_document'],
            visual_insight_summary=row['visual_insight_summary'],
            bullish_confidence=float(row['bullish_confidence'])
        ))
        
    return PerceptionResponse(
        audio_insights=audio_insights,
        vision_insights=vision_insights
    )
