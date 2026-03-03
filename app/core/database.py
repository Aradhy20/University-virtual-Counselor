"""
Database layer using SQLAlchemy + SQLite (dev) / Postgres (prod).
Provides the engine, session factory, and Base for all models.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Default to SQLite for local dev. Override with DATABASE_URL env var for Postgres.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/aditi.db")

# SQLite needs check_same_thread=False for FastAPI's async usage
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Called once at startup."""
    from app.models import student  # noqa: F401 — import so Base sees the models
    Base.metadata.create_all(bind=engine)
    print("[DB] All tables created/verified.")
