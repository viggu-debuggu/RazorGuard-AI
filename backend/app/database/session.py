from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings
from app.core.logging import logger

FALLBACK_SQLITE_URL = "sqlite:///./razorguard.db"
_primary_url = settings.DATABASE_URL
_is_sqlite = _primary_url.startswith("sqlite")
db_url = _primary_url

# Attempt to verify Postgres connectivity if not using SQLite initially
if not _is_sqlite:
    try:
        # Create a temporary engine to test connection quickly (timeout after 3s)
        temp_engine = create_engine(_primary_url, connect_args={"connect_timeout": 3})
        with temp_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        temp_engine.dispose()
        logger.info("database_postgres_connection_success")
    except Exception as e:
        logger.error("database_postgres_connection_failed", error=str(e))
        logger.warning("DATABASE_FALLBACK_ACTIVATED: PostgreSQL is down/unreachable. Falling back to local SQLite.")
        db_url = FALLBACK_SQLITE_URL
        settings.DATABASE_URL = FALLBACK_SQLITE_URL

_engine_kwargs: dict = {"pool_pre_ping": True}
if not db_url.startswith("sqlite"):
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20
    _engine_kwargs["pool_recycle"] = 3600
else:
    # Required for SQLite multi-thread safety in tests
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(db_url, **_engine_kwargs)
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
            connection.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error("database_connection_check_failed", error=str(e))
        return False

