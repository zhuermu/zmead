"""
Meta (Facebook/Instagram) Platform Adapter

Implements the PlatformAdapter interface for Meta Marketing API.
"""

import logging
from typing import Any, Dict, Optional
from .base import PlatformAdapter

logger = logging.getLogger(__name__)


class MetaAdapter(PlatformAdapter):
    """
    Meta Marketing API adapter.
    
    Handles all interactions with Meta's advertising platform including
    Facebook and Instagram ads.
    """
    
    def __init__(self):
        self.api_version = "v18.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
    
    async def create_campaign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a campaign on Meta platform.
        
        Uses Facebook Business SDK to create campaigns.
        """
        try:
            # Import here to avoid dependency issues if SDK not installed
            from facebook_business.adobjects.campaign import Campaign
            from facebook_business.adobjects.adaccount import AdAccount
            
            ad_account_id = params.get("ad_account_id")
            if not ad_account_id:
                return self._format_error(
                    "1001",
                    "INVALID_REQUEST",
                    "Missing required parameter: ad_account_id"
                )
            
            # Create ad account object
            ad_account = AdAccount(f"act_{ad_account_id}")
            
            # Create campaign
            campaign = Campaign(parent_id=ad_account.get_id_assured())
            campaign[Campaign.Field.name] = params["name"]
            campaign[Campaign.Field.objective] = self._map_objective(
                params["objective"]
            )
            campaign[Campaign.Field.status] = Campaign.Status.active
            campaign[Campaign.Field.daily_budget] = int(
                params["daily_budget"] * 100  # Convert to cents
            )
            
            # Create on platform
            campaign.remote_create()
            
            logger.info(
                f"Created Meta campaign: {campaign[Campaign.Field.id]}",
                extra={
                    "campaign_id": campaign[Campaign.Field.id],
                    "name": params["name"],
                    "objective": params["objective"]
                }
            )
            
            return {
                "id": campaign[Campaign.Field.id],
                "name": params["name"],
                "status": "active"
            }
            
        except ImportError:
            return self._format_error(
                "5001",
                "DEPENDENCY_ERROR",
                "Facebook Business SDK not installed"
            )
        except Exception as e:
            logger.error(f"Failed to create Meta campaign: {e}")
            return self._format_error(
                "4000",
                "PLATFORM_API_ERROR",
                f"Meta API error: {str(e)}"
            )
    
    async def create_adset(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an adset on Meta platform.
        """
        try:
            from facebook_business.adobjects.adset import AdSet
            
            campaign_id = params.get("campaign_id")
            if not campaign_id:
                return self._format_error(
                    "1001",
                    "INVALID_REQUEST",
                    "Missing required parameter: campaign_id"
                )
            
            # Create adset
            adset = AdSet(parent_id=campaign_id)
            adset[AdSet.Field.name] = params["name"]
            adset[AdSet.Field.daily_budget] = int(
                params["daily_budget"] * 100  # Convert to cents
            )
            adset[AdSet.Field.billing_event] = AdSet.BillingEvent.impressions
            adset[AdSet.Field.optimization_goal] = self._map_optimization_goal(
                params.get("optimization_goal", "value")
            )
            adset[AdSet.Field.bid_strategy] = self._map_bid_strategy(
                params.get("bid_strategy", "lowest_cost_without_cap")
            )
            adset[AdSet.Field.targeting] = self._format_targeting(
                params["targeting"]
            )
            adset[AdSet.Field.status] = AdSet.Status.active
            
            # Create on platform
            adset.remote_create()
            
            logger.info(
                f"Created Meta adset: {adset[AdSet.Field.id]}",
                extra={
                    "adset_id": adset[AdSet.Field.id],
                    "campaign_id": campaign_id,
                    "name": params["name"]
                }
            )
            
            return {
                "id": adset[AdSet.Field.id],
                "name": params["name"],
                "daily_budget": params["daily_budget"],
                "status": "active"
            }
            
        except ImportError:
            return self._format_error(
                "5001",
                "DEPENDENCY_ERROR",
                "Facebook Business SDK not installed"
            )
        except Exception as e:
            logger.error(f"Failed to create Meta adset: {e}")
            return self._format_error(
                "4000",
                "PLATFORM_API_ERROR",
                f"Meta API error: {str(e)}"
            )
    
    async def create_ad(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an ad on Meta platform.
        """
        try:
            from facebook_business.adobjects.ad import Ad
            from facebook_business.adobjects.adcreative import AdCreative
            
            adset_id = params.get("adset_id")
            if not adset_id:
                return self._format_error(
                    "1001",
                    "INVALID_REQUEST",
                    "Missing required parameter: adset_id"
                )
            
            # For now, return a mock response since creative creation
            # requires additional setup (page_id, image upload, etc.)
            # This will be fully implemented when integrated with creative module
            
            logger.info(
                f"Created Meta ad (mock): {params['name']}",
                extra={
                    "adset_id": adset_id,
                    "creative_id": params.get("creative_id"),
                    "name": params["name"]
                }
            )
            
            return {
                "id": f"mock_ad_{adset_id}_{params.get('creative_id')}",
                "creative_id": params.get("creative_id"),
                "status": "active"
            }
            
        except ImportError:
            return self._format_error(
                "5001",
                "DEPENDENCY_ERROR",
                "Facebook Business SDK not installed"
            )
        except Exception as e:
            logger.error(f"Failed to create Meta ad: {e}")
            return self._format_error(
                "4000",
                "PLATFORM_API_ERROR",
                f"Meta API error: {str(e)}"
            )
    
    async def update_budget(
        self,
        adset_id: str,
        budget: float
    ) -> Dict[str, Any]:
        """
        Update adset budget on Meta platform.
        """
        try:
            from facebook_business.adobjects.adset import AdSet
            
            adset = AdSet(adset_id)
            adset[AdSet.Field.daily_budget] = int(budget * 100)
            adset.remote_update()
            
            logger.info(
                f"Updated Meta adset budget: {adset_id}",
                extra={"adset_id": adset_id, "new_budget": budget}
            )
            
            return {
                "status": "success",
                "new_budget": budget
            }
            
        except ImportError:
            return self._format_error(
                "5001",
                "DEPENDENCY_ERROR",
                "Facebook Business SDK not installed"
            )
        except Exception as e:
            logger.error(f"Failed to update Meta adset budget: {e}")
            return self._format_error(
                "4000",
                "PLATFORM_API_ERROR",
                f"Meta API error: {str(e)}"
            )
    
    async def pause_adset(self, adset_id: str) -> Dict[str, Any]:
        """
        Pause an adset on Meta platform.
        """
        try:
            from facebook_business.adobjects.adset import AdSet
            
            adset = AdSet(adset_id)
            adset[AdSet.Field.status] = AdSet.Status.paused
            adset.remote_update()
            
            logger.info(
                f"Paused Meta adset: {adset_id}",
                extra={"adset_id": adset_id}
            )
            
            return {
                "status": "success",
                "new_status": "paused"
            }
            
        except ImportError:
            return self._format_error(
                "5001",
                "DEPENDENCY_ERROR",
                "Facebook Business SDK not installed"
            )
        except Exception as e:
            logger.error(f"Failed to pause Meta adset: {e}")
            return self._format_error(
                "4000",
                "PLATFORM_API_ERROR",
                f"Meta API error: {str(e)}"
            )
    
    async def resume_adset(self, adset_id: str) -> Dict[str, Any]:
        """
        Resume a paused adset on Meta platform.
        """
        try:
            from facebook_business.adobjects.adset import AdSet
            
            adset = AdSet(adset_id)
            adset[AdSet.Field.status] = AdSet.Status.active
            adset.remote_update()
            
            logger.info(
                f"Resumed Meta adset: {adset_id}",
                extra={"adset_id": adset_id}
            )
            
            return {
                "status": "success",
                "new_status": "active"
            }
            
        except ImportError:
            return self._format_error(
                "5001",
                "DEPENDENCY_ERROR",
                "Facebook Business SDK not installed"
            )
        except Exception as e:
            logger.error(f"Failed to resume Meta adset: {e}")
            return self._format_error(
                "4000",
                "PLATFORM_API_ERROR",
                f"Meta API error: {str(e)}"
            )
    
    async def get_campaign_status(
        self,
        campaign_id: str
    ) -> Dict[str, Any]:
        """
        Get campaign status from Meta platform.
        """
        try:
            from facebook_business.adobjects.campaign import Campaign
            
            campaign = Campaign(campaign_id)
            campaign_data = campaign.api_get(fields=[
                Campaign.Field.name,
                Campaign.Field.status,
                Campaign.Field.daily_budget,
            ])
            
            logger.info(
                f"Retrieved Meta campaign status: {campaign_id}",
                extra={"campaign_id": campaign_id}
            )
            
            return {
                "campaign_id": campaign_id,
                "name": campaign_data.get(Campaign.Field.name),
                "status": campaign_data.get(Campaign.Field.status),
                "daily_budget": float(
                    campaign_data.get(Campaign.Field.daily_budget, 0)
                ) / 100,  # Convert from cents
                "metrics": {}  # Will be populated from insights API
            }
            
        except ImportError:
            return self._format_error(
                "5001",
                "DEPENDENCY_ERROR",
                "Facebook Business SDK not installed"
            )
        except Exception as e:
            logger.error(f"Failed to get Meta campaign status: {e}")
            return self._format_error(
                "4000",
                "PLATFORM_API_ERROR",
                f"Meta API error: {str(e)}"
            )
    
    async def delete_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """
        Delete a campaign on Meta platform.
        """
        try:
            from facebook_business.adobjects.campaign import Campaign
            
            campaign = Campaign(campaign_id)
            campaign[Campaign.Field.status] = Campaign.Status.deleted
            campaign.remote_update()
            
            logger.info(
                f"Deleted Meta campaign: {campaign_id}",
                extra={"campaign_id": campaign_id}
            )
            
            return {
                "status": "success",
                "message": f"Campaign {campaign_id} deleted successfully"
            }
            
        except ImportError:
            return self._format_error(
                "5001",
                "DEPENDENCY_ERROR",
                "Facebook Business SDK not installed"
            )
        except Exception as e:
            logger.error(f"Failed to delete Meta campaign: {e}")
            return self._format_error(
                "4000",
                "PLATFORM_API_ERROR",
                f"Meta API error: {str(e)}"
            )
    
    def _map_objective(self, objective: str) -> str:
        """Map generic objective to Meta-specific objective."""
        objective_map = {
            "sales": "OUTCOME_SALES",
            "traffic": "OUTCOME_TRAFFIC",
            "awareness": "OUTCOME_AWARENESS",
            "leads": "OUTCOME_LEADS",
            "engagement": "OUTCOME_ENGAGEMENT"
        }
        return objective_map.get(objective.lower(), "OUTCOME_SALES")
    
    def _map_optimization_goal(self, goal: str) -> str:
        """Map generic optimization goal to Meta-specific goal."""
        from facebook_business.adobjects.adset import AdSet
        
        goal_map = {
            "value": AdSet.OptimizationGoal.value,
            "conversions": AdSet.OptimizationGoal.offsite_conversions,
            "clicks": AdSet.OptimizationGoal.link_clicks,
            "impressions": AdSet.OptimizationGoal.impressions
        }
        return goal_map.get(goal.lower(), AdSet.OptimizationGoal.value)
    
    def _map_bid_strategy(self, strategy: str) -> str:
        """Map generic bid strategy to Meta-specific strategy."""
        from facebook_business.adobjects.adset import AdSet
        
        strategy_map = {
            "lowest_cost": AdSet.BidStrategy.lowest_cost_without_cap,
            "lowest_cost_without_cap": AdSet.BidStrategy.lowest_cost_without_cap,
            "cost_cap": AdSet.BidStrategy.cost_cap
        }
        return strategy_map.get(
            strategy.lower(),
            AdSet.BidStrategy.lowest_cost_without_cap
        )
    
    def _format_targeting(self, targeting: Dict[str, Any]) -> Dict[str, Any]:
        """Format targeting parameters for Meta API."""
        formatted = {
            "geo_locations": {
                "countries": targeting.get("countries", ["US"])
            },
            "age_min": targeting.get("age_min", 18),
            "age_max": targeting.get("age_max", 65),
        }
        
        # Add targeting optimization if specified
        if targeting.get("targeting_optimization") == "none":
            formatted["targeting_optimization"] = "none"
        
        return formatted
