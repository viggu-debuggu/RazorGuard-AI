from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.database.session import verify_db_connection, engine
from app.models import Base
from app.api.endpoints import auth, transactions, graph, policies
from app.core.limiter import limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

# 1. Initialize structured logging configuration
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validates core services at boot time."""
    logger.info("system_booting_checks")
    
    # Ensure all tables exist (Alembic fallback)
    Base.metadata.create_all(bind=engine)
    
    # Check Database connection
    if verify_db_connection():
        logger.info("database_connectivity_active")
    else:
        logger.warning("database_connectivity_failed_verify_configurations")
        
    logger.info("system_ready_for_requests", api_prefix=settings.API_PREFIX)
    yield


# 2. Instantiate FastAPI Application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="RazorGuard AI autonomous payment risk manager API gateway",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    lifespan=lifespan
)

# Attach rate limiter to app state and register exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 3. Configure CORS Middlewares
origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Include endpoints routers
app.include_router(auth.router, prefix=f"{settings.API_PREFIX}/auth", tags=["Authentication"])
app.include_router(transactions.router, prefix=f"{settings.API_PREFIX}/transactions", tags=["Transactions Queue"])
app.include_router(graph.router, prefix=f"{settings.API_PREFIX}/graph", tags=["Knowledge Graph"])
app.include_router(policies.router, prefix=f"{settings.API_PREFIX}/policies", tags=["Compliance RAG"])

@app.get("/", tags=["System Diagnostics"])
def read_root():
    """Root endpoint for status check diagnostics."""
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT
    }
