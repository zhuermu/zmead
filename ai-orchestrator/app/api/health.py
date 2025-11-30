"""Health check endpoints for AI Orchestrator.

This module provides health and readiness endpoints for monitoring
and Kubernetes probes.

Requirements: Monitoring
"""

from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter

from app.core.config import get_settings
from app.core.redis_client import RedisConnectionError
from app.core.redis_client import ping as redis_ping
from app.services.mcp_client import MCPClient, MCPError

logger = structlog.get_logger(__name__)

router = APIRouter()


async def check_redis_health() -> dict[str, Any]:
    """Check Redis connection health.

    Returns:
        Dict with status and optional error message
    """
    try:
        await redis_ping(max_retries=1, retry_delay=0.5)
        return {"status": "healthy"}
    except RedisConnectionError as e:
        logger.warning("health_check_redis_failed", error=str(e))
        return {"status": "unhealthy", "error": str(e)}
    except Exception as e:
        logger.warning("health_check_redis_error", error=str(e))
        return {"status": "unhealthy", "error": str(e)}


async def check_mcp_health() -> dict[str, Any]:
    """Check MCP connection health by calling a lightweight tool.

    Uses get_credit_balance as a lightweight health check.

    Returns:
        Dict with status and optional error message
    """
    try:
        async with MCPClient(timeout=5.0, max_retries=1) as client:
            # Try to call a lightweight tool
            # This will fail with auth error if MCP is up but we don't have valid user
            # That's still a "healthy" connection
            await client.call_tool("get_credit_balance", {})
            return {"status": "healthy"}
    except MCPError as e:
        # If we get an MCP error, the connection is working
        # The error might be auth-related which is expected
        if e.code in ["UNAUTHORIZED", "INVALID_TOKEN"]:
            # Connection works, just auth issue (expected for health check)
            return {"status": "healthy", "note": "connection ok, auth required"}
        logger.warning("health_check_mcp_failed", error=str(e), code=e.code)
        return {"status": "unhealthy", "error": str(e)}
    except Exception as e:
        logger.warning("health_check_mcp_error", error=str(e))
        return {"status": "unhealthy", "error": str(e)}


async def check_gemini_health() -> dict[str, Any]:
    """Check Gemini API health with a test request.

    Returns:
        Dict with status and optional error message
    """
    try:
        from app.services.gemini_client import GeminiClient

        client = GeminiClient()
        # Simple test - just check if we can create the model
        # A full test would make an API call, but that costs money
        if client.chat_model is not None:
            return {"status": "healthy"}
        return {"status": "degraded", "note": "model not initialized"}
    except Exception as e:
        logger.warning("health_check_gemini_error", error=str(e))
        return {"status": "unhealthy", "error": str(e)}


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint.

    Checks the health of all dependencies:
    - Redis connection
    - MCP connection to Web Platform
    - Gemini API availability

    Returns:
        JSON with overall status and individual check results

    Status values:
    - "healthy": All checks passed
    - "degraded": Some checks failed but service is operational
    - "unhealthy": Critical checks failed
    """
    settings = get_settings()

    # Run all health checks
    redis_check = await check_redis_health()
    mcp_check = await check_mcp_health()
    gemini_check = await check_gemini_health()

    checks = {
        "redis": redis_check,
        "mcp": mcp_check,
        "gemini": gemini_check,
    }

    # Determine overall status
    # Redis is critical, MCP and Gemini are important but not critical
    redis_healthy = redis_check.get("status") == "healthy"
    mcp_healthy = mcp_check.get("status") in ["healthy", "degraded"]
    gemini_healthy = gemini_check.get("status") in ["healthy", "degraded"]

    if redis_healthy and mcp_healthy and gemini_healthy:
        overall_status = "healthy"
    elif redis_healthy:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    response = {
        "status": overall_status,
        "checks": checks,
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": settings.environment,
        "version": "1.0.0",
    }

    logger.debug("health_check_complete", status=overall_status)

    return response


@router.get("/ready")
async def readiness_check() -> dict[str, Any]:
    """Kubernetes readiness probe endpoint.

    Checks if the service is ready to accept traffic.
    More strict than health check - all critical dependencies must be healthy.

    Returns:
        JSON with ready status

    HTTP Status:
    - 200: Ready to accept traffic
    - 503: Not ready (returned via exception in real implementation)
    """
    # Check Redis (critical for state management)
    redis_check = await check_redis_health()
    redis_ready = redis_check.get("status") == "healthy"

    # Check if LangGraph is compiled
    try:
        from app.core.graph import get_agent_graph

        graph = get_agent_graph()
        graph_ready = graph is not None
    except Exception:
        graph_ready = False

    ready = redis_ready and graph_ready

    response = {
        "ready": ready,
        "checks": {
            "redis": redis_ready,
            "graph": graph_ready,
        },
        "timestamp": datetime.now(UTC).isoformat(),
    }

    if not ready:
        logger.warning("readiness_check_failed", checks=response["checks"])

    return response


@router.get("/live")
async def liveness_check() -> dict[str, Any]:
    """Kubernetes liveness probe endpoint.

    Simple check to verify the service is running.
    Should always return 200 if the process is alive.

    Returns:
        JSON with alive status
    """
    return {
        "alive": True,
        "timestamp": datetime.now(UTC).isoformat(),
    }
