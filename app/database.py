import os
from dotenv import load_dotenv 
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base , sessionmaker

load_dotenv()

SQLALCHEMY_Database_URL = os.getenv("DATABASE_URL")

if not SQLALCHEMY_Database_URL:
    raise ValueError("Database Url environment is not set")

# --- Fix Neon's URL quirk ---
if SQLALCHEMY_Database_URL.startswith("postgres://"):
    SQLALCHEMY_Database_URL = SQLALCHEMY_Database_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(SQLALCHEMY_Database_URL)

SessionLocal = sessionmaker(autocommit = False , autoflush= False , bind=engine)

base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()