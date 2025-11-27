"""Ad Account API endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.ad_account import (
    AdAccountCreate,
    AdAccountListResponse,
    AdAccountResponse,
    AdAccountUpdate,
    OAuthBindCallbackRequest,
)
from app.services.ad_account import AdAccountService

router = APIRouter(prefix="/ad-accounts", tags=["ad-accounts"])


@router.get("", response_model=AdAccountListResponse)
async def list_ad_accounts(
    current_user: CurrentUser,
    db: DbSession,
) -> AdAccountListResponse:
    """List all ad accounts for the current user."""
    service = AdAccountService(db)
    accounts = await service.list_ad_accounts(current_user.id)
    return AdAccountListResponse(accounts=accounts, total=len(accounts))


@router.post("", response_model=AdAccountResponse, status_code=status.HTTP_201_CREATED)
async def bind_ad_account(
    data: AdAccountCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> AdAccountResponse:
    """Bind a new ad account for the current user."""
    service = AdAccountService(db)
    account = await service.bind_ad_account(current_user.id, data)
    await db.commit()
    return account


@router.get("/{account_id}", response_model=AdAccountResponse)
async def get_ad_account(
    account_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> AdAccountResponse:
    """Get a specific ad account by ID."""
    service = AdAccountService(db)
    account = await service.get_ad_account(current_user.id, account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ad account not found",
        )
    return account


@router.put("/{account_id}", response_model=AdAccountResponse)
async def update_ad_account(
    account_id: int,
    data: AdAccountUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> AdAccountResponse:
    """Update an ad account."""
    service = AdAccountService(db)
    account = await service.update_ad_account(current_user.id, account_id, data)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ad account not found",
        )
    await db.commit()
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unbind_ad_account(
    account_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """Unbind (delete) an ad account."""
    service = AdAccountService(db)
    success = await service.unbind_ad_account(current_user.id, account_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ad account not found",
        )
    await db.commit()


@router.post("/{account_id}/activate", response_model=AdAccountResponse)
async def activate_ad_account(
    account_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> AdAccountResponse:
    """Set an ad account as the active one for its platform."""
    service = AdAccountService(db)
    account = await service.set_active_ad_account(current_user.id, account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ad account not found",
        )
    await db.commit()
    return account



@router.post("/{account_id}/refresh", response_model=dict)
async def refresh_ad_account_token(
    account_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Manually trigger token refresh for an ad account."""
    service = AdAccountService(db)
    account = await service.get_ad_account(current_user.id, account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ad account not found",
        )

    # Trigger async token refresh task
    from app.tasks.token_refresh import refresh_ad_account_token as refresh_task

    task = refresh_task.delay(account_id)
    return {
        "message": "Token refresh initiated",
        "task_id": task.id,
        "account_id": account_id,
    }


@router.post("/oauth/callback", response_model=AdAccountResponse, status_code=status.HTTP_201_CREATED)
async def oauth_callback(
    data: OAuthBindCallbackRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> AdAccountResponse:
    """Handle OAuth callback and bind ad account."""
    service = AdAccountService(db)
    
    # Exchange OAuth code for access token
    # This is a simplified version - in production, you'd call the actual OAuth provider
    try:
        account = await service.bind_ad_account_from_oauth(
            user_id=current_user.id,
            platform=data.platform,
            code=data.code,
            state=data.state,
        )
        await db.commit()
        return account
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to bind ad account: {str(e)}",
        )
