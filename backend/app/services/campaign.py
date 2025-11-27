"""Campaign service for managing advertising campaigns."""

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ad_account import AdAccount
from app.models.campaign import Campaign
from app.schemas.campaign import (
    CampaignCreate,
    CampaignFilter,
    CampaignStatus,
    CampaignUpdate,
    PlatformSyncResult,
)


class CampaignNotFoundError(Exception):
    """Raised when campaign is not found."""

    def __init__(self, campaign_id: int):
        self.campaign_id = campaign_id
        super().__init__(f"Campaign {campaign_id} not found")


class AdAccountNotFoundError(Exception):
    """Raised when ad account is not found."""

    def __init__(self, ad_account_id: int):
        self.ad_account_id = ad_account_id
        super().__init__(f"Ad account {ad_account_id} not found")


class AdAccountNotActiveError(Exception):
    """Raised when ad account is not active."""

    def __init__(self, ad_account_id: int):
        self.ad_account_id = ad_account_id
        super().__init__(f"Ad account {ad_account_id} is not active")


class CampaignService:
    """Service for campaign operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_ad_account(
        self, ad_account_id: int, user_id: int
    ) -> AdAccount | None:
        """Get ad account by ID and verify ownership."""
        result = await self.db.execute(
            select(AdAccount).where(
                AdAccount.id == ad_account_id,
                AdAccount.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()


    async def create(
        self,
        user_id: int,
        data: CampaignCreate,
    ) -> Campaign:
        """Create a new campaign.

        Args:
            user_id: Owner user ID
            data: Campaign creation data

        Returns:
            Created Campaign instance

        Raises:
            AdAccountNotFoundError: If ad account not found
            AdAccountNotActiveError: If ad account status is not active
        """
        # Verify ad account exists and belongs to user
        ad_account = await self._get_ad_account(data.ad_account_id, user_id)
        if not ad_account:
            raise AdAccountNotFoundError(data.ad_account_id)

        # Check ad account status
        if ad_account.status != "active":
            raise AdAccountNotActiveError(data.ad_account_id)

        campaign = Campaign(
            user_id=user_id,
            ad_account_id=data.ad_account_id,
            platform=ad_account.platform,
            name=data.name,
            objective=data.objective.value,
            status=CampaignStatus.DRAFT.value,
            budget=data.budget,
            budget_type=data.budget_type.value,
            targeting=data.targeting or {},
            creative_ids=data.creative_ids or [],
            landing_page_id=data.landing_page_id,
        )

        self.db.add(campaign)
        await self.db.flush()
        await self.db.refresh(campaign)

        return campaign

    async def get_by_id(
        self,
        campaign_id: int,
        user_id: int | None = None,
    ) -> Campaign | None:
        """Get campaign by ID.

        Args:
            campaign_id: Campaign ID
            user_id: Optional user ID to filter by owner

        Returns:
            Campaign instance or None if not found
        """
        query = select(Campaign).where(Campaign.id == campaign_id)

        if user_id is not None:
            query = query.where(Campaign.user_id == user_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()


    async def get_list(
        self,
        user_id: int,
        filters: CampaignFilter | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Get paginated list of campaigns.

        Args:
            user_id: Owner user ID
            filters: Optional filter criteria
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Dictionary with campaigns, total, page, page_size, has_more
        """
        # Base query - exclude deleted campaigns by default
        query = select(Campaign).where(
            Campaign.user_id == user_id,
            Campaign.status != CampaignStatus.DELETED.value,
        )

        # Apply filters
        if filters:
            if filters.status:
                # If explicitly filtering by status, override default exclusion
                query = select(Campaign).where(
                    Campaign.user_id == user_id,
                    Campaign.status == filters.status.value,
                )
            if filters.platform:
                query = query.where(Campaign.platform == filters.platform.value)
            if filters.ad_account_id:
                query = query.where(Campaign.ad_account_id == filters.ad_account_id)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Apply pagination and ordering
        offset = (page - 1) * page_size
        query = query.order_by(Campaign.created_at.desc()).offset(offset).limit(page_size)

        result = await self.db.execute(query)
        campaigns = list(result.scalars().all())

        return {
            "campaigns": campaigns,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": offset + len(campaigns) < total,
        }


    async def update(
        self,
        campaign_id: int,
        user_id: int,
        data: CampaignUpdate,
    ) -> Campaign:
        """Update a campaign.

        Args:
            campaign_id: Campaign ID
            user_id: Owner user ID
            data: Update data

        Returns:
            Updated Campaign instance

        Raises:
            CampaignNotFoundError: If campaign not found or not owned by user
        """
        campaign = await self.get_by_id(campaign_id, user_id)

        if not campaign:
            raise CampaignNotFoundError(campaign_id)

        # Update fields if provided
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "objective" and value is not None:
                setattr(campaign, field, value.value)
            elif field == "status" and value is not None:
                setattr(campaign, field, value.value)
            elif field == "budget_type" and value is not None:
                setattr(campaign, field, value.value)
            else:
                setattr(campaign, field, value)

        campaign.updated_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(campaign)

        return campaign

    async def delete(
        self,
        campaign_id: int,
        user_id: int,
    ) -> bool:
        """Delete a campaign (soft delete - marks as deleted).

        Per Requirements 10.5: Mark as deleted and preserve history.

        Args:
            campaign_id: Campaign ID
            user_id: Owner user ID

        Returns:
            True if deleted successfully

        Raises:
            CampaignNotFoundError: If campaign not found or not owned by user
        """
        campaign = await self.get_by_id(campaign_id, user_id)

        if not campaign:
            raise CampaignNotFoundError(campaign_id)

        # Soft delete - mark as deleted to preserve history
        campaign.status = CampaignStatus.DELETED.value
        campaign.updated_at = datetime.utcnow()

        await self.db.flush()
        return True


    async def get_campaign_status(
        self,
        campaign_id: int,
        user_id: int,
    ) -> str | None:
        """Get real-time campaign status.

        Per Requirements 10.4: Return real-time status.

        Args:
            campaign_id: Campaign ID
            user_id: Owner user ID

        Returns:
            Campaign status string or None if not found
        """
        campaign = await self.get_by_id(campaign_id, user_id)
        if not campaign:
            return None
        return campaign.status

    async def get_by_ad_account(
        self,
        ad_account_id: int,
        user_id: int,
        include_deleted: bool = False,
    ) -> list[Campaign]:
        """Get all campaigns for an ad account.

        Args:
            ad_account_id: Ad account ID
            user_id: Owner user ID
            include_deleted: Whether to include deleted campaigns

        Returns:
            List of Campaign instances
        """
        query = select(Campaign).where(
            Campaign.ad_account_id == ad_account_id,
            Campaign.user_id == user_id,
        )

        if not include_deleted:
            query = query.where(Campaign.status != CampaignStatus.DELETED.value)

        query = query.order_by(Campaign.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_platform_campaign_id(
        self,
        campaign_id: int,
        platform_campaign_id: str,
    ) -> bool:
        """Update the platform campaign ID after syncing to ad platform.

        Args:
            campaign_id: Campaign ID
            platform_campaign_id: ID from the ad platform

        Returns:
            True if updated successfully
        """
        result = await self.db.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()

        if not campaign:
            return False

        campaign.platform_campaign_id = platform_campaign_id
        campaign.updated_at = datetime.utcnow()

        await self.db.flush()
        return True


    async def sync_to_platform(
        self,
        campaign_id: int,
        user_id: int,
    ) -> "PlatformSyncResult":
        """Sync a campaign to its ad platform.

        Per Requirements 10.3: Sync to ad platform on create/update.

        Args:
            campaign_id: Campaign ID
            user_id: Owner user ID

        Returns:
            PlatformSyncResult with sync status

        Raises:
            CampaignNotFoundError: If campaign not found
        """
        from app.services.platform_sync import PlatformSyncResult, PlatformSyncService

        campaign = await self.get_by_id(campaign_id, user_id)
        if not campaign:
            raise CampaignNotFoundError(campaign_id)

        ad_account = await self._get_ad_account(campaign.ad_account_id, user_id)
        if not ad_account:
            return PlatformSyncResult(
                success=False,
                error_message="Ad account not found",
                error_code="AD_ACCOUNT_NOT_FOUND",
            )

        sync_service = PlatformSyncService(self.db)

        if campaign.platform_campaign_id:
            # Campaign already synced, do an update
            result = await sync_service.sync_campaign_update(
                campaign=campaign,
                ad_account=ad_account,
                update_fields={
                    "name": campaign.name,
                    "status": campaign.status,
                    "budget": campaign.budget,
                    "budget_type": campaign.budget_type,
                    "targeting": campaign.targeting,
                },
            )
        else:
            # New campaign, create on platform
            result = await sync_service.sync_campaign_create(
                campaign=campaign,
                ad_account=ad_account,
            )

        return result
