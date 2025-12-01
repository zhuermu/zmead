"""API dependencies for authentication and database access."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.services.auth import AuthService

# Security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Get current authenticated user from JWT token."""
    # Development mode: skip authentication and use/create test user
    if settings.disable_auth:
        return await _get_or_create_dev_user(db, request)

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(int(user_id))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Set user_id in request state for rate limiting
    request.state.user_id = user.id
    request.state.user = user

    return user


async def _get_or_create_dev_user(db: AsyncSession, request: Request) -> User:
    """Get or create development test user when auth is disabled."""
    dev_email = "dev@example.com"
    
    # Try to find existing dev user
    stmt = select(User).where(User.email == dev_email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        # Create dev user
        user = User(
            email=dev_email,
            display_name="Dev User",
            avatar_url=None,
            oauth_provider="dev",
            oauth_id="dev-user-1",
            gifted_credits=Decimal("10000.00"),  # Generous credits for testing
            purchased_credits=Decimal("0.00"),
            last_login_at=datetime.now(UTC),
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
    else:
        # Update last login
        user.last_login_at = datetime.now(UTC)
        await db.flush()
    
    # Set user_id in request state for rate limiting
    request.state.user_id = user.id
    request.state.user = user
    
    return user


async def get_optional_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User | None:
    """Get current user if authenticated, None otherwise."""
    if not credentials:
        return None

    try:
        return await get_current_user(request, credentials, db)
    except HTTPException:
        return None


# Type aliases for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]


async def verify_service_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> bool:
    """Verify that the request has a valid service token.

    This is used for system-level API endpoints that are called by
    internal services (e.g., AI Orchestrator) not end users.

    Raises:
        HTTPException: If token is missing or invalid
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Service token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    service_token = settings.ai_orchestrator_service_token

    if not service_token or token != service_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return True


# Type alias for service token verification
ServiceTokenVerified = Annotated[bool, Depends(verify_service_token)]
