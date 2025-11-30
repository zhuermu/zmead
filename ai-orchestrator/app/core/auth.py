"""Service authentication for AI Orchestrator.

This module provides authentication utilities for validating
service-to-service tokens from the Web Platform.

Requirements: Security
"""

import structlog
from fastapi import Depends, Header, HTTPException, status

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        self.message = message
        super().__init__(message)


async def validate_service_token(
    authorization: str | None = Header(None, alias="Authorization"),
) -> str:
    """Validate service token from Authorization header.

    This is a FastAPI dependency that extracts and validates the Bearer token
    from the Authorization header. It compares against the configured
    WEB_PLATFORM_SERVICE_TOKEN.

    Args:
        authorization: Authorization header value (Bearer <token>)

    Returns:
        The validated token string

    Raises:
        HTTPException(401): If token is missing or invalid

    Example:
        @app.post("/chat")
        async def chat(token: str = Depends(validate_service_token)):
            # token is validated
            pass
    """
    settings = get_settings()

    # Check if Authorization header is present
    if not authorization:
        logger.warning(
            "auth_missing_header",
            error="Authorization header missing",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Authorization header is required",
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check Bearer prefix
    if not authorization.startswith("Bearer "):
        logger.warning(
            "auth_invalid_format",
            error="Invalid authorization format",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "INVALID_TOKEN",
                    "message": "Invalid authorization format. Expected: Bearer <token>",
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract token
    token = authorization[7:]  # Remove "Bearer " prefix

    if not token:
        logger.warning(
            "auth_empty_token",
            error="Empty token",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "INVALID_TOKEN",
                    "message": "Token is empty",
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate token against configured service token
    expected_token = settings.web_platform_service_token

    if token != expected_token:
        logger.warning(
            "auth_invalid_token",
            error="Token mismatch",
            # Don't log the actual tokens for security
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "INVALID_TOKEN",
                    "message": "Invalid service token",
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug("auth_success")

    return token


def get_service_token_dependency():
    """Get the service token validation dependency.

    Returns a dependency that can be used in FastAPI routes.

    Example:
        from app.core.auth import get_service_token_dependency

        @app.post("/chat")
        async def chat(_: str = Depends(get_service_token_dependency())):
            pass
    """
    return Depends(validate_service_token)
