from sqlmodel import create_engine, Session
import os
from dotenv import load_dotenv

load_dotenv()

database_url = os.getenv("DATABASE_URL")

engine = create_engine(database_url, echo=True)

def get_session():
    with Session(engine) as session:
        yield session
