# backend/app/core/database.py
# ─────────────────────────────────────────────────────────────
#  Połączenie z PostgreSQL + dependency injection dla FastAPI
# ─────────────────────────────────────────────────────────────

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://soolevo:soolevo@localhost:5432/soolevo"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — dostarcza sesję DB i zamyka ją po requestcie."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
