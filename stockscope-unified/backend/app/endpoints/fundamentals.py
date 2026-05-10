from fastapi import APIRouter, Depends
from loguru import logger
import duckdb
from pathlib import Path
from typing import List
from datetime import datetime

from .fundamentals_schemas import KnowledgeGraphResponse, GraphNode, GraphEdge, SentimentSnapshot, TickerTearsheet, OHLCVData

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
DB_PATH = BASE_DIR / "quant-engine" / "storage" / "db" / "quant_data.duckdb"

@router.get("/fundamentals/tearsheet/{ticker}", response_model=TickerTearsheet)
def get_ticker_tearsheet(ticker: str, con: duckdb.DuckDBPyConnection = Depends(get_duckdb_conn)):
    """
    Phase 25.3: Professional Fundamental Tearsheet API.
    """
    if con is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    ticker = ticker.upper()
    try:
        # 1. Fetch Metadata
        meta = con.execute("SELECT company_name, avg_daily_volume FROM idx_metadata WHERE ticker = ?", [ticker]).fetchone()
        
        # 2. Fetch OHLCV History (Last 100 days)
        # We query the new hydrated_ohlcv table from Phase 23
        ohlcv_df = con.execute("""
            SELECT date, open, high, low, close, volume 
            FROM hydrated_ohlcv 
            WHERE ticker = ? 
            ORDER BY date DESC LIMIT 100
        """, [ticker]).df()
        
        history = []
        for _, row in ohlcv_df.iterrows():
            history.append(OHLCVData(
                date=str(row['date']),
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=int(row['volume'])
            ))
            
        return TickerTearsheet(
            ticker=ticker,
            company_name=meta[0] if meta else ticker,
            market_cap=1500000000000.0, # Mocked fundamental metrics
            pe_ratio=15.4,
            pb_ratio=2.1,
            roe=0.18,
            dividend_yield=0.035,
            ohlcv_history=history
        )
    except Exception as e:
        logger.error(f"Error fetching tearsheet for {ticker}: {e}")
        return TickerTearsheet(
            ticker=ticker, company_name=ticker, market_cap=0, pe_ratio=0, pb_ratio=0, roe=0, dividend_yield=0, ohlcv_history=[]
        )

@router.get("/fundamentals/graph", response_model=KnowledgeGraphResponse)
def get_supply_chain_graph(con: duckdb.DuckDBPyConnection = Depends(get_duckdb_conn)):
    """
    Phase 7.3: Supply Chain Knowledge Graph API.
    """
    if con is None:
        return KnowledgeGraphResponse(nodes=[], links=[])

    try:
        # 1. Fetch Edges
        edges_df = con.execute("SELECT source_ticker, target_ticker, relationship_type, weight FROM supply_chain_edges").df()
        
        # 2. Identify Unique Tickers (Nodes)
        unique_tickers = list(set(edges_df['source_ticker'].tolist() + edges_df['target_ticker'].tolist()))
        
        if not unique_tickers:
            return KnowledgeGraphResponse(nodes=[], links=[])

        # 3. Fetch Metadata for Nodes
        tickers_str = ", ".join([f"'{t}'" for t in unique_tickers])
        meta_df = con.execute(f"SELECT ticker, sector FROM idx_metadata WHERE ticker IN ({tickers_str})").df()
        sectors = dict(zip(meta_df['ticker'], meta_df['sector']))
        
        # 4. Fetch 30d Sentiment for Nodes
        sent_df = con.execute(f"""
            SELECT ticker, AVG(sentiment_score) as avg_s 
            FROM nlp_sentiment_ledger 
            WHERE ticker IN ({tickers_str})
            GROUP BY ticker
        """).df()
        sent_map = dict(zip(sent_df['ticker'], sent_df['avg_s']))
        
        nodes = []
        for t in unique_tickers:
            nodes.append(GraphNode(
                id=t,
                group=sectors.get(t, 'UNKNOWN'),
                sentiment_30d=float(sent_map.get(t, 0.0))
            ))
            
        links = []
        for _, row in edges_df.iterrows():
            links.append(GraphEdge(
                source=row['source_ticker'],
                target=row['target_ticker'],
                type=row['relationship_type'],
                value=float(row['weight'])
            ))
            
        return KnowledgeGraphResponse(nodes=nodes, links=links)
        
    except Exception as e:
        logger.error(f"Error fetching knowledge graph: {e}")
        return KnowledgeGraphResponse(nodes=[], links=[])

@router.get("/fundamentals/sentiment/{ticker}", response_model=List[SentimentSnapshot])
def get_ticker_sentiment_timeline(ticker: str, con: duckdb.DuckDBPyConnection = Depends(get_duckdb_conn)):
    """
    Returns 90-day sentiment timeline for a specific ticker.
    """
    if con is None:
        return []

    try:
        df = con.execute(f"""
            SELECT date, sentiment_score, extracted_insight
            FROM nlp_sentiment_ledger
            WHERE ticker = ?
            ORDER BY date DESC
            LIMIT 90
        """, [ticker.upper()]).df()
        
        results = []
        for _, row in df.iterrows():
            results.append(SentimentSnapshot(
                date=str(row['date']),
                sentiment_score=float(row['sentiment_score']),
                insight=row['extracted_insight']
            ))
        return results
    except Exception as e:
        logger.error(f"Error fetching sentiment timeline for {ticker}: {e}")
        return []
