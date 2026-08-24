import os
import pytest
import tempfile

# Configure testing environment variables before importing app
DB_FILE_PATH = os.path.join(tempfile.gettempdir(), "razorguard_test_temp.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_FILE_PATH}"
os.environ["ENVIRONMENT"] = "development"
os.environ["LLM_PROVIDER"] = "mock"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.session import Base, get_db
from app.main import app

# Create local testing engine
engine = create_engine(os.environ["DATABASE_URL"], connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Builds the SQLite testing tables schema before tests run, and cleans up at finish."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    # Clean up local SQLite db file
    if os.path.exists(DB_FILE_PATH):
        try:
            os.remove(DB_FILE_PATH)
        except PermissionError:
            pass


@pytest.fixture
def db_session():
    """Provides a fresh database session for a single test case, rolled back at finish."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    """Provides a FastAPI TestClient configured to override database dependency checks."""
    def _get_db_override():
        try:
            yield db_session
        finally:
            pass
            
    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
