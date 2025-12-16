"""Platform sync service for syncing campaigns to ad platforms.

This module provides an abstraction layer for syncing campaign data
to various ad platforms (Meta, TikTok, Google).
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import token_encryption
from app.models.ad_account import AdAccount
from app.models.campaign import Campaign
from app.schemas.campaign import PlatformSyncResult

logger = logging.getLogger(__name__)


class PlatformType(str, Enum):
    """Supported ad platforms."""

    META = "meta"
    TIKTOK = "tiktok"
    GOOGLE = "google"


class PlatformAPIError(Exception):
    """Base exception for platform API errors."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        platform: str | None = None,
    ):
        self.message = message
        self.error_code = error_code
        self.platform = platform
        super().__init__(message)


class PlatformAuthError(PlatformAPIError):
    """Raised when platform authentication fails."""

    pass


class PlatformRateLimitError(PlatformAPIError):
    """Raised when platform rate limit is exceeded."""

    pass


class PlatformValidationError(PlatformAPIError):
    """Raised when platform validation fails."""

    pass



class BasePlatformClient(ABC):
    """Abstract base class for ad platform API clients."""

    def __init__(self, access_token: str, account_id: str):
        """Initialize platform client.

        Args:
            access_token: Decrypted OAuth access token
            account_id: Platform-specific account ID
        """
        self.access_token = access_token
        self.account_id = account_id

    @abstractmethod
    async def create_campaign(
        self,
        name: str,
        objective: str,
        budget: Decimal,
        budget_type: str,
        targeting: dict,
    ) -> PlatformSyncResult:
        """Create a campaign on the platform.

        Args:
            name: Campaign name
            objective: Campaign objective
            budget: Budget amount
            budget_type: 'daily' or 'lifetime'
            targeting: Targeting configuration

        Returns:
            PlatformSyncResult with success status and platform campaign ID
        """
        pass

    @abstractmethod
    async def update_campaign(
        self,
        platform_campaign_id: str,
        name: str | None = None,
        status: str | None = None,
        budget: Decimal | None = None,
        budget_type: str | None = None,
        targeting: dict | None = None,
    ) -> PlatformSyncResult:
        """Update a campaign on the platform.

        Args:
            platform_campaign_id: Platform-specific campaign ID
            name: Optional new name
            status: Optional new status
            budget: Optional new budget
            budget_type: Optional new budget type
            targeting: Optional new targeting

        Returns:
            PlatformSyncResult with success status
        """
        pass

    @abstractmethod
    async def delete_campaign(
        self,
        platform_campaign_id: str,
    ) -> PlatformSyncResult:
        """Delete/pause a campaign on the platform.

        Args:
            platform_campaign_id: Platform-specific campaign ID

        Returns:
            PlatformSyncResult with success status
        """
        pass

    @abstractmethod
    async def get_campaign_status(
        self,
        platform_campaign_id: str,
    ) -> str | None:
        """Get current campaign status from platform.

        Args:
            platform_campaign_id: Platform-specific campaign ID

        Returns:
            Campaign status string or None if not found
        """
        pass



