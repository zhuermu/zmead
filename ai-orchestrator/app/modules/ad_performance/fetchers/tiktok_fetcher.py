"""
TikTok Ads API data fetcher.

Integrates with TikTok Ads API to fetch ad performance data from TikTok platform.

Requirements: 1.1, 1.2, 1.3
"""

from typing import Any

import structlog

from .base import BaseFetcher, RetryableError

logger = structlog.get_logger(__name__)


class TikTokFetcher(BaseFetcher):
    """TikTok Ads API 数据抓取器
    
    Fetches advertising data from TikTok Ads API.
    Handles authentication, API calls, and data transformation to standard format.
    
    Requirements: 1.1, 1.2, 1.3
    """

    def __init__(
        self,
        access_token: str,
        app_id: str | None = None,
        secret: str | None = None,
        max_retries: int = 3,
        backoff_factor: int = 2,
    ):
        """
        Initialize TikTok fetcher with access credentials.
        
        Args:
            access_token: TikTok Ads API access token
            app_id: TikTok app ID (optional, for OAuth)
            secret: TikTok app secret (optional, for OAuth)
            max_retries: Maximum number of retry attempts (default: 3)
            backoff_factor: Exponential backoff multiplier (default: 2)
        """
        super().__init__(max_retries, backoff_factor)
        self.access_token = access_token
        self.app_id = app_id
        self.secret = secret
        
        # Note: TikTok Ads API typically uses REST API calls rather than a Python SDK
        # We'll implement direct API calls using httpx or requests
        self.api_base_url = "https://business-api.tiktok.com/open_api/v1.3"
        self.api_initialized = True
        
        logger.info(
            "tiktok_fetcher_initialized",
            has_token=bool(access_token),
            has_app_id=bool(app_id),
        )

    async def fetch_insights(
        self,
        date_range: dict,
        levels: list[str],
        metrics: list[str],
        account_id: str | None = None,
    ) -> dict:
        """
        抓取 TikTok 广告数据
        
        Fetches ad performance data from TikTok Ads API for specified date range,
        levels (campaign/adset/ad), and metrics.
        
        Args:
            date_range: {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}
            levels: ["campaign", "adset", "ad"]
            metrics: ["spend", "impressions", "clicks", "conversions", "revenue"]
            account_id: TikTok advertiser ID
            
        Returns:
            {
                "campaigns": [...],
                "adsets": [...],
                "ads": [...]
            }
            
        Requirements: 1.1, 1.2, 1.3
        """
        if not self.api_initialized:
            raise RuntimeError("TikTok API not initialized")

        if not account_id:
            raise ValueError("account_id is required for TikTok fetcher")

        logger.info(
            "tiktok_fetch_insights_start",
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
            "tiktok_fetch_insights_complete",
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
            import httpx
        except ImportError as e:
            logger.error("httpx_import_error", error=str(e))
            raise ImportError("httpx is required. Install with: pip install httpx") from e

        results = {"campaigns": [], "adsets": [], "ads": []}

        # Map our standard level names to TikTok API dimension names
        level_mapping = {
            "campaign": "CAMPAIGN_ID",
            "adset": "ADGROUP_ID",  # TikTok calls adsets "adgroups"
            "ad": "AD_ID",
        }

        # Map our standard metric names to TikTok API field names
        tiktok_metrics = self._map_metrics_to_tiktok_fields(metrics)

        try:
            async with httpx.AsyncClient() as client:
                for level in levels:
                    try:
                        dimension = level_mapping.get(level)
                        if not dimension:
                            logger.warning("tiktok_unsupported_level", level=level)
                            continue

                        # Build request parameters
                        params = {
                            "advertiser_id": account_id,
                            "start_date": date_range["start_date"],
                            "end_date": date_range["end_date"],
                            "dimensions": [dimension],
                            "metrics": tiktok_metrics,
                            "page_size": 1000,  # Max page size
                        }

                        # Make API request
                        response = await client.get(
                            f"{self.api_base_url}/reports/integrated/get/",
                            headers={
                                "Access-Token": self.access_token,
                                "Content-Type": "application/json",
                            },
                            params=params,
                            timeout=30.0,
                        )

                        # Check response status
                        if response.status_code != 200:
                            error_msg = f"TikTok API returned status {response.status_code}"
                            logger.error(
                                "tiktok_api_error",
                                status_code=response.status_code,
                                response=response.text,
                            )
                            raise RetryableError(error_msg)

                        # Parse response
                        data = response.json()
                        
                        if data.get("code") != 0:
                            error_msg = f"TikTok API error: {data.get('message', 'Unknown error')}"
                            logger.error(
                                "tiktok_api_response_error",
                                code=data.get("code"),
                                message=data.get("message"),
                            )
                            
                            # Check if retryable
                            if self._is_retryable_tiktok_code(data.get("code")):
                                raise RetryableError(error_msg)
                            raise RuntimeError(error_msg)

                        # Transform insights to standard format
                        insights = data.get("data", {}).get("list", [])
                        level_key = f"{level}s"
                        results[level_key] = [
                            self._transform_insight(insight, level) for insight in insights
                        ]

                        logger.info(
                            "tiktok_level_fetched",
                            level=level,
                            count=len(results[level_key]),
                        )

                    except httpx.HTTPError as e:
                        logger.error(
                            "tiktok_http_error",
                            level=level,
                            error=str(e),
                            error_type=type(e).__name__,
                        )
                        raise RetryableError(f"TikTok API HTTP error for level {level}: {e}") from e

                    except Exception as e:
                        logger.error(
                            "tiktok_level_fetch_error",
                            level=level,
                            error=str(e),
                            error_type=type(e).__name__,
                        )
                        if self._is_retryable_error(e):
                            raise RetryableError(f"TikTok API error for level {level}: {e}") from e
                        raise

            return results

        except Exception as e:
            logger.error(
                "tiktok_fetch_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            if self._is_retryable_error(e):
                raise RetryableError(f"TikTok API error: {e}") from e
            raise

    def _map_metrics_to_tiktok_fields(self, metrics: list[str]) -> list[str]:
        """
        Map standard metric names to TikTok API field names.
        
        Args:
            metrics: Standard metric names
            
        Returns:
            TikTok API field names
        """
        # Mapping from our standard names to TikTok API names
        metric_mapping = {
            "spend": "spend",
            "impressions": "impressions",
            "clicks": "clicks",
            "conversions": "conversion",  # TikTok uses "conversion"
            "revenue": "total_purchase_value",  # TikTok uses total_purchase_value
        }

        tiktok_metrics = []
        for metric in metrics:
            if metric in metric_mapping:
                tiktok_metric = metric_mapping[metric]
                if tiktok_metric not in tiktok_metrics:
                    tiktok_metrics.append(tiktok_metric)

        return tiktok_metrics

    def _transform_insight(self, insight: dict, level: str) -> dict:
        """
        Transform TikTok API response to standard format.
        
        Args:
            insight: Raw insight data from TikTok API
            level: Data level (campaign, adset, ad)
            
        Returns:
            Standardized insight data
        """
        # TikTok uses different field names for IDs
        id_mapping = {
            "campaign": "campaign_id",
            "adset": "adgroup_id",
            "ad": "ad_id",
        }

        name_mapping = {
            "campaign": "campaign_name",
            "adset": "adgroup_name",
            "ad": "ad_name",
        }

        # Extract entity ID and name
        entity_id = insight.get("dimensions", {}).get(id_mapping.get(level, ""), "")
        entity_name = insight.get("dimensions", {}).get(name_mapping.get(level, ""), "")

        # Extract metrics from the metrics object
        metrics_data = insight.get("metrics", {})
        
        spend = float(metrics_data.get("spend", 0))
        impressions = int(metrics_data.get("impressions", 0))
        clicks = int(metrics_data.get("clicks", 0))
        conversions = int(metrics_data.get("conversion", 0))
        revenue = float(metrics_data.get("total_purchase_value", 0))

        return {
            "entity_id": entity_id,
            "entity_name": entity_name,
            "entity_type": level,
            "spend": spend,
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "revenue": revenue,
            "platform": "tiktok",
        }

    async def get_account_info(self, account_id: str) -> dict:
        """
        获取 TikTok 广告账户信息
        
        Args:
            account_id: TikTok advertiser ID
            
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
            raise RuntimeError("TikTok API not initialized")

        logger.info("tiktok_get_account_info", account_id=account_id)

        # Use retry mechanism
        result = await self.retry_with_backoff(
            self._get_account_info_internal,
            account_id=account_id,
        )

        return result

    async def _get_account_info_internal(self, account_id: str) -> dict:
        """Internal method to get account info (wrapped by retry mechanism)"""
        try:
            import httpx
        except ImportError as e:
            raise ImportError("httpx is required. Install with: pip install httpx") from e

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base_url}/advertiser/info/",
                    headers={
                        "Access-Token": self.access_token,
                        "Content-Type": "application/json",
                    },
                    params={"advertiser_ids": [account_id]},
                    timeout=30.0,
                )

                if response.status_code != 200:
                    error_msg = f"TikTok API returned status {response.status_code}"
                    logger.error(
                        "tiktok_account_api_error",
                        status_code=response.status_code,
                        response=response.text,
                    )
                    raise RetryableError(error_msg)

                data = response.json()
                
                if data.get("code") != 0:
                    error_msg = f"TikTok API error: {data.get('message', 'Unknown error')}"
                    logger.error(
                        "tiktok_account_response_error",
                        code=data.get("code"),
                        message=data.get("message"),
                    )
                    if self._is_retryable_tiktok_code(data.get("code")):
                        raise RetryableError(error_msg)
                    raise RuntimeError(error_msg)

                # Extract account info
                accounts = data.get("data", {}).get("list", [])
                if not accounts:
                    raise ValueError(f"Account {account_id} not found")

                account_data = accounts[0]

                return {
                    "account_id": account_id,
                    "account_name": account_data.get("name", ""),
                    "currency": account_data.get("currency", "USD"),
                    "timezone": account_data.get("timezone", "UTC"),
                    "status": account_data.get("status", ""),
                }

        except httpx.HTTPError as e:
            logger.error(
                "tiktok_account_http_error",
                account_id=account_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise RetryableError(f"TikTok API HTTP error: {e}") from e

        except Exception as e:
            logger.error(
                "tiktok_account_info_error",
                account_id=account_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            if self._is_retryable_error(e):
                raise RetryableError(f"TikTok API error getting account info: {e}") from e
            raise

    def _is_retryable_tiktok_code(self, code: int | None) -> bool:
        """
        Determine if a TikTok API error code is retryable.
        
        Args:
            code: TikTok API error code
            
        Returns:
            True if error should trigger retry, False otherwise
        """
        if code is None:
            return False

        # TikTok retryable error codes
        retryable_codes = [
            40002,  # Rate limit exceeded
            40003,  # Server error
            50000,  # Internal server error
            50001,  # Service temporarily unavailable
        ]

        return code in retryable_codes

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

        # Check specific error types
        retryable_types = [
            "ConnectionError",
            "Timeout",
            "TimeoutError",
            "HTTPError",
        ]

        if error_type in retryable_types:
            return True

        return False
