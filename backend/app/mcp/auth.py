"""MCP authentication utilities."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.models.user import User
from app.services.auth import AuthService


class MCPAuthError(Exception):
    """Raised when MCP authentication fails."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


async def authenticate_mcp_request(
    token: str | None,
    db: AsyncSession,
) -> User:
    """Authenticate an MCP request using service token.
    
    MCP requests use the same JWT tokens as the REST API.
    The token should be passed in the Authorization header.
    
    Args:
        token: JWT token (without "Bearer " prefix)
        db: Database session
        
    Returns:
        Authenticated User
        
    Raises:
        MCPAuthError: If authentication fails
    """
    if not token:
        raise MCPAuthError("Authentication required")

    # Decode and validate token
    payload = decode_token(token)

    if not payload:
        raise MCPAuthError("Invalid or expired token")

    if payload.get("type") != "access":
        raise MCPAuthError("Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise MCPAuthError("Invalid token payload")

    # Get user from database
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(int(user_id))

    if not user:
        raise MCPAuthError("User not found or inactive")

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