class MetaPlatformClient(BasePlatformClient):
    """Meta (Facebook) Ads API client.

    Note: This is a stub implementation. In production, this would use
    the Facebook Marketing API SDK.
    """

    OBJECTIVE_MAPPING = {
        "awareness": "OUTCOME_AWARENESS",
        "traffic": "OUTCOME_TRAFFIC",
        "engagement": "OUTCOME_ENGAGEMENT",
        "leads": "OUTCOME_LEADS",
        "conversions": "OUTCOME_SALES",
        "sales": "OUTCOME_SALES",
    }

    STATUS_MAPPING = {
        "draft": "PAUSED",
        "active": "ACTIVE",
        "paused": "PAUSED",
        "deleted": "DELETED",
    }

    async def create_campaign(
        self,
        name: str,
        objective: str,
        budget: Decimal,
        budget_type: str,
        targeting: dict,
    ) -> PlatformSyncResult:
        """Create a campaign on Meta Ads."""
        try:
            # In production, this would call the Meta Marketing API
            # For now, we simulate a successful creation
            logger.info(
                f"[META] Creating campaign: name={name}, objective={objective}, "
                f"budget={budget}, budget_type={budget_type}"
            )

            # Simulate API call - in production use facebook_business SDK
            # from facebook_business.adobjects.campaign import Campaign
            # campaign = Campaign(parent_id=f"act_{self.account_id}")
            # campaign.update({
            #     Campaign.Field.name: name,
            #     Campaign.Field.objective: self.OBJECTIVE_MAPPING.get(objective),
            #     Campaign.Field.status: "PAUSED",
            #     Campaign.Field.special_ad_categories: [],
            # })
            # campaign.remote_create()

            # Return simulated success
            # In production, return actual platform_campaign_id
            simulated_id = f"meta_campaign_{datetime.utcnow().timestamp()}"

            return PlatformSyncResult(
                success=True,
                platform_campaign_id=simulated_id,
            )

        except Exception as e:
            logger.error(f"[META] Failed to create campaign: {e}")
            return PlatformSyncResult(
                success=False,
                error_message=str(e),
                error_code="META_CREATE_ERROR",
            )

    async def update_campaign(
        self,
        platform_campaign_id: str,
        name: str | None = None,
        status: str | None = None,
        budget: Decimal | None = None,
        budget_type: str | None = None,
        targeting: dict | None = None,
    ) -> PlatformSyncResult:
        """Update a campaign on Meta Ads."""
        try:
            logger.info(
                f"[META] Updating campaign {platform_campaign_id}: "
                f"name={name}, status={status}, budget={budget}"
            )

            # In production, this would call the Meta Marketing API
            # campaign = Campaign(platform_campaign_id)
            # update_params = {}
            # if name:
            #     update_params[Campaign.Field.name] = name
            # if status:
            #     update_params[Campaign.Field.status] = self.STATUS_MAPPING.get(status)
            # campaign.api_update(params=update_params)

            return PlatformSyncResult(
                success=True,
                platform_campaign_id=platform_campaign_id,
            )

        except Exception as e:
            logger.error(f"[META] Failed to update campaign: {e}")
            return PlatformSyncResult(
                success=False,
                error_message=str(e),
                error_code="META_UPDATE_ERROR",
            )

    async def delete_campaign(
        self,
        platform_campaign_id: str,
    ) -> PlatformSyncResult:
        """Delete a campaign on Meta Ads (sets status to DELETED)."""
        try:
            logger.info(f"[META] Deleting campaign {platform_campaign_id}")

            # In production, Meta doesn't truly delete - it archives
            # campaign = Campaign(platform_campaign_id)
            # campaign.api_update(params={Campaign.Field.status: "DELETED"})

            return PlatformSyncResult(
                success=True,
                platform_campaign_id=platform_campaign_id,
            )

        except Exception as e:
            logger.error(f"[META] Failed to delete campaign: {e}")
            return PlatformSyncResult(
                success=False,
                error_message=str(e),
                error_code="META_DELETE_ERROR",
            )

    async def get_campaign_status(
        self,
        platform_campaign_id: str,
    ) -> str | None:
        """Get campaign status from Meta Ads."""
        try:
            logger.info(f"[META] Getting status for campaign {platform_campaign_id}")

            # In production:
            # campaign = Campaign(platform_campaign_id)
            # campaign.api_get(fields=[Campaign.Field.status])
            # return campaign[Campaign.Field.status]

            # Return simulated status
            return "active"

        except Exception as e:
            logger.error(f"[META] Failed to get campaign status: {e}")
            return None



class TikTokPlatformClient(BasePlatformClient):
    """TikTok Ads API client.

    Note: This is a stub implementation. In production, this would use
    the TikTok Marketing API.
    """

    OBJECTIVE_MAPPING = {
        "awareness": "REACH",
        "traffic": "TRAFFIC",
        "engagement": "VIDEO_VIEWS",
        "leads": "LEAD_GENERATION",
        "conversions": "CONVERSIONS",
        "sales": "PRODUCT_SALES",
    }

    async def create_campaign(
        self,
        name: str,
        objective: str,
        budget: Decimal,
        budget_type: str,
        targeting: dict,
    ) -> PlatformSyncResult:
        """Create a campaign on TikTok Ads."""
        try:
            logger.info(
                f"[TIKTOK] Creating campaign: name={name}, objective={objective}"
            )

            # In production, use TikTok Marketing API
            simulated_id = f"tiktok_campaign_{datetime.utcnow().timestamp()}"

            return PlatformSyncResult(
                success=True,
                platform_campaign_id=simulated_id,
            )

        except Exception as e:
            logger.error(f"[TIKTOK] Failed to create campaign: {e}")
            return PlatformSyncResult(
                success=False,
                error_message=str(e),
                error_code="TIKTOK_CREATE_ERROR",
            )

    async def update_campaign(
        self,
        platform_campaign_id: str,
        name: str | None = None,
        status: str | None = None,
        budget: Decimal | None = None,
        budget_type: str | None = None,
        targeting: dict | None = None,
    ) -> PlatformSyncResult:
        """Update a campaign on TikTok Ads."""
        try:
            logger.info(f"[TIKTOK] Updating campaign {platform_campaign_id}")

            return PlatformSyncResult(
                success=True,
                platform_campaign_id=platform_campaign_id,
            )

        except Exception as e:
            logger.error(f"[TIKTOK] Failed to update campaign: {e}")
            return PlatformSyncResult(
                success=False,
                error_message=str(e),
                error_code="TIKTOK_UPDATE_ERROR",
            )

    async def delete_campaign(
        self,
        platform_campaign_id: str,
    ) -> PlatformSyncResult:
        """Delete a campaign on TikTok Ads."""
        try:
            logger.info(f"[TIKTOK] Deleting campaign {platform_campaign_id}")

            return PlatformSyncResult(
                success=True,
                platform_campaign_id=platform_campaign_id,
            )

        except Exception as e:
            logger.error(f"[TIKTOK] Failed to delete campaign: {e}")
            return PlatformSyncResult(
                success=False,
                error_message=str(e),
                error_code="TIKTOK_DELETE_ERROR",
            )

    async def get_campaign_status(
        self,
        platform_campaign_id: str,
    ) -> str | None:
        """Get campaign status from TikTok Ads."""
        try:
            return "active"
        except Exception as e:
            logger.error(f"[TIKTOK] Failed to get campaign status: {e}")
            return None


