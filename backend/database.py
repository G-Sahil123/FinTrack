from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
# Expected format: mysql+pymysql://user:password@host:port/dbname
assert DATABASE_URL is not None
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,       
    pool_recycle=300,          
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency that provides a DB session and ensures it's closed after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()