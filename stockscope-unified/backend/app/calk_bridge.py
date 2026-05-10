
import asyncio
import os
import sys
from pathlib import Path
from typing import List

from sqlmodel import Session, select, create_engine
from loguru import logger

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models import FinancialReport, FinancialFact
from app.database import engine

# Add webcrawler directory to sys.path to import extractor
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "Experiment" / "webcrawler"))
from calk_extractor import extract_from_pdf

def save_to_stockscope(record: dict):
    """Save extracted record to Stockscope database."""
    with Session(engine) as session:
        # 1. Update/Create FinancialReport entry
        statement = select(FinancialReport).where(
            FinancialReport.ticker == record["ticker_symbol"],
            FinancialReport.year == record["fiscal_year"]
        )
        report = session.exec(statement).first()
        
        if not report:
            report = FinancialReport(
                ticker=record["ticker_symbol"],
                year=record["fiscal_year"]
            )
        
        # Update fields if found
        if record.get("net_income") is not None:
            report.net_income = int(record["net_income"])
        if record.get("outstanding_shares") is not None:
            report.outstanding_shares = int(record["outstanding_shares"])
            
        session.add(report)
        
        # 2. Save detailed facts (Depreciation, Amortization)
        facts = [
            ("depreciation_calk", record.get("depreciation_calk")),
            ("amortization_calk", record.get("amortization_calk")),
        ]
        
        for key, value in facts:
            if value is not None:
                fact = FinancialFact(
                    ticker=record["ticker_symbol"],
                    fact_key=key,
                    value=float(value),
                    period=f"{record['fiscal_year']}-FY"
                )
                session.add(fact)
                
        session.commit()
        logger.info(f"Ingested CALK data for {record['ticker_symbol']} {record['fiscal_year']} into Stockscope DB")

if __name__ == "__main__":
    # Example usage: ingest from a specific JSON/dict
    # This would normally be called by the crawler loop
    print("Stockscope CALK Bridge ready.")
