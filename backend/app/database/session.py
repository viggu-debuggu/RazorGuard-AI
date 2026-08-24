from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings
from app.core.logging import logger

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Check connection health before using
    pool_size=10,        # Max connection pool size
    max_overflow=20,     # Max overflow connections
    pool_recycle=3600    # Recycle connections after 1 hour
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator:
    """FastAPI dependency to yield database sessions with safe teardown."""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error("database_session_error", error=str(e))
        db.rollback()
        raise
    finally:
        db.close()


def verify_db_connection() -> bool:
    """Verifies database connectivity at startup."""
    try:
        with engine.connect() as connection:
            from sqlalchemy import text
            connection.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error("database_connection_check_failed", error=str(e))
        return False
