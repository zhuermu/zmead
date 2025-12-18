"""Main FastAPI application."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import close_db, init_db
from app.core.error_middleware import GlobalErrorHandlerMiddleware
from app.core.exception_handlers import (
    database_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.core.rate_limit import RateLimitMiddleware
from app.core.redis import close_redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()
    await close_redis()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

# Register exception handlers (these are backups, the middleware will catch most errors)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, database_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Rate Limiting
# 100 requests per minute per user (with 1.5x burst allowance)
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=100,
    burst_multiplier=1.5,
)

# IMPORTANT: Add error handler middleware LAST so it runs FIRST (outermost layer)
# This ensures ALL exceptions are caught before they reach Starlette's debug handler
app.add_middleware(GlobalErrorHandlerMiddleware)

# Include API routers
app.include_router(api_router, prefix=settings.api_v1_prefix)

# Include WebSocket router at root level (not under /api/v1)
from app.api.v1.websocket import router as websocket_router
app.include_router(websocket_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.app_version}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": f"Welcome to {settings.app_name}"}
