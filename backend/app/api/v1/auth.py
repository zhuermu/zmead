"""Authentication API endpoints."""

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from app.api.deps import CurrentUser, DbSession
from app.schemas.auth import (
    AuthResponse,
    OAuthCallbackRequest,
    TokenRefreshRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/oauth/google", response_class=RedirectResponse)
async def google_oauth_redirect(
    db: DbSession,
    state: str | None = Query(None, description="Optional state parameter"),
) -> RedirectResponse:
    """Redirect to Google OAuth authorization page."""
    auth_service = AuthService(db)
    oauth_url = auth_service.get_google_oauth_url(state)
    return RedirectResponse(url=oauth_url, status_code=status.HTTP_302_FOUND)


@router.get("/oauth/google/url")
async def get_google_oauth_url(
    db: DbSession,
    state: str | None = Query(None, description="Optional state parameter"),
) -> dict[str, str]:
    """Get Google OAuth URL without redirect (for frontend use)."""
    auth_service = AuthService(db)
    oauth_url = auth_service.get_google_oauth_url(state)
    return {"url": oauth_url}


@router.post("/oauth/callback", response_model=AuthResponse)
async def oauth_callback(
    request: OAuthCallbackRequest,
    db: DbSession,
) -> AuthResponse:
    """Handle OAuth callback with authorization code."""
    auth_service = AuthService(db)
    try:
        return await auth_service.authenticate_with_google(request.code)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth authentication failed: {str(e)}",
        )


@router.get("/oauth/callback")
async def oauth_callback_get(
    db: DbSession,
    code: str = Query(..., description="Authorization code from OAuth provider"),
    state: str | None = Query(None, description="State parameter"),
) -> AuthResponse:
    """Handle OAuth callback via GET (browser redirect)."""
    auth_service = AuthService(db)
    try:
        return await auth_service.authenticate_with_google(code)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth authentication failed: {str(e)}",
        )



@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: TokenRefreshRequest,
    db: DbSession,
) -> TokenResponse:
    """Refresh access token using refresh token."""
    auth_service = AuthService(db)
    tokens = await auth_service.refresh_tokens(request.refresh_token)
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    return tokens


@router.post("/logout")
async def logout(current_user: CurrentUser) -> dict[str, str]:
    """Logout current user (client should discard tokens)."""
    # JWT tokens are stateless, so logout is handled client-side
    # In a production system, you might want to blacklist the token
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser) -> UserResponse:
    """Get current authenticated user information."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        avatar_url=current_user.avatar_url,
        oauth_provider=current_user.oauth_provider,
        gifted_credits=current_user.gifted_credits,
        purchased_credits=current_user.purchased_credits,
        total_credits=current_user.total_credits,
        language=current_user.language,
        timezone=current_user.timezone,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login_at=current_user.last_login_at,
    )
