"""
database.py
Sets up the SQLAlchemy engine, session factory, and declarative base.
Uses SQLite for simplicity — swap SQLALCHEMY_DATABASE_URL for Postgres later
without changing any other file.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./finance_tracker.db"

# check_same_thread=False is required only for SQLite (allows use across
# FastAPI's threaded request handling)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    FastAPI dependency — yields a DB session per request and
    guarantees it's closed afterwards, even if an error occurs.
    Usage in routes: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()