import pandas as pd
from loguru import logger
import subprocess
import json
import re
from pathlib import Path
import sys

# Add src to path to import calk_extractor
# Base dir is Algo Trade/quant-engine
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.core.calk_extractor import CALKExtractor
from src.data.duckdb_repo import DuckDBRepo

class NLPAnalyst:
    """
    Phase 7.1: The NLP Analyst Agent.
    Ingests raw text from CALK reports/News and outputs sentiment + corporate graph edges.
    """
    
    def __init__(self, repo: DuckDBRepo):
        self.repo = repo
        self._init_ledger()

    def _init_ledger(self):
        """Initialize nlp_sentiment_ledger and supply_chain_edges tables."""
        self.repo.execute("""
            CREATE TABLE IF NOT EXISTS nlp_sentiment_ledger (
                ticker VARCHAR,
                date DATE,
                source_type VARCHAR, -- 'CALK', 'NEWS', 'PRESS_RELEASE'
                document_url TEXT,
                extracted_insight TEXT,
                sentiment_score DOUBLE,
                PRIMARY KEY (ticker, date, source_type)
            );
        """)
        
        self.repo.execute("""
            CREATE TABLE IF NOT EXISTS supply_chain_edges (
                source_ticker VARCHAR,
                target_ticker VARCHAR,
                relationship_type VARCHAR, -- 'SUPPLIER', 'CUSTOMER', 'COMPETITOR'
                weight DOUBLE DEFAULT 1.0,
                last_verified DATE,
                PRIMARY KEY (source_ticker, target_ticker, relationship_type)
            );
        """)

    def analyze_ticker(self, ticker: str, pdf_path: str = None):
        """
        Extract text and run LLM analysis for a ticker.
        """
        logger.info(f"NLP Analyst: Starting analysis for {ticker}...")
        
        text = ""
        source_type = "NEWS"
        
        if pdf_path and Path(pdf_path).exists():
            extractor = CALKExtractor(pdf_path)
            text = extractor.get_text_chunks(max_pages=20) # Analyze MD&A / Notes
            source_type = "CALK"
        else:
            # Fallback to news scraping if PDF not provided
            # In a real run, we'd fetch latest news text
            text = f"Sample news flow for {ticker}: Market expects growth in the auto sector despite supply chain bottlenecks."
            
        if not text:
            return

        prompt = f"""
        ACT as an Expert Equity Analyst. Analyze this financial text for {ticker} 
        and extract sentiment and corporate supply chain relationships.
        
        TEXT:
        {text[:5000]} # Truncate for prompt limits
        
        REQUIREMENTS:
        1. Output a STRICT JSON payload.
        2. 'sentiment_score': Float between -1.0 (extremely bearish) and 1.0 (extremely bullish).
        3. 'insight': 1-sentence key takeaway.
        4. 'related_entities': List of other IDX tickers mentioned and their relationship to {ticker}.
           Format: [ {{"ticker": "ASII", "relationship": "CUSTOMER"}}, ... ]
        
        JSON ONLY.
        """
        
        try:
            # Invoke Hermes
            process = subprocess.run(["python", "-m", "hermes_agent", "-z", "-q", prompt], 
                                    capture_output=True, text=True, encoding='utf-8')
            
            raw_output = process.stdout
            
            # Extract JSON
            json_match = re.search(r'\{.*\}', raw_output, re.DOTALL)
            if not json_match:
                logger.error(f"No JSON found in LLM output for {ticker}")
                return
                
            data = json.loads(json_match.group(0))
            
            # 1. Store Sentiment
            self.repo.execute("""
                INSERT OR REPLACE INTO nlp_sentiment_ledger (ticker, date, source_type, extracted_insight, sentiment_score)
                VALUES (?, CURRENT_DATE, ?, ?, ?)
            """, [ticker, source_type, data.get('insight', ''), data.get('sentiment_score', 0.0)])
            
            # 2. Store Supply Chain Edges
            for entity in data.get('related_entities', []):
                rel_ticker = entity.get('ticker')
                rel_type = entity.get('relationship', 'UNKNOWN')
                
                if rel_ticker and rel_ticker != ticker:
                    # In Supply Chain, if X is supplier of Y, edge is X -> Y
                    # Logic: If relate_entity is CUSTOMER of ticker, then ticker -> rel_ticker
                    # If related_entity is SUPPLIER of ticker, then rel_ticker -> ticker
                    
                    source = ticker if rel_type == 'CUSTOMER' else rel_ticker
                    target = rel_ticker if rel_type == 'CUSTOMER' else ticker
                    
                    self.repo.execute("""
                        INSERT OR REPLACE INTO supply_chain_edges (source_ticker, target_ticker, relationship_type, last_verified)
                        VALUES (?, ?, ?, CURRENT_DATE)
                    """, [source, target, rel_type])
            
            logger.success(f"NLP Analysis complete for {ticker}: Sentiment={data.get('sentiment_score')}")
            
        except Exception as e:
            logger.error(f"NLP Analysis failed for {ticker}: {e}")

    def run_bulk(self, n: int = 50):
        """Analyze top N tickers from the universe."""
        tickers = self.repo.execute("SELECT ticker FROM idx_metadata WHERE status = 'ACTIVE' LIMIT ?", [n]).df()['ticker'].tolist()
        for t in tickers:
            self.analyze_ticker(t)
