"""MCP authentication utilities."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import decode_token
from app.models.user import User
from app.services.auth import AuthService

logger = logging.getLogger(__name__)


class MCPAuthError(Exception):
    """Raised when MCP authentication fails."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def is_service_token(token: str) -> bool:
    """Check if the token is a valid service-to-service token.

    Args:
        token: Token to check

    Returns:
        True if valid service token
    """
    settings = get_settings()
    service_token = settings.ai_orchestrator_service_token

    if not service_token:
        return False

    return token == service_token


async def authenticate_mcp_request(
    token: str | None,
    db: AsyncSession,
    user_id: str | int | None = None,
) -> User | None:
    """Authenticate an MCP request using JWT token or service token.

    MCP requests can use either:
    1. JWT tokens from the REST API (user auth)
    2. Service tokens for service-to-service communication (AI orchestrator)

    When using service tokens, user_id should be provided to identify
    which user the operation is for.

    Args:
        token: JWT token or service token (without "Bearer " prefix)
        db: Database session
        user_id: Optional user ID for service token requests

    Returns:
        Authenticated User or None for service token auth

    Raises:
        MCPAuthError: If authentication fails
    """
    if not token:
        raise MCPAuthError("认证失败，请重新登录")

    # First, check if it's a service token from AI orchestrator
    if is_service_token(token):
        logger.debug("MCP request authenticated via service token")

        # If user_id is provided, fetch the user
        if user_id:
            auth_service = AuthService(db)
            user = await auth_service.get_user_by_id(int(user_id))
            if user:
                return user

        # For service token auth without user_id, return None
        # The tool handler should handle this case appropriately
        return None

    # Try JWT token authentication
    payload = decode_token(token)

    if not payload:
        raise MCPAuthError("认证失败，请重新登录")

    if payload.get("type") != "access":
        raise MCPAuthError("认证失败，请重新登录")

    user_id_from_token = payload.get("sub")
    if not user_id_from_token:
        raise MCPAuthError("认证失败，请重新登录")

    # Get user from database
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(int(user_id_from_token))

    if not user:
        raise MCPAuthError("认证失败，请重新登录")

    return user


def extract_token_from_header(authorization: str | None) -> str | None:
    """Extract token from Authorization header.
    
    Args:
        authorization: Authorization header value
        
    Returns:
        Token string or None
    """
    if not authorization:
        return None

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]
