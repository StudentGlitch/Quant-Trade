from sqlmodel import Session, SQLModel
from .database import engine
from .models import FinancialReport, FinancialFact

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def create_reports():
    with Session(engine) as session:
        # Ticker: WAPO (Growth story)
        report1 = FinancialReport(ticker="WAPO", year=2022, total_assets=1500000000, net_income=50000000, outstanding_shares=1000000)
        report2 = FinancialReport(ticker="WAPO", year=2023, total_assets=1600000000, net_income=60000000, outstanding_shares=1000000)
        
        # Ticker: ADES (High quality)
        report3 = FinancialReport(ticker="ADES", year=2022, total_assets=1200000000, net_income=80000000, outstanding_shares=500000)
        report4 = FinancialReport(ticker="ADES", year=2023, total_assets=1300000000, net_income=120000000, outstanding_shares=500000)
        
        session.add(report1)
        session.add(report2)
        session.add(report3)
        session.add(report4)
        
        # Add facts for ADES (High score)
        fact1 = FinancialFact(ticker="ADES", fact_key="operating_cash_flow", value=150000000, period="2023-FY")
        fact2 = FinancialFact(ticker="ADES", fact_key="depreciation_calk", value=20000000, period="2023-FY")
        
        session.add(fact1)
        session.add(fact2)
        
        session.commit()

if __name__ == "__main__":
    create_db_and_tables()
    create_reports()
    print("Database seeded successfully!")
