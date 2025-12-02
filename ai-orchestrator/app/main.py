"""FastAPI application for AI Orchestrator.

This module creates and configures the FastAPI application instance,
including CORS, startup/shutdown events, and middleware.

Requirements: Infrastructure
"""

from contextlib import asynccontextmanager
from datetime import UTC, datetime

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.graph import build_agent_graph, reset_agent_graph
from app.core.graph_v3 import build_agent_graph_v3, reset_agent_graph_v3
from app.core.logging import configure_logging, set_request_id
from app.core.redis_client import close_redis_pool, init_redis_pool
from app.services.mcp_client import MCPClient
from app.tools.setup import register_all_tools
from app.agents.setup import register_all_agents

logger = structlog.get_logger(__name__)

# Global MCP client instance
_mcp_client: MCPClient | None = None


def get_mcp_client() -> MCPClient:
    """Get the global MCP client instance."""
    if _mcp_client is None:
        raise RuntimeError("MCP client not initialized. Application not started properly.")
    return _mcp_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    global _mcp_client

    settings = get_settings()

    # Configure logging
    configure_logging(
        log_level=settings.log_level,
        json_format=settings.is_production,
    )

    logger.info(
        "application_startup_begin",
        environment=settings.environment,
        app_name=settings.app_name,
    )

    # Initialize Redis connection pool
    try:
        await init_redis_pool()
        logger.info("redis_initialized")
    except Exception as e:
        logger.error("redis_initialization_failed", error=str(e))
        raise

    # Initialize MCP client and test connection
    try:
        _mcp_client = MCPClient()
        # Test connection by getting client (creates connection pool)
        await _mcp_client._get_client()
        logger.info(
            "mcp_client_initialized",
            base_url=settings.web_platform_url,
        )
    except Exception as e:
        logger.error("mcp_client_initialization_failed", error=str(e))
        # Don't fail startup - MCP might become available later
        logger.warning("mcp_client_will_retry_on_first_request")

    # Register all tools (legacy)
    try:
        register_all_tools()
        logger.info("tools_registered")
    except Exception as e:
        logger.error("tool_registration_failed", error=str(e))
        raise

    # Register all sub-agents (v3 architecture)
    try:
        register_all_agents()
        logger.info("agents_registered")
    except Exception as e:
        logger.error("agent_registration_failed", error=str(e))
        raise

    # Compile LangGraph (legacy v2)
    try:
        graph = build_agent_graph()
        logger.info("langgraph_v2_compiled")
    except Exception as e:
        logger.error("langgraph_v2_compilation_failed", error=str(e))
        raise

    # Compile LangGraph v3 (simplified architecture)
    try:
        graph_v3 = build_agent_graph_v3()
        logger.info("langgraph_v3_compiled")
    except Exception as e:
        logger.error("langgraph_v3_compilation_failed", error=str(e))
        raise

    logger.info("application_startup_complete")

    yield

    # Shutdown
    logger.info("application_shutdown_begin")

    # Close MCP client
    if _mcp_client:
        await _mcp_client.close()
        _mcp_client = None
        logger.info("mcp_client_closed")

    # Close Redis connection pool
    await close_redis_pool()
    logger.info("redis_pool_closed")

    # Reset graphs
    reset_agent_graph()
    reset_agent_graph_v3()

    logger.info("application_shutdown_complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="AI Orchestrator - Unified AI Agent for AAE Platform",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
    )

    # Register exception handlers
    from app.core.errors import register_exception_handlers

    register_exception_handlers(app)

    # Configure CORS
    # Allow web-platform origin and localhost for development
    allowed_origins = [
        settings.web_platform_url,
        "http://localhost:3000",  # Frontend dev server
        "http://localhost:8000",  # Backend dev server
    ]

    if settings.is_development:
        # Allow all origins in development
        allowed_origins.append("*")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add request logging middleware
    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        """Log all incoming requests with timing."""
        # Generate and set request ID
        request_id = request.headers.get("X-Request-ID")
        request_id = set_request_id(request_id)

        # Store request ID in request state for access in endpoints
        request.state.request_id = request_id

        start_time = datetime.now(UTC)

        # Log request start
        logger.info(
            "request_start",
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )

        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            # Log request completion
            logger.info(
                "request_complete",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            logger.error(
                "request_error",
                method=request.method,
                path=request.url.path,
                error=str(e),
                duration_ms=round(duration_ms, 2),
            )
            raise

    # Include routers
    from app.api.chat import router as chat_router
    from app.api.chat_v3 import router as chat_v3_router
    from app.api.health import router as health_router
    from app.api.campaign_automation import router as campaign_automation_router

    app.include_router(health_router, tags=["Health"])
    app.include_router(chat_router, prefix="/api/v1", tags=["Chat"])
    app.include_router(chat_v3_router, prefix="/api/v1", tags=["Chat V3"])
    app.include_router(campaign_automation_router, prefix="/api", tags=["Campaign Automation"])

    return app


# Create the application instance
app = create_app()
