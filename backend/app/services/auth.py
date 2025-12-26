"""Authentication service for OAuth and JWT management."""

from datetime import UTC, datetime
from decimal import Decimal
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    GoogleUserInfo,
    TokenResponse,
    UserResponse,
)


class AuthService:
    """Service for handling authentication operations."""

    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    def __init__(self, db: AsyncSession) -> None:
        """Initialize auth service with database session."""
        self.db = db

    def get_google_oauth_url(self, state: str | None = None) -> str:
        """Generate Google OAuth authorization URL."""
        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
        }
        if state:
            params["state"] = state
        return f"{self.GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def exchange_google_code(self, code: str) -> dict:
        """Exchange authorization code for tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.google_redirect_uri,
                },
            )
            response.raise_for_status()
            return response.json()


    async def get_google_user_info(self, access_token: str) -> GoogleUserInfo:
        """Fetch user info from Google using access token."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            data = response.json()
            return GoogleUserInfo(
                id=data["id"],
                email=data["email"],
                name=data.get("name", data["email"].split("@")[0]),
                picture=data.get("picture"),
                verified_email=data.get("verified_email", False),
            )

    async def get_or_create_user(
        self,
        oauth_provider: str,
        oauth_id: str,
        email: str,
        display_name: str,
        avatar_url: str | None = None,
    ) -> tuple[User, bool]:
        """Get existing user or create new one. Returns (user, is_new)."""
        from app.api.deps import is_super_admin

        # Try to find existing user by OAuth ID
        stmt = select(User).where(
            User.oauth_provider == oauth_provider,
            User.oauth_id == oauth_id,
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            # Update last login
            user.last_login_at = datetime.now(UTC)

            # Auto-approve super admins
            if is_super_admin(user.email) and not user.is_approved:
                user.is_approved = True

            await self.db.flush()
            return user, False

        # Check if email already exists with different OAuth
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            # Link OAuth to existing account
            existing_user.oauth_provider = oauth_provider
            existing_user.oauth_id = oauth_id
            existing_user.last_login_at = datetime.now(UTC)
            if avatar_url and not existing_user.avatar_url:
                existing_user.avatar_url = avatar_url

            # Auto-approve super admins
            if is_super_admin(existing_user.email) and not existing_user.is_approved:
                existing_user.is_approved = True

            await self.db.flush()
            return existing_user, False

        # Create new user with registration bonus
        # Super admins are auto-approved
        is_admin = is_super_admin(email)

        new_user = User(
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
            oauth_provider=oauth_provider,
            oauth_id=oauth_id,
            gifted_credits=Decimal("500.00"),  # Registration bonus
            purchased_credits=Decimal("0.00"),
            last_login_at=datetime.now(UTC),
            is_approved=is_admin,  # Auto-approve super admins
        )
        self.db.add(new_user)
        await self.db.flush()
        await self.db.refresh(new_user)
        return new_user, True

    def create_tokens(self, user: User) -> TokenResponse:
        """Create access and refresh tokens for user."""
        token_data = {"sub": str(user.id), "email": user.email}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
        )

    async def authenticate_with_google(self, code: str) -> AuthResponse:
        """Complete Google OAuth flow and return auth response.

        Raises:
            HTTPException: If user is not approved (status 403)
        """
        from fastapi import HTTPException, status
        from app.api.deps import is_super_admin

        # Exchange code for tokens
        token_data = await self.exchange_google_code(code)
        google_access_token = token_data["access_token"]

        # Get user info from Google
        user_info = await self.get_google_user_info(google_access_token)

        # Get or create user
        user, is_new = await self.get_or_create_user(
            oauth_provider="google",
            oauth_id=user_info.id,
            email=user_info.email,
            display_name=user_info.name,
            avatar_url=user_info.picture,
        )

        # Commit the database transaction to save user changes
        await self.db.commit()

        # Check if user is approved (unless they're a super admin)
        if not user.is_approved and not is_super_admin(user.email):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "PENDING_APPROVAL",
                    "message": "Your account is pending approval. Please wait for an administrator to approve your access.",
                    "user_email": user.email,
                },
            )

        # Create JWT tokens
        tokens = self.create_tokens(user)

        return AuthResponse(
            tokens=tokens,
            user=UserResponse(
                id=user.id,
                email=user.email,
                display_name=user.display_name,
                avatar_url=user.avatar_url,
                oauth_provider=user.oauth_provider,
                gifted_credits=user.gifted_credits,
                purchased_credits=user.purchased_credits,
                total_credits=user.total_credits,
                language=user.language,
                timezone=user.timezone,
                conversational_provider=user.conversational_provider,
                conversational_model=user.conversational_model,
                is_active=user.is_active,
                is_approved=user.is_approved,
                is_super_admin=is_super_admin(user.email),
                created_at=user.created_at,
                last_login_at=user.last_login_at,
            ),
        )

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse | None:
        """Refresh access token using refresh token."""
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        # Verify user exists and is active
        stmt = select(User).where(User.id == int(user_id), User.is_active == True)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return None

        return self.create_tokens(user)

    async def get_user_by_id(self, user_id: int) -> User | None:
        """Get user by ID."""
        stmt = select(User).where(User.id == user_id, User.is_active == True)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
