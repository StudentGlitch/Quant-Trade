
from sqlmodel import SQLModel, create_engine
import os
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.models import FinancialReport, FinancialFact, CrawlLog
from app.database import engine

def init_db():
    SQLModel.metadata.create_all(engine)
    print("Database initialized with all models.")

if __name__ == "__main__":
    init_db()
