"""Google Ads Campaign Management Service."""

import logging
from datetime import datetime, UTC
from typing import Any

from google.ads.googleads.client import GoogleAdsClient as GoogleAdsAPIClient
from google.oauth2.credentials import Credentials

from app.core.config import settings

logger = logging.getLogger(__name__)

# Budget protection: Maximum daily budget in USD
MAX_DAILY_BUDGET_USD = 1000


class GoogleAdsCampaignService:
    """Service for managing Google Ads campaigns, ad groups, and ads."""

    def __init__(self):
        """Initialize Google Ads campaign service."""
        self.developer_token = settings.google_ads_developer_token
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret

    def _get_client(
        self, customer_id: str, access_token: str, refresh_token: str
    ) -> GoogleAdsAPIClient:
        """
        Create Google Ads API client for a specific customer.

        Args:
            customer_id: Google Ads customer ID
            access_token: OAuth access token
            refresh_token: OAuth refresh token

        Returns:
            Initialized Google Ads API client
        """
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=["https://www.googleapis.com/auth/adwords"],
        )

        return GoogleAdsAPIClient(
            credentials=credentials,
            developer_token=self.developer_token,
        )

    async def create_campaign(
        self,
        customer_id: str,
        access_token: str,
        refresh_token: str,
        campaign_name: str,
        daily_budget_micros: int,
        campaign_type: str = "SEARCH",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new Google Ads campaign.

        Args:
            customer_id: Google Ads customer ID
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            campaign_name: Name of the campaign
            daily_budget_micros: Daily budget in micros (e.g., 10000000 = $10)
            campaign_type: Campaign type (SEARCH, DISPLAY, VIDEO, etc.)
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            Dictionary containing campaign details

        Raises:
            ValueError: If budget exceeds maximum allowed or other validation errors
        """
        try:
            # Budget protection
            daily_budget_usd = daily_budget_micros / 1_000_000
            if daily_budget_usd > MAX_DAILY_BUDGET_USD:
                raise ValueError(
                    f"Daily budget ${daily_budget_usd:.2f} exceeds maximum allowed ${MAX_DAILY_BUDGET_USD}"
                )

            client = self._get_client(customer_id, access_token, refresh_token)

            # Create campaign budget
            campaign_budget_service = client.get_service("CampaignBudgetService")
            campaign_budget_operation = client.get_type("CampaignBudgetOperation")
            campaign_budget = campaign_budget_operation.create

            campaign_budget.name = f"{campaign_name} Budget"
            campaign_budget.amount_micros = daily_budget_micros
            campaign_budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD

            budget_response = campaign_budget_service.mutate_campaign_budgets(
                customer_id=customer_id, operations=[campaign_budget_operation]
            )
            budget_resource_name = budget_response.results[0].resource_name

            # Create campaign
            campaign_service = client.get_service("CampaignService")
            campaign_operation = client.get_type("CampaignOperation")
            campaign = campaign_operation.create

            campaign.name = campaign_name
            campaign.advertising_channel_type = getattr(
                client.enums.AdvertisingChannelTypeEnum, campaign_type
            )
            campaign.status = client.enums.CampaignStatusEnum.PAUSED  # Start paused for safety
            campaign.campaign_budget = budget_resource_name
            campaign.bidding_strategy_type = (
                client.enums.BiddingStrategyTypeEnum.MAXIMIZE_CONVERSIONS
            )

            # Set campaign dates if provided
            if start_date:
                campaign.start_date = start_date.replace("-", "")  # Format: YYYYMMDD
            if end_date:
                campaign.end_date = end_date.replace("-", "")

            campaign_response = campaign_service.mutate_campaigns(
                customer_id=customer_id, operations=[campaign_operation]
            )

            campaign_resource_name = campaign_response.results[0].resource_name
            campaign_id = campaign_resource_name.split("/")[-1]

            logger.info(
                f"Created campaign {campaign_id} for customer {customer_id}: {campaign_name}"
            )

            return {
                "campaign_id": campaign_id,
                "campaign_resource_name": campaign_resource_name,
                "campaign_name": campaign_name,
                "daily_budget_micros": daily_budget_micros,
                "status": "PAUSED",
                "type": campaign_type,
            }

        except Exception as e:
            logger.error(f"Failed to create campaign: {str(e)}")
            raise ValueError(f"Campaign creation failed: {str(e)}")

    async def create_ad_group(
        self,
        customer_id: str,
        access_token: str,
        refresh_token: str,
        campaign_id: str,
        ad_group_name: str,
        cpc_bid_micros: int | None = None,
    ) -> dict[str, Any]:
        """
        Create a new ad group within a campaign.

        Args:
            customer_id: Google Ads customer ID
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            campaign_id: Parent campaign ID
            ad_group_name: Name of the ad group
            cpc_bid_micros: CPC bid in micros (optional)

        Returns:
            Dictionary containing ad group details
        """
        try:
            client = self._get_client(customer_id, access_token, refresh_token)

            ad_group_service = client.get_service("AdGroupService")
            ad_group_operation = client.get_type("AdGroupOperation")
            ad_group = ad_group_operation.create

            ad_group.name = ad_group_name
            ad_group.campaign = client.get_service("CampaignService").campaign_path(
                customer_id, campaign_id
            )
            ad_group.status = client.enums.AdGroupStatusEnum.PAUSED
            ad_group.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD

            if cpc_bid_micros:
                ad_group.cpc_bid_micros = cpc_bid_micros

            ad_group_response = ad_group_service.mutate_ad_groups(
                customer_id=customer_id, operations=[ad_group_operation]
            )

            ad_group_resource_name = ad_group_response.results[0].resource_name
            ad_group_id = ad_group_resource_name.split("/")[-1]

            logger.info(
                f"Created ad group {ad_group_id} in campaign {campaign_id}: {ad_group_name}"
            )

            return {
                "ad_group_id": ad_group_id,
                "ad_group_resource_name": ad_group_resource_name,
                "ad_group_name": ad_group_name,
                "campaign_id": campaign_id,
                "status": "PAUSED",
            }

        except Exception as e:
            logger.error(f"Failed to create ad group: {str(e)}")
            raise ValueError(f"Ad group creation failed: {str(e)}")

    async def create_responsive_search_ad(
        self,
        customer_id: str,
        access_token: str,
        refresh_token: str,
        ad_group_id: str,
        headlines: list[str],
        descriptions: list[str],
        final_url: str,
    ) -> dict[str, Any]:
        """
        Create a responsive search ad.

        Args:
            customer_id: Google Ads customer ID
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            ad_group_id: Parent ad group ID
            headlines: List of headlines (3-15 required, max 30 chars each)
            descriptions: List of descriptions (2-4 required, max 90 chars each)
            final_url: Landing page URL

        Returns:
            Dictionary containing ad details

        Raises:
            ValueError: If validation fails (headline/description count, length, etc.)
        """
        try:
            # Validation
            if len(headlines) < 3 or len(headlines) > 15:
                raise ValueError("Responsive search ads require 3-15 headlines")
            if len(descriptions) < 2 or len(descriptions) > 4:
                raise ValueError("Responsive search ads require 2-4 descriptions")

            for i, headline in enumerate(headlines):
                if len(headline) > 30:
                    raise ValueError(f"Headline {i+1} exceeds 30 characters: {headline}")

            for i, description in enumerate(descriptions):
                if len(description) > 90:
                    raise ValueError(
                        f"Description {i+1} exceeds 90 characters: {description}"
                    )

            client = self._get_client(customer_id, access_token, refresh_token)

            ad_group_ad_service = client.get_service("AdGroupAdService")
            ad_group_ad_operation = client.get_type("AdGroupAdOperation")
            ad_group_ad = ad_group_ad_operation.create

            ad_group_ad.ad_group = client.get_service("AdGroupService").ad_group_path(
                customer_id, ad_group_id
            )
            ad_group_ad.status = client.enums.AdGroupAdStatusEnum.PAUSED

            # Create responsive search ad
            ad_group_ad.ad.final_urls.append(final_url)
            responsive_search_ad = ad_group_ad.ad.responsive_search_ad

            # Add headlines
            for headline in headlines:
                headline_asset = client.get_type("AdTextAsset")
                headline_asset.text = headline
                responsive_search_ad.headlines.append(headline_asset)

            # Add descriptions
            for description in descriptions:
                description_asset = client.get_type("AdTextAsset")
                description_asset.text = description
                responsive_search_ad.descriptions.append(description_asset)

            ad_response = ad_group_ad_service.mutate_ad_group_ads(
                customer_id=customer_id, operations=[ad_group_ad_operation]
            )

            ad_resource_name = ad_response.results[0].resource_name
            ad_id = ad_resource_name.split("/")[-1]

            logger.info(f"Created responsive search ad {ad_id} in ad group {ad_group_id}")

            return {
                "ad_id": ad_id,
                "ad_resource_name": ad_resource_name,
                "ad_group_id": ad_group_id,
                "headlines_count": len(headlines),
                "descriptions_count": len(descriptions),
                "final_url": final_url,
                "status": "PAUSED",
            }

        except Exception as e:
            logger.error(f"Failed to create ad: {str(e)}")
            raise ValueError(f"Ad creation failed: {str(e)}")

    async def update_campaign_status(
        self,
        customer_id: str,
        access_token: str,
        refresh_token: str,
        campaign_id: str,
        status: str,
    ) -> dict[str, Any]:
        """
        Update campaign status (ENABLED, PAUSED, REMOVED).

        Args:
            customer_id: Google Ads customer ID
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            campaign_id: Campaign ID to update
            status: New status (ENABLED, PAUSED, REMOVED)

        Returns:
            Dictionary with update confirmation
        """
        try:
            client = self._get_client(customer_id, access_token, refresh_token)

            campaign_service = client.get_service("CampaignService")
            campaign_operation = client.get_type("CampaignOperation")

            campaign_resource_name = campaign_service.campaign_path(customer_id, campaign_id)
            campaign = campaign_operation.update
            campaign.resource_name = campaign_resource_name
            campaign.status = getattr(client.enums.CampaignStatusEnum, status)

            field_mask = client.get_type("FieldMask")
            field_mask.paths.append("status")
            campaign_operation.update_mask.CopyFrom(field_mask)

            campaign_service.mutate_campaigns(
                customer_id=customer_id, operations=[campaign_operation]
            )

            logger.info(f"Updated campaign {campaign_id} status to {status}")

            return {
                "campaign_id": campaign_id,
                "status": status,
                "updated_at": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to update campaign status: {str(e)}")
            raise ValueError(f"Campaign status update failed: {str(e)}")


# Singleton instance
_google_ads_campaign_service: GoogleAdsCampaignService | None = None


def get_google_ads_campaign_service() -> GoogleAdsCampaignService:
    """Get or create Google Ads campaign service instance."""
    global _google_ads_campaign_service
    if _google_ads_campaign_service is None:
        _google_ads_campaign_service = GoogleAdsCampaignService()
    return _google_ads_campaign_service
