"""
Meta Marketing API data fetcher.

Integrates with facebook-business SDK to fetch ad performance data from Meta platforms
(Facebook, Instagram).

Requirements: 1.1, 1.2, 1.3
"""

from typing import Any

import structlog

from .base import BaseFetcher, RetryableError

logger = structlog.get_logger(__name__)


class MetaFetcher(BaseFetcher):
    """Meta Marketing API 数据抓取器
    
    Fetches advertising data from Meta Marketing API (Facebook/Instagram).
    Handles authentication, API calls, and data transformation to standard format.
    
    Requirements: 1.1, 1.2, 1.3
    """

    def __init__(
        self,
        access_token: str,
        max_retries: int = 3,
        backoff_factor: int = 2,
    ):
        """
        Initialize Meta fetcher with access token.
        
        Args:
            access_token: Meta Marketing API access token
            max_retries: Maximum number of retry attempts (default: 3)
            backoff_factor: Exponential backoff multiplier (default: 2)
        """
        super().__init__(max_retries, backoff_factor)
        self.access_token = access_token
        
        # Initialize Facebook API
        try:
            from facebook_business.api import FacebookAdsApi
            from facebook_business.adobjects.adaccount import AdAccount

            FacebookAdsApi.init(access_token=access_token)
            self.AdAccount = AdAccount
            self.api_initialized = True
            
            logger.info("meta_fetcher_initialized", has_token=bool(access_token))
            
        except ImportError as e:
            logger.error(
                "meta_sdk_import_error",
                error=str(e),
                message="facebook-business SDK not installed",
            )
            self.api_initialized = False
            raise ImportError(
                "facebook-business SDK is required. Install with: pip install facebook-business"
            ) from e

    async def fetch_insights(
        self,
        date_range: dict,
        levels: list[str],
        metrics: list[str],
        account_id: str | None = None,
    ) -> dict:
        """
        抓取 Meta 广告数据
        
        Fetches ad performance data from Meta Marketing API for specified date range,
        levels (campaign/adset/ad), and metrics.
        
        Args:
            date_range: {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}
            levels: ["campaign", "adset", "ad"]
            metrics: ["spend", "impressions", "clicks", "conversions", "revenue"]
            account_id: Meta ad account ID (without "act_" prefix)
            
        Returns:
            {
                "campaigns": [...],
                "adsets": [...],
                "ads": [...]
            }
            
        Requirements: 1.1, 1.2, 1.3
        """
        if not self.api_initialized:
            raise RuntimeError("Meta API not initialized")

        if not account_id:
            raise ValueError("account_id is required for Meta fetcher")

        logger.info(
            "meta_fetch_insights_start",
            account_id=account_id,
            date_range=date_range,
            levels=levels,
            metrics=metrics,
        )

        # Use retry mechanism for API calls
        result = await self.retry_with_backoff(
            self._fetch_insights_internal,
            account_id=account_id,
            date_range=date_range,
            levels=levels,
            metrics=metrics,
        )

        logger.info(
            "meta_fetch_insights_complete",
            account_id=account_id,
            campaigns_count=len(result.get("campaigns", [])),
            adsets_count=len(result.get("adsets", [])),
            ads_count=len(result.get("ads", [])),
        )

        return result

    async def _fetch_insights_internal(
        self,
        account_id: str,
        date_range: dict,
        levels: list[str],
        metrics: list[str],
    ) -> dict:
        """Internal method to fetch insights (wrapped by retry mechanism)"""
        try:
            account = self.AdAccount(f"act_{account_id}")
            results = {"campaigns": [], "adsets": [], "ads": []}

            # Map our standard metric names to Meta API field names
            meta_fields = self._map_metrics_to_meta_fields(metrics)

            for level in levels:
                try:
                    # Fetch insights for this level
                    insights = account.get_insights(
                        fields=meta_fields,
                        params={
                            "time_range": {
                                "since": date_range["start_date"],
                                "until": date_range["end_date"],
                            },
                            "level": level,
                        },
                    )

                    # Transform each insight to standard format
                    level_key = f"{level}s"
                    results[level_key] = [
                        self._transform_insight(insight, level) for insight in insights
                    ]

                    logger.info(
                        "meta_level_fetched",
                        level=level,
                        count=len(results[level_key]),
                    )

                except Exception as e:
                    logger.error(
                        "meta_level_fetch_error",
                        level=level,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    # Check if this is a retryable error
                    if self._is_retryable_error(e):
                        raise RetryableError(f"Meta API error for level {level}: {e}") from e
                    raise

            return results

        except Exception as e:
            logger.error(
                "meta_fetch_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            # Check if this is a retryable error
            if self._is_retryable_error(e):
                raise RetryableError(f"Meta API error: {e}") from e
            raise

    def _map_metrics_to_meta_fields(self, metrics: list[str]) -> list[str]:
        """
        Map standard metric names to Meta API field names.
        
        Args:
            metrics: Standard metric names
            
        Returns:
            Meta API field names
        """
        # Mapping from our standard names to Meta API names
        metric_mapping = {
            "spend": "spend",
            "impressions": "impressions",
            "clicks": "clicks",
            "conversions": "actions",  # Meta uses "actions" for conversions
            "revenue": "purchase_roas",  # Meta uses purchase_roas for revenue tracking
        }

        # Always include ID and name fields
        meta_fields = ["campaign_id", "campaign_name", "adset_id", "adset_name", "ad_id", "ad_name"]

        # Add requested metrics
        for metric in metrics:
            if metric in metric_mapping:
                meta_field = metric_mapping[metric]
                if meta_field not in meta_fields:
                    meta_fields.append(meta_field)

        return meta_fields

    def _transform_insight(self, insight: dict, level: str) -> dict:
        """
        Transform Meta API response to standard format.
        
        Args:
            insight: Raw insight data from Meta API
            level: Data level (campaign, adset, ad)
            
        Returns:
            Standardized insight data
        """
        # Extract entity ID and name based on level
        entity_id = insight.get(f"{level}_id", "")
        entity_name = insight.get(f"{level}_name", "")

        # Extract metrics with safe defaults
        spend = float(insight.get("spend", 0))
        impressions = int(insight.get("impressions", 0))
        clicks = int(insight.get("clicks", 0))

        # Handle conversions (Meta uses "actions" array)
        conversions = 0
        if "actions" in insight:
            for action in insight["actions"]:
                if action.get("action_type") in ["purchase", "offsite_conversion.fb_pixel_purchase"]:
                    conversions += int(action.get("value", 0))

        # Handle revenue (Meta uses purchase_roas or action_values)
        revenue = 0.0
        if "purchase_roas" in insight:
            # purchase_roas is an array with value
            for roas_data in insight["purchase_roas"]:
                revenue += float(roas_data.get("value", 0)) * spend
        elif "action_values" in insight:
            for action_value in insight["action_values"]:
                if action_value.get("action_type") in ["purchase", "offsite_conversion.fb_pixel_purchase"]:
                    revenue += float(action_value.get("value", 0))

        return {
            "entity_id": entity_id,
            "entity_name": entity_name,
            "entity_type": level,
            "spend": spend,
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "revenue": revenue,
            "platform": "meta",
        }

    async def get_account_info(self, account_id: str) -> dict:
        """
        获取 Meta 广告账户信息
        
        Args:
            account_id: Meta ad account ID (without "act_" prefix)
            
        Returns:
            {
                "account_id": str,
                "account_name": str,
                "currency": str,
                "timezone": str
            }
            
        Requirements: 1.1
        """
        if not self.api_initialized:
            raise RuntimeError("Meta API not initialized")

        logger.info("meta_get_account_info", account_id=account_id)

        # Use retry mechanism
        result = await self.retry_with_backoff(
            self._get_account_info_internal,
            account_id=account_id,
        )

        return result

    async def _get_account_info_internal(self, account_id: str) -> dict:
        """Internal method to get account info (wrapped by retry mechanism)"""
        try:
            account = self.AdAccount(f"act_{account_id}")
            account_data = account.api_get(
                fields=["name", "currency", "timezone_name", "account_status"]
            )

            return {
                "account_id": account_id,
                "account_name": account_data.get("name", ""),
                "currency": account_data.get("currency", "USD"),
                "timezone": account_data.get("timezone_name", "UTC"),
                "status": account_data.get("account_status", ""),
            }

        except Exception as e:
            logger.error(
                "meta_account_info_error",
                account_id=account_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            if self._is_retryable_error(e):
                raise RetryableError(f"Meta API error getting account info: {e}") from e
            raise

    def _is_retryable_error(self, error: Exception) -> bool:
        """
        Determine if an error is retryable.
        
        Args:
            error: Exception to check
            
        Returns:
            True if error should trigger retry, False otherwise
        """
        error_str = str(error).lower()
        error_type = type(error).__name__

        # Retryable error patterns
        retryable_patterns = [
            "timeout",
            "connection",
            "rate limit",
            "temporarily unavailable",
            "service unavailable",
            "internal server error",
        ]

        # Check error message
        for pattern in retryable_patterns:
            if pattern in error_str:
                return True

        # Check specific error types from facebook-business SDK
        retryable_types = [
            "FacebookRequestError",  # May include rate limits
            "ConnectionError",
            "Timeout",
        ]

        if error_type in retryable_types:
            return True

        return False
