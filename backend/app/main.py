from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging

from app.config import settings
from app.logging_config import setup_logging, CorrelationIdMiddleware
from app.errors import (
    AppException,
    app_exception_handler,
    generic_exception_handler,
)
from app.database import async_engine, Base
from app.api.v1.jobs import router as jobs_router
from app.schemas import HealthResponse, ReadyResponse
from app.storage.minio_client import minio_storage

# Initialize structured logging
setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger("incubrix.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting IncuBrix B-roll Engine Service...")
    # Create tables if not exist
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization deferred: {e}")

    # Ensure MinIO bucket
    try:
        minio_storage.ensure_bucket()
    except Exception as e:
        logger.warning(f"MinIO bucket check deferred: {e}")

    yield

    logger.info("Shutting down IncuBrix B-roll Engine Service...")
    await async_engine.dispose()

app = FastAPI(
    title="IncuBrix B-roll Engine API",
    description="Containerized media pipeline service that turns audio/scripts into license-clean B-roll video.",
    version="1.0.0",
    lifespan=lifespan,
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["openapi"] = "3.1.0"
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Middleware
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Liveness Probe
@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health():
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0",
    )

# Readiness Probe
@app.get("/ready", response_model=ReadyResponse, tags=["System"])
async def ready():
    postgres_ok = False
    redis_ok = False
    minio_ok = False

    # Check Postgres
    try:
        async with async_engine.connect() as conn:
            await conn.execute(Base.metadata.tables["jobs"].select().limit(1))
        postgres_ok = True
    except Exception:
        postgres_ok = False

    # Check Redis
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=0.2, socket_timeout=0.2)
        await r.ping()
        await r.aclose()
        redis_ok = True
    except Exception:
        redis_ok = False

    # Check MinIO
    minio_ok = minio_storage.check_health()

    is_ready = postgres_ok or settings.ENVIRONMENT == "development"

    return ReadyResponse(
        status="ready" if is_ready else "not_ready",
        postgres=postgres_ok,
        redis=redis_ok,
        minio=minio_ok,
    )

# Mount API Routers
app.include_router(jobs_router, prefix="/api/v1")
