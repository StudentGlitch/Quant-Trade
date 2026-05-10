
from sqlmodel import Session, select
from typing import Dict, List, Optional
from loguru import logger

from .models import FinancialReport, FinancialFact
from .database import engine

class ScoringEngine:
    def __init__(self):
        self.session = Session(engine)

    def calculate_piotroski_f_score(self, ticker: str, year: int) -> int:
        """Calculate a simplified Piotroski F-Score (0-9)."""
        score = 0
        
        # Fetch current and previous year reports
        current = self._get_report(ticker, year)
        prev = self._get_report(ticker, year - 1)
        
        if not current:
            return 0
            
        # 1. Profitability: Positive Net Income
        if current.net_income and current.net_income > 0:
            score += 1
            
        # 2. Profitability: Positive ROA
        if current.net_income and current.total_assets and current.total_assets > 0:
            roa = current.net_income / current.total_assets
            if roa > 0:
                score += 1
                
            # 3. Efficiency: ROA vs Prev
            if prev and prev.net_income and prev.total_assets:
                prev_roa = prev.net_income / prev.total_assets
                if roa > prev_roa:
                    score += 1

        # 4. Dilution: Outstanding Shares vs Prev
        if current.outstanding_shares and prev and prev.outstanding_shares:
            if current.outstanding_shares <= prev.outstanding_shares:
                score += 1
        elif current.outstanding_shares and not prev:
            # Assume no dilution if no prev data
            score += 1

        # 5. Accruals (using CALK facts if available)
        # We need Operating Cash Flow for this.
        ocf = self._get_fact(ticker, year, "operating_cash_flow")
        if ocf is not None and current.net_income:
            if ocf > 0:
                score += 1 # Criterion: Positive OCF
            if ocf > current.net_income:
                score += 1 # Criterion: OCF > Net Income

        return score

    def _get_report(self, ticker: str, year: int) -> Optional[FinancialReport]:
        statement = select(FinancialReport).where(
            FinancialReport.ticker == ticker, 
            FinancialReport.year == year
        )
        return self.session.exec(statement).first()

    def _get_fact(self, ticker: str, year: int, key: str) -> Optional[float]:
        statement = select(FinancialFact).where(
            FinancialFact.ticker == ticker,
            FinancialFact.period.like(f"{year}%"),
            FinancialFact.fact_key == key
        )
        fact = self.session.exec(statement).first()
        return fact.value if fact else None

def score_ticker(ticker: str, year: int):
    engine = ScoringEngine()
    f_score = engine.calculate_piotroski_f_score(ticker, year)
    print(f"Piotroski F-Score for {ticker} ({year}): {f_score}/9")
    return f_score

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        score_ticker(sys.argv[1], int(sys.argv[2] if len(sys.argv) > 2 else 2023))
