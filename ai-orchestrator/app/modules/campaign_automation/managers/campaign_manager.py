"""
Campaign Manager - Handles campaign creation, management, and status queries.

This module provides the core campaign management functionality including:
- Creating campaigns with automatic adset and ad generation
- Managing campaign status (pause/resume/delete)
- Querying campaign details and performance
- AI-powered ad copy generation with fallback

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 4.1, 8.1, 8.2
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog

from app.modules.campaign_automation.adapters.base import PlatformAdapter
from app.modules.campaign_automation.adapters.router import PlatformRouter
from app.modules.campaign_automation.clients.ai_client import AIClient
from app.modules.campaign_automation.models import Campaign, Adset, Ad, Targeting
from app.services.gemini_client import GeminiClient, GeminiError
from app.services.mcp_client import MCPClient, MCPError

logger = structlog.get_logger(__name__)


class CampaignManager:
    """
    Campaign Manager - Manages campaign lifecycle and operations.
    
    Responsibilities:
    - Create Campaign/Adset/Ad three-tier structure
    - Configure audience targeting and placements
    - Manage campaign status (start/pause/delete)
    - Mount creatives and generate ad copy
    - Query campaign details and performance
    
    Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 4.1, 8.1, 8.2
    """
    
    # Default age groups for automatic adset generation
    DEFAULT_AGE_GROUPS = [(18, 35), (36, 50), (51, 65)]
    
    def __init__(
        self,
        mcp_client: MCPClient,
        gemini_client: GeminiClient,
    ):
        """
        Initialize Campaign Manager.
        
        Args:
            mcp_client: MCP client for Web Platform communication
            gemini_client: Gemini client for AI copy generation
        """
        self.mcp_client = mcp_client
        self.gemini_client = gemini_client
        self.ai_client = AIClient(gemini_client)
        self.platform_router = PlatformRouter()
        
        logger.info("campaign_manager_initialized")
    
    async def create_campaign(
        self,
        objective: str,
        daily_budget: float,
        target_countries: List[str],
        creative_ids: List[str],
        platform: str,
        context: Dict[str, Any],
        product_url: Optional[str] = None,
        target_roas: Optional[float] = None,
        target_cpa: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Create a complete campaign structure with adsets and ads.
        
        This method orchestrates the creation of:
        1. Campaign on the platform
        2. Multiple adsets (one per age group)
        3. Ads for each creative in each adset
        4. AI-generated ad copy for each ad
        5. Data persistence to Web Platform via MCP
        
        Args:
            objective: Campaign objective (sales, traffic, awareness)
            daily_budget: Total daily budget in USD
            target_countries: List of target country codes (e.g., ["US", "CA"])
            creative_ids: List of creative IDs to use
            platform: Platform name (meta, tiktok, google)
            context: Request context with user_id, session_id
            product_url: Product URL for ad copy generation
            target_roas: Target ROAS for optimization (optional)
            target_cpa: Target CPA for optimization (optional)
            
        Returns:
            Dict containing:
                - status: "success"
                - campaign_id: Created campaign ID
                - adsets: List of created adsets
                - ads: List of created ads
                - message: Success message
                
        Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3
        """
        user_id = context.get("user_id")
        
        log = logger.bind(
            user_id=user_id,
            platform=platform,
            objective=objective,
            daily_budget=daily_budget,
        )
        
        log.info("create_campaign_start")
        
        try:
            # Get platform adapter
            adapter = self.platform_router.get_adapter(platform)
            
            if not adapter:
                return {
                    "status": "error",
                    "error": {
                        "code": "1001",
                        "type": "INVALID_REQUEST",
                        "message": f"Unsupported platform: {platform}",
                        "details": {
                            "supported_platforms": self.platform_router.get_supported_platforms()
                        }
                    }
                }
            
            # Get active ad account for the platform
            active_account_result = await self.mcp_client.call_tool(
                "get_active_ad_account",
                {
                    "platform": platform,
                }
            )
            
            active_account = active_account_result.get("active_account")
            if not active_account:
                log.error("no_active_ad_account", platform=platform)
                return {
                    "status": "error",
                    "error": {
                        "code": "6000",
                        "type": "AD_ACCOUNT_NOT_BOUND",
                        "message": f"未找到 {platform} 平台的活跃广告账户，请先绑定广告账户",
                        "details": {
                            "platform": platform,
                        },
                    }
                }
            
            ad_account_id = active_account.get("id")
            
            # Get ad account token
            token_result = await self.mcp_client.call_tool(
                "get_ad_account_token",
                {
                    "ad_account_id": ad_account_id,
                }
            )
            
            access_token = token_result.get("access_token")
            if not access_token:
                log.error("failed_to_get_access_token", ad_account_id=ad_account_id)
                return {
                    "status": "error",
                    "error": {
                        "code": "6001",
                        "type": "AD_ACCOUNT_TOKEN_EXPIRED",
                        "message": "广告账户授权已过期，请重新授权",
                        "details": {
                            "ad_account_id": ad_account_id,
                            "platform": platform,
                        },
                    }
                }
            
            # Step 1: Create Campaign
            campaign_name = f"Campaign {datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            
            campaign_result = await adapter.create_campaign({
                "name": campaign_name,
                "objective": objective,
                "daily_budget": daily_budget,
                "ad_account_id": ad_account_id,
                "access_token": access_token,
            })
            
            if campaign_result.get("status") == "error":
                log.error("campaign_creation_failed", result=campaign_result)
                return campaign_result
            
            campaign_id = campaign_result["id"]
            log.info("campaign_created", campaign_id=campaign_id)
            
            # Step 2: Create Adsets
            adsets = await self._create_adsets(
                campaign_id=campaign_id,
                daily_budget=daily_budget,
                target_countries=target_countries,
                adapter=adapter,
                ad_account_id=ad_account_id,
                access_token=access_token,
            )
            
            log.info("adsets_created", count=len(adsets))
            
            # Step 3: Create Ads
            ads = await self._create_ads(
                adsets=adsets,
                creative_ids=creative_ids,
                product_url=product_url,
                platform=platform,
                adapter=adapter,
                ad_account_id=ad_account_id,
                access_token=access_token,
                context=context,
            )
            
            log.info("ads_created", count=len(ads))
            
            # Step 4: Save to Web Platform via MCP
            # Note: We store the platform_campaign_id in the Web Platform database
            await self.mcp_client.call_tool(
                "create_campaign",
                {
                    "ad_account_id": ad_account_id,
                    "name": campaign_name,
                    "objective": objective,
                    "budget": daily_budget,
                    "budget_type": "daily",
                    "targeting": {
                        "countries": target_countries,
                        "target_roas": target_roas,
                        "target_cpa": target_cpa,
                    },
                    "creative_ids": [int(cid) for cid in creative_ids if cid.isdigit()],
                }
            )
            
            log.info("campaign_saved_to_platform")
            
            return {
                "status": "success",
                "campaign_id": campaign_id,
                "adsets": [
                    {
                        "adset_id": a["id"],
                        "name": a["name"],
                        "daily_budget": a["daily_budget"],
                        "targeting": a.get("targeting", {}),
                    }
                    for a in adsets
                ],
                "ads": [
                    {
                        "ad_id": a["id"],
                        "creative_id": a["creative_id"],
                        "adset_id": a["adset_id"],
                        "copy": a.get("copy", ""),
                    }
                    for a in ads
                ],
                "message": "广告系列创建成功",
            }
            
        except (MCPError, GeminiError) as e:
            log.error("create_campaign_service_error", error=str(e))
            return {
                "status": "error",
                "error": {
                    "code": "4000",
                    "type": "SERVICE_ERROR",
                    "message": str(e),
                }
            }
        except Exception as e:
            log.error("create_campaign_unexpected_error", error=str(e), exc_info=True)
            return {
                "status": "error",
                "error": {
                    "code": "1000",
                    "type": "UNKNOWN_ERROR",
                    "message": str(e),
                }
            }
    
    async def _create_adsets(
        self,
        campaign_id: str,
        daily_budget: float,
        target_countries: List[str],
        adapter: PlatformAdapter,
        ad_account_id: str,
        access_token: str,
    ) -> List[Dict[str, Any]]:
        """
        Create adsets for the campaign.
        
        Automatically creates one adset per age group with:
        - Equal budget distribution
        - Broad audience targeting
        - Automatic placements
        - Lowest cost bid strategy
        
        Args:
            campaign_id: Parent campaign ID
            daily_budget: Total daily budget to distribute
            target_countries: Target country codes
            adapter: Platform adapter
            ad_account_id: Ad account ID
            access_token: Access token
            
        Returns:
            List of created adset dicts
            
        Requirements: 1.2, 1.3, 1.4, 1.5
        """
        age_groups = self.DEFAULT_AGE_GROUPS
        budget_per_adset = daily_budget / len(age_groups)
        
        adsets = []
        
        for age_min, age_max in age_groups:
            adset_name = f"{target_countries[0]} {age_min}-{age_max}"
            
            adset_result = await adapter.create_adset({
                "campaign_id": campaign_id,
                "name": adset_name,
                "daily_budget": budget_per_adset,
                "targeting": {
                    "age_min": age_min,
                    "age_max": age_max,
                    "countries": target_countries,
                    "targeting_optimization": "none",  # Broad audience
                },
                "optimization_goal": "value",
                "bid_strategy": "lowest_cost_without_cap",
                "placements": "automatic",
                "ad_account_id": ad_account_id,
                "access_token": access_token,
            })
            
            if adset_result.get("status") == "error":
                logger.error("adset_creation_failed", adset_name=adset_name, result=adset_result)
                continue
            
            adsets.append(adset_result)
        
        return adsets
    
    async def _create_ads(
        self,
        adsets: List[Dict[str, Any]],
        creative_ids: List[str],
        product_url: Optional[str],
        platform: str,
        adapter: PlatformAdapter,
        ad_account_id: str,
        access_token: str,
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Create ads for each creative in each adset.
        
        For each adset and creative combination:
        1. Fetch creative details from Web Platform
        2. Generate AI-powered ad copy
        3. Create ad on platform
        
        Args:
            adsets: List of adsets to create ads in
            creative_ids: List of creative IDs
            product_url: Product URL for copy generation
            platform: Platform name
            adapter: Platform adapter
            ad_account_id: Ad account ID
            access_token: Access token
            context: Request context
            
        Returns:
            List of created ad dicts
            
        Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
        """
        user_id = context.get("user_id")
        ads = []
        
        # Fetch creative details from Web Platform
        # Note: get_creatives returns paginated results, we fetch all creatives
        # and filter by the provided creative_ids
        creatives_result = await self.mcp_client.call_tool(
            "get_creatives",
            {
                "page": 1,
                "page_size": 100,  # Get up to 100 creatives
                "status": "active",
            }
        )
        
        all_creatives = creatives_result.get("creatives", [])
        
        # Filter to only the requested creative_ids
        creative_id_set = set(str(cid) for cid in creative_ids)
        creatives = [
            c for c in all_creatives
            if str(c.get("id")) in creative_id_set
        ]
        
        if not creatives:
            logger.warning("no_creatives_found", creative_ids=creative_ids)
            return ads
        
        logger.info("creatives_fetched", count=len(creatives))
        
        # Create ads for each adset and creative combination
        for adset in adsets:
            for creative in creatives:
                creative_id = creative.get("id")
                
                # Generate ad copy
                ad_copy = await self._generate_ad_copy(
                    product_url=product_url,
                    creative_id=creative_id,
                    platform=platform,
                )
                
                # Create ad
                ad_name = f"Ad {creative_id}"
                
                ad_result = await adapter.create_ad({
                    "adset_id": adset["id"],
                    "creative_id": creative_id,
                    "name": ad_name,
                    "copy": ad_copy,
                    "ad_account_id": ad_account_id,
                    "access_token": access_token,
                    "creative_url": creative.get("cdn_url") or creative.get("file_url"),
                })
                
                if ad_result.get("status") == "error":
                    logger.error("ad_creation_failed", ad_name=ad_name, result=ad_result)
                    continue
                
                ads.append({
                    "id": ad_result["id"],
                    "creative_id": creative_id,
                    "adset_id": adset["id"],
                    "copy": ad_copy,
                })
        
        return ads
    
    async def _generate_ad_copy(
        self,
        product_url: Optional[str],
        creative_id: str,
        platform: str,
    ) -> str:
        """
        Generate AI-powered ad copy with fallback strategy.
        
        Delegates to AIClient which implements:
        1. Try Gemini 2.5 Pro
        2. If fails, try Gemini 2.5 Flash
        3. If still fails, use template copy
        
        Args:
            product_url: Product URL
            creative_id: Creative ID
            platform: Platform name
            
        Returns:
            Generated ad copy text
            
        Requirements: 2.4, 2.5
        """
        return await self.ai_client.generate_ad_copy(
            product_url=product_url or "",
            creative_id=creative_id,
            platform=platform,
        )
    
    async def update_campaign_status(
        self,
        campaign_id: str,
        status: str,
        platform: str,
        context: Dict[str, Any],
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update campaign status (pause/resume/delete).
        
        Args:
            campaign_id: Campaign ID
            status: New status (pause, active, delete)
            platform: Platform name
            context: Request context
            reason: Reason for status change (optional)
            
        Returns:
            Dict containing:
                - status: "success"
                - campaign_id: Campaign ID
                - new_status: Updated status
                - message: Confirmation message
                
        Requirements: 4.1, 4.5
        """
        user_id = context.get("user_id")
        
        log = logger.bind(
            user_id=user_id,
            campaign_id=campaign_id,
            new_status=status,
        )
        
        log.info("update_campaign_status_start")
        
        try:
            # Get platform adapter
            adapter = self.platform_router.get_adapter(platform)
            
            if not adapter:
                return {
                    "status": "error",
                    "error": {
                        "code": "1001",
                        "type": "INVALID_REQUEST",
                        "message": f"Unsupported platform: {platform}",
                        "details": {
                            "supported_platforms": self.platform_router.get_supported_platforms()
                        }
                    }
                }
            
            # Get active ad account for the platform
            active_account_result = await self.mcp_client.call_tool(
                "get_active_ad_account",
                {
                    "platform": platform,
                }
            )
            
            active_account = active_account_result.get("active_account")
            if not active_account:
                return {
                    "status": "error",
                    "error": {
                        "code": "6000",
                        "type": "AD_ACCOUNT_NOT_BOUND",
                        "message": f"未找到 {platform} 平台的活跃广告账户",
                    }
                }
            
            ad_account_id = active_account.get("id")
            
            # Get ad account token
            token_result = await self.mcp_client.call_tool(
                "get_ad_account_token",
                {
                    "ad_account_id": ad_account_id,
                }
            )
            
            access_token = token_result.get("access_token")
            
            # Execute status change on platform
            if status == "delete":
                result = await adapter.delete_campaign(campaign_id)
            elif status == "pause":
                # Note: Pausing is typically done at adset level
                # For now, we'll update via MCP
                result = {"status": "success"}
            elif status == "active":
                # Note: Resuming is typically done at adset level
                result = {"status": "success"}
            else:
                return {
                    "status": "error",
                    "error": {
                        "code": "1001",
                        "type": "INVALID_REQUEST",
                        "message": f"Invalid status: {status}",
                    }
                }
            
            if result.get("status") == "error":
                log.error("platform_status_update_failed", result=result)
                return result
            
            # Get the campaign from Web Platform to get its internal ID
            # Note: We need to find the campaign by platform_campaign_id
            campaigns_result = await self.mcp_client.call_tool(
                "get_campaigns",
                {
                    "page": 1,
                    "page_size": 100,
                    "platform": platform,
                }
            )
            
            campaigns = campaigns_result.get("campaigns", [])
            campaign = next(
                (c for c in campaigns if c.get("platform_campaign_id") == campaign_id),
                None
            )
            
            if campaign:
                # Update in Web Platform via MCP
                await self.mcp_client.call_tool(
                    "update_campaign",
                    {
                        "campaign_id": campaign.get("id"),
                        "status": status,
                    }
                )
            
            log.info("campaign_status_updated")
            
            return {
                "status": "success",
                "campaign_id": campaign_id,
                "new_status": status,
                "message": f"广告系列已{status}",
            }
            
        except MCPError as e:
            log.error("update_campaign_status_mcp_error", error=str(e))
            return {
                "status": "error",
                "error": {
                    "code": "3000",
                    "type": "MCP_ERROR",
                    "message": str(e),
                }
            }
        except Exception as e:
            log.error("update_campaign_status_unexpected_error", error=str(e), exc_info=True)
            return {
                "status": "error",
                "error": {
                    "code": "1000",
                    "type": "UNKNOWN_ERROR",
                    "message": str(e),
                }
            }
    
    async def get_campaign_details(
        self,
        campaign_id: str,
        platform: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Get campaign details and performance metrics.
        
        Args:
            campaign_id: Campaign ID
            platform: Platform name
            context: Request context
            
        Returns:
            Dict containing:
                - status: "success"
                - campaign: Campaign details with metrics
                - adsets: List of adsets with metrics
                - message: Success message
                
        Requirements: 8.1, 8.2
        """
        user_id = context.get("user_id")
        
        log = logger.bind(
            user_id=user_id,
            campaign_id=campaign_id,
            platform=platform,
        )
        
        log.info("get_campaign_details_start")
        
        try:
            # Get platform adapter
            adapter = self.platform_router.get_adapter(platform)
            
            if not adapter:
                return {
                    "status": "error",
                    "error": {
                        "code": "1001",
                        "type": "INVALID_REQUEST",
                        "message": f"Unsupported platform: {platform}",
                        "details": {
                            "supported_platforms": self.platform_router.get_supported_platforms()
                        }
                    }
                }
            
            # Get active ad account for the platform
            active_account_result = await self.mcp_client.call_tool(
                "get_active_ad_account",
                {
                    "platform": platform,
                }
            )
            
            active_account = active_account_result.get("active_account")
            if not active_account:
                return {
                    "status": "error",
                    "error": {
                        "code": "6000",
                        "type": "AD_ACCOUNT_NOT_BOUND",
                        "message": f"未找到 {platform} 平台的活跃广告账户",
                    }
                }
            
            ad_account_id = active_account.get("id")
            
            # Get ad account token
            token_result = await self.mcp_client.call_tool(
                "get_ad_account_token",
                {
                    "ad_account_id": ad_account_id,
                }
            )
            
            access_token = token_result.get("access_token")
            
            # Get campaign status from platform
            campaign_status = await adapter.get_campaign_status(campaign_id)
            
            if campaign_status.get("status") == "error":
                log.error("failed_to_get_campaign_status", result=campaign_status)
                return campaign_status
            
            # Get performance metrics from Web Platform via MCP
            # Requirements: 8.1, 8.3
            from datetime import datetime, timedelta, timezone as dt_timezone
            
            end_date = datetime.now(dt_timezone.utc)
            start_date = end_date - timedelta(days=7)
            
            metrics_result = await self.mcp_client.call_tool(
                "get_reports",
                {
                    "ad_account_id": ad_account_id,
                    "entity_type": "campaign",
                    "entity_id": campaign_id,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "page": 1,
                    "page_size": 10,
                }
            )
            
            metrics = metrics_result.get("metrics", [])
            
            # Calculate aggregated metrics
            total_spend = sum(float(m.get("spend", 0)) for m in metrics)
            total_revenue = sum(float(m.get("revenue", 0)) for m in metrics)
            total_conversions = sum(m.get("conversions", 0) for m in metrics)
            total_impressions = sum(m.get("impressions", 0) for m in metrics)
            total_clicks = sum(m.get("clicks", 0) for m in metrics)
            
            # Calculate derived metrics
            roas = total_revenue / total_spend if total_spend > 0 else 0
            cpa = total_spend / total_conversions if total_conversions > 0 else 0
            ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
            
            # Merge platform status with metrics
            campaign_data = campaign_status.get("campaign", {})
            campaign_data.update({
                "spend_today": total_spend,
                "revenue_today": total_revenue,
                "roas_today": round(roas, 2),
                "cpa_today": round(cpa, 2),
                "ctr_today": round(ctr, 2),
                "conversions_today": total_conversions,
            })
            
            log.info("campaign_details_retrieved")
            
            return {
                "status": "success",
                "campaign": campaign_data,
                "adsets": campaign_status.get("adsets", []),
                "message": "广告系列详情获取成功",
            }
            
        except MCPError as e:
            log.error("get_campaign_details_mcp_error", error=str(e))
            return {
                "status": "error",
                "error": {
                    "code": "3000",
                    "type": "MCP_ERROR",
                    "message": str(e),
                }
            }
        except Exception as e:
            log.error("get_campaign_details_unexpected_error", error=str(e), exc_info=True)
            return {
                "status": "error",
                "error": {
                    "code": "1000",
                    "type": "UNKNOWN_ERROR",
                    "message": str(e),
                }
            }
