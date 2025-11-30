"""
Google Ads API data fetcher (stub implementation for MVP).

This is a stub implementation that returns empty data. Full implementation
will be added in a future release.

Requirements: 1.1
"""

import structlog

from .base import BaseFetcher

logger = structlog.get_logger(__name__)


class GoogleFetcher(BaseFetcher):
    """Google Ads API 数据抓取器 (Stub Implementation)
    
    This is a stub implementation for MVP. It returns empty data structures
    to maintain API compatibility while Google Ads integration is pending.
    
    TODO: Implement full Google Ads API integration
    - Integrate google-ads SDK
    - Implement OAuth2 authentication
    - Implement fetch_insights() for Google Ads API
    - Transform API response to standard format
    - Handle Google-specific errors
    
    Requirements: 1.1
    """

    def __init__(
        self,
        access_token: str | None = None,
        developer_token: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        refresh_token: str | None = None,
        max_retries: int = 3,
        backoff_factor: int = 2,
    ):
        """
        Initialize Google fetcher (stub).
        
        Args:
            access_token: Google Ads API access token (not used in stub)
            developer_token: Google Ads developer token (not used in stub)
            client_id: OAuth2 client ID (not used in stub)
            client_secret: OAuth2 client secret (not used in stub)
            refresh_token: OAuth2 refresh token (not used in stub)
            max_retries: Maximum number of retry attempts (default: 3)
            backoff_factor: Exponential backoff multiplier (default: 2)
        """
        super().__init__(max_retries, backoff_factor)
        self.access_token = access_token
        self.developer_token = developer_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        
        logger.warning(
            "google_fetcher_stub_initialized",
            message="Google Ads fetcher is a stub implementation - returns empty data",
        )

    async def fetch_insights(
        self,
        date_range: dict,
        levels: list[str],
        metrics: list[str],
        account_id: str | None = None,
    ) -> dict:
        """
        抓取 Google 广告数据 (Stub Implementation)
        
        This stub implementation returns empty data structures.
        
        TODO: Implement actual Google Ads API integration
        
        Args:
            date_range: {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}
            levels: ["campaign", "adset", "ad"]
            metrics: ["spend", "impressions", "clicks", "conversions", "revenue"]
            account_id: Google Ads customer ID
            
        Returns:
            {
                "campaigns": [],
                "adsets": [],
                "ads": []
            }
            
        Requirements: 1.1
        """
        logger.warning(
            "google_fetch_insights_stub",
            account_id=account_id,
            date_range=date_range,
            levels=levels,
            metrics=metrics,
            message="Returning empty data - Google Ads integration not yet implemented",
        )

        # Return empty data structures
        return {
            "campaigns": [],
            "adsets": [],
            "ads": [],
        }

    async def get_account_info(self, account_id: str) -> dict:
        """
        获取 Google 广告账户信息 (Stub Implementation)
        
        This stub implementation returns minimal account info.
        
        TODO: Implement actual Google Ads API integration
        
        Args:
            account_id: Google Ads customer ID
            
        Returns:
            {
                "account_id": str,
                "account_name": str,
                "currency": str,
                "timezone": str
            }
            
        Requirements: 1.1
        """
        logger.warning(
            "google_get_account_info_stub",
            account_id=account_id,
            message="Returning stub data - Google Ads integration not yet implemented",
        )

        # Return stub account info
        return {
            "account_id": account_id,
            "account_name": "Google Ads Account (Stub)",
            "currency": "USD",
            "timezone": "UTC",
            "status": "stub",
        }