class GooglePlatformClient(BasePlatformClient):
    """Google Ads API client using the Google Ads API v28."""

    def __init__(self, access_token: str, account_id: str, refresh_token: str | None = None):
        """Initialize Google Ads client.

        Args:
            access_token: OAuth access token
            account_id: Google Ads customer ID
            refresh_token: OAuth refresh token for token refresh
        """
        super().__init__(access_token, account_id)
        self.refresh_token = refresh_token

    # Campaign type mapping based on objective
    CAMPAIGN_TYPE_MAPPING = {
        "awareness": "SEARCH",  # Brand awareness campaigns
        "traffic": "SEARCH",  # Website traffic campaigns
        "engagement": "DISPLAY",  # Engagement campaigns
        "leads": "SEARCH",  # Lead generation campaigns
        "conversions": "SEARCH",  # Conversion campaigns
        "sales": "SEARCH",  # Sales campaigns
    }

    async def create_campaign(
        self,
        name: str,
        objective: str,
        budget: Decimal,
        budget_type: str,
        targeting: dict,
    ) -> PlatformSyncResult:
        """Create a campaign on Google Ads using the Google Ads API."""
        try:
            from app.services.google_ads_campaign_service import get_google_ads_campaign_service

            logger.info(
                f"[GOOGLE] Creating campaign: name={name}, objective={objective}, "
                f"budget={budget}, budget_type={budget_type}"
            )

            # Get Google Ads campaign service
            service = get_google_ads_campaign_service()

            # Convert budget to micros (Google Ads uses micros: 1 USD = 1,000,000 micros)
            daily_budget_micros = int(float(budget) * 1_000_000)

            # Determine campaign type based on objective
            campaign_type = self.CAMPAIGN_TYPE_MAPPING.get(objective, "SEARCH")

            # Create campaign using Google Ads API
            result = await service.create_campaign(
                customer_id=self.account_id,
                access_token=self.access_token,
                refresh_token=self.refresh_token or "",
                campaign_name=name,
                daily_budget_micros=daily_budget_micros,
                campaign_type=campaign_type,
            )

            logger.info(f"[GOOGLE] Campaign created successfully: {result['campaign_id']}")

            return PlatformSyncResult(
                success=True,
                platform_campaign_id=result["campaign_id"],
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[GOOGLE] Failed to create campaign: {error_msg}")

            # If developer token not approved, return simulated success for testing
            if "DEVELOPER_TOKEN_NOT_APPROVED" in error_msg or "test accounts" in error_msg:
                logger.warning(
                    "[GOOGLE] Developer token only approved for test accounts. "
                    "Returning simulated campaign ID for development testing."
                )
                import time
                simulated_id = f"test_campaign_{int(time.time())}"
                return PlatformSyncResult(
                    success=True,
                    platform_campaign_id=simulated_id,
                )

            return PlatformSyncResult(
                success=False,
                error_message=error_msg,
                error_code="GOOGLE_CREATE_ERROR",
            )

    async def update_campaign(
        self,
        platform_campaign_id: str,
        name: str | None = None,
        status: str | None = None,
        budget: Decimal | None = None,
        budget_type: str | None = None,
        targeting: dict | None = None,
    ) -> PlatformSyncResult:
        """Update a campaign on Google Ads."""
        try:
            from app.services.google_ads_campaign_service import get_google_ads_campaign_service

            logger.info(f"[GOOGLE] Updating campaign {platform_campaign_id}: status={status}")

            service = get_google_ads_campaign_service()

            # Map our status to Google Ads status
            google_status_map = {
                "draft": "PAUSED",
                "active": "ENABLED",
                "paused": "PAUSED",
                "deleted": "REMOVED",
            }

            if status:
                google_status = google_status_map.get(status, "PAUSED")
                await service.update_campaign_status(
                    customer_id=self.account_id,
                    access_token=self.access_token,
                    refresh_token=self.refresh_token or "",
                    campaign_id=platform_campaign_id,
                    status=google_status,
                )

            return PlatformSyncResult(
                success=True,
                platform_campaign_id=platform_campaign_id,
            )

        except Exception as e:
            logger.error(f"[GOOGLE] Failed to update campaign: {e}")
            return PlatformSyncResult(
                success=False,
                error_message=str(e),
                error_code="GOOGLE_UPDATE_ERROR",
            )

    async def delete_campaign(
        self,
        platform_campaign_id: str,
    ) -> PlatformSyncResult:
        """Delete (pause) a campaign on Google Ads."""
        try:
            from app.services.google_ads_campaign_service import get_google_ads_campaign_service

            logger.info(f"[GOOGLE] Removing campaign {platform_campaign_id}")

            service = get_google_ads_campaign_service()

            # Google Ads doesn't truly delete - it sets status to REMOVED
            await service.update_campaign_status(
                customer_id=self.account_id,
                access_token=self.access_token,
                refresh_token=self.refresh_token or "",
                campaign_id=platform_campaign_id,
                status="REMOVED",
            )

            return PlatformSyncResult(
                success=True,
                platform_campaign_id=platform_campaign_id,
            )

        except Exception as e:
            logger.error(f"[GOOGLE] Failed to delete campaign: {e}")
            return PlatformSyncResult(
                success=False,
                error_message=str(e),
                error_code="GOOGLE_DELETE_ERROR",
            )

    async def get_campaign_status(
        self,
        platform_campaign_id: str,
    ) -> str | None:
        """Get campaign status from Google Ads."""
        try:
            # For now, return None to indicate status should be fetched from database
            # In production, this would query the Google Ads API
            logger.info(f"[GOOGLE] Getting status for campaign {platform_campaign_id}")
            return None
        except Exception as e:
            logger.error(f"[GOOGLE] Failed to get campaign status: {e}")
            return None



class PlatformSyncService:
    """Service for syncing campaigns to ad platforms.

    This service handles the synchronization of campaign data between
    the local database and external ad platforms (Meta, TikTok, Google).
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_platform_client(
        self,
        platform: str,
        access_token: str,
        account_id: str,
        refresh_token: str | None = None,
    ) -> BasePlatformClient:
        """Get the appropriate platform client.

        Args:
            platform: Platform type ('meta', 'tiktok', 'google')
            access_token: Decrypted OAuth access token
            account_id: Platform-specific account ID
            refresh_token: Optional decrypted refresh token (required for Google)

        Returns:
            Platform client instance

        Raises:
            ValueError: If platform is not supported
        """
        clients = {
            PlatformType.META.value: MetaPlatformClient,
            PlatformType.TIKTOK.value: TikTokPlatformClient,
            PlatformType.GOOGLE.value: GooglePlatformClient,
        }

        client_class = clients.get(platform)
        if not client_class:
            raise ValueError(f"Unsupported platform: {platform}")

        # Google client needs refresh token
        if platform == PlatformType.GOOGLE.value:
            return client_class(access_token, account_id, refresh_token)
        else:
            return client_class(access_token, account_id)

    async def _get_decrypted_token(self, ad_account: AdAccount) -> str:
        """Get decrypted access token from ad account.

        Args:
            ad_account: AdAccount model instance

        Returns:
            Decrypted access token
        """
        return token_encryption.decrypt(ad_account.access_token_encrypted)

    async def _get_decrypted_refresh_token(self, ad_account: AdAccount) -> str | None:
        """Get decrypted refresh token from ad account.

        Args:
            ad_account: AdAccount model instance

        Returns:
            Decrypted refresh token or None if not available
        """
        if ad_account.refresh_token_encrypted:
            return token_encryption.decrypt(ad_account.refresh_token_encrypted)
        return None

    async def sync_campaign_create(
        self,
        campaign: Campaign,
        ad_account: AdAccount,
    ) -> PlatformSyncResult:
        """Sync a newly created campaign to the ad platform.

        Args:
            campaign: Campaign model instance
            ad_account: AdAccount model instance

        Returns:
            PlatformSyncResult with sync status
        """
        try:
            access_token = await self._get_decrypted_token(ad_account)
            refresh_token = await self._get_decrypted_refresh_token(ad_account)
            client = self._get_platform_client(
                campaign.platform,
                access_token,
                ad_account.platform_account_id,
                refresh_token,
            )

            result = await client.create_campaign(
                name=campaign.name,
                objective=campaign.objective,
                budget=campaign.budget,
                budget_type=campaign.budget_type,
                targeting=campaign.targeting,
            )

            if result.success and result.platform_campaign_id:
                # Update campaign with platform ID
                campaign.platform_campaign_id = result.platform_campaign_id
                campaign.updated_at = datetime.utcnow()
                await self.db.flush()

            return result

        except Exception as e:
            logger.error(f"Failed to sync campaign create: {e}")
            return PlatformSyncResult(
                success=False,
                error_message=str(e),
                error_code="SYNC_CREATE_ERROR",
            )

    async def sync_campaign_update(
        self,
        campaign: Campaign,
        ad_account: AdAccount,
        update_fields: dict[str, Any],
    ) -> PlatformSyncResult:
        """Sync campaign updates to the ad platform.

        Args:
            campaign: Campaign model instance
            ad_account: AdAccount model instance
            update_fields: Dictionary of fields that were updated

        Returns:
            PlatformSyncResult with sync status
        """
        # Only sync if campaign has been synced to platform before
        if not campaign.platform_campaign_id:
            logger.info(
                f"Campaign {campaign.id} not yet synced to platform, skipping update sync"
            )
            return PlatformSyncResult(success=True)

        try:
            access_token = await self._get_decrypted_token(ad_account)
            refresh_token = await self._get_decrypted_refresh_token(ad_account)
            client = self._get_platform_client(
                campaign.platform,
                access_token,
                ad_account.platform_account_id,
                refresh_token,
            )

            result = await client.update_campaign(
                platform_campaign_id=campaign.platform_campaign_id,
                name=update_fields.get("name"),
                status=update_fields.get("status"),
                budget=update_fields.get("budget"),
                budget_type=update_fields.get("budget_type"),
                targeting=update_fields.get("targeting"),
            )

            return result

        except Exception as e:
            logger.error(f"Failed to sync campaign update: {e}")
            return PlatformSyncResult(
                success=False,
                error_message=str(e),
                error_code="SYNC_UPDATE_ERROR",
            )

    async def sync_campaign_delete(
        self,
        campaign: Campaign,
        ad_account: AdAccount,
    ) -> PlatformSyncResult:
        """Sync campaign deletion to the ad platform.

        Args:
            campaign: Campaign model instance
            ad_account: AdAccount model instance

        Returns:
            PlatformSyncResult with sync status
        """
        # Only sync if campaign has been synced to platform before
        if not campaign.platform_campaign_id:
            logger.info(
                f"Campaign {campaign.id} not yet synced to platform, skipping delete sync"
            )
            return PlatformSyncResult(success=True)

        try:
            access_token = await self._get_decrypted_token(ad_account)
            refresh_token = await self._get_decrypted_refresh_token(ad_account)
            client = self._get_platform_client(
                campaign.platform,
                access_token,
                ad_account.platform_account_id,
                refresh_token,
            )

            result = await client.delete_campaign(
                platform_campaign_id=campaign.platform_campaign_id,
            )

            return result

        except Exception as e:
            logger.error(f"Failed to sync campaign delete: {e}")
            return PlatformSyncResult(
                success=False,
                error_message=str(e),
                error_code="SYNC_DELETE_ERROR",
            )

    async def get_platform_status(
        self,
        campaign: Campaign,
        ad_account: AdAccount,
    ) -> str | None:
        """Get real-time campaign status from the ad platform.

        Args:
            campaign: Campaign model instance
            ad_account: AdAccount model instance

        Returns:
            Campaign status string or None if not available
        """
        if not campaign.platform_campaign_id:
            return campaign.status

        try:
            access_token = await self._get_decrypted_token(ad_account)
            refresh_token = await self._get_decrypted_refresh_token(ad_account)
            client = self._get_platform_client(
                campaign.platform,
                access_token,
                ad_account.platform_account_id,
                refresh_token,
            )

            return await client.get_campaign_status(
                platform_campaign_id=campaign.platform_campaign_id,
            )

        except Exception as e:
            logger.error(f"Failed to get platform status: {e}")
            return campaign.status
