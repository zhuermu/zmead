"""Campaign management API endpoints."""

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.campaign import (
    AdPlatform,
    CampaignCreate,
    CampaignFilter,
    CampaignListResponse,
    CampaignResponse,
    CampaignStatus,
    CampaignUpdate,
)
from app.services.campaign import (
    AdAccountNotActiveError,
    AdAccountNotFoundError,
    CampaignNotFoundError,
    CampaignService,
)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("", response_model=CampaignListResponse)
async def list_campaigns(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    platform: AdPlatform | None = Query(None, description="Filter by platform"),
    status: CampaignStatus | None = Query(None, description="Filter by status"),
    ad_account_id: int | None = Query(None, description="Filter by ad account"),
) -> CampaignListResponse:
    """List user's campaigns with optional filters and pagination.

    Returns all campaigns for the authenticated user, excluding deleted
    campaigns by default. Use status=deleted to see deleted campaigns.
    """
    service = CampaignService(db)

    filters = CampaignFilter(
        platform=platform,
        status=status,
        ad_account_id=ad_account_id,
    )

    result = await service.get_list(
        user_id=current_user.id,
        filters=filters,
        page=page,
        page_size=page_size,
    )

    return CampaignListResponse(
        campaigns=[CampaignResponse.model_validate(c) for c in result["campaigns"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        has_more=result["has_more"],
    )



@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    db: DbSession,
    current_user: CurrentUser,
    data: CampaignCreate,
) -> CampaignResponse:
    """Create a new campaign.

    Creates a campaign in draft status. The campaign is associated with
    the specified ad account and inherits its platform.

    The ad account must be active (status='active') to create campaigns.
    """
    service = CampaignService(db)

    try:
        campaign = await service.create(
            user_id=current_user.id,
            data=data,
        )
        await db.commit()
        return CampaignResponse.model_validate(campaign)
    except AdAccountNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ad account {e.ad_account_id} not found",
        )
    except AdAccountNotActiveError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ad account {e.ad_account_id} is not active. Please reauthorize the account.",
        )


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    db: DbSession,
    current_user: CurrentUser,
    campaign_id: int,
) -> CampaignResponse:
    """Get campaign details by ID.

    Returns the real-time status and all campaign details.
    """
    service = CampaignService(db)

    campaign = await service.get_by_id(
        campaign_id=campaign_id,
        user_id=current_user.id,
    )

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )

    return CampaignResponse.model_validate(campaign)


@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    db: DbSession,
    current_user: CurrentUser,
    campaign_id: int,
    data: CampaignUpdate,
) -> CampaignResponse:
    """Update a campaign.

    Updates the campaign in the database. If the campaign has been synced
    to an ad platform (has platform_campaign_id), changes will also be
    synced to the platform.
    """
    service = CampaignService(db)

    try:
        campaign = await service.update(
            campaign_id=campaign_id,
            user_id=current_user.id,
            data=data,
        )
        await db.commit()
        return CampaignResponse.model_validate(campaign)
    except CampaignNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    db: DbSession,
    current_user: CurrentUser,
    campaign_id: int,
) -> None:
    """Delete a campaign.

    Performs a soft delete - marks the campaign as deleted but preserves
    the record for historical purposes. The campaign will no longer appear
    in list queries by default.
    """
    service = CampaignService(db)

    try:
        await service.delete(
            campaign_id=campaign_id,
            user_id=current_user.id,
        )
        await db.commit()
    except CampaignNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )


@router.get("/{campaign_id}/status", response_model=dict)
async def get_campaign_status(
    db: DbSession,
    current_user: CurrentUser,
    campaign_id: int,
) -> dict:
    """Get real-time campaign status.

    Returns the current status of the campaign.
    """
    service = CampaignService(db)

    status_value = await service.get_campaign_status(
        campaign_id=campaign_id,
        user_id=current_user.id,
    )

    if status_value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )

    return {"campaign_id": campaign_id, "status": status_value}



@router.post("/{campaign_id}/sync", response_model=dict)
async def sync_campaign_to_platform(
    db: DbSession,
    current_user: CurrentUser,
    campaign_id: int,
) -> dict:
    """Sync a campaign to its ad platform.

    Creates or updates the campaign on the associated ad platform
    (Meta, TikTok, or Google). The campaign must have an active
    ad account with valid credentials.

    Returns the sync result including the platform campaign ID
    if successful.
    """
    service = CampaignService(db)

    try:
        result = await service.sync_to_platform(
            campaign_id=campaign_id,
            user_id=current_user.id,
        )
        await db.commit()

        return {
            "campaign_id": campaign_id,
            "success": result.success,
            "platform_campaign_id": result.platform_campaign_id,
            "error_message": result.error_message,
            "error_code": result.error_code,
        }
    except CampaignNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )
