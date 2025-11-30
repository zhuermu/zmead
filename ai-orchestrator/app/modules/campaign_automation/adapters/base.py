"""
Platform Adapter Base Class

Defines the abstract interface for all platform adapters.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


class PlatformAdapter(ABC):
    """
    Abstract base class for platform adapters.
    
    All platform-specific implementations (Meta, TikTok, Google) must
    inherit from this class and implement all abstract methods.
    """
    
    @abstractmethod
    async def create_campaign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a campaign on the platform.
        
        Args:
            params: Campaign parameters including:
                - name: Campaign name
                - objective: Campaign objective (sales, traffic, awareness)
                - daily_budget: Daily budget in USD
                - ad_account_id: Platform-specific ad account ID
                
        Returns:
            Dict containing:
                - id: Platform campaign ID
                - name: Campaign name
                - status: Campaign status
        """
        pass
    
    @abstractmethod
    async def create_adset(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an adset (ad group) on the platform.
        
        Args:
            params: Adset parameters including:
                - campaign_id: Parent campaign ID
                - name: Adset name
                - daily_budget: Daily budget in USD
                - targeting: Targeting configuration
                - optimization_goal: Optimization goal
                - bid_strategy: Bid strategy
                
        Returns:
            Dict containing:
                - id: Platform adset ID
                - name: Adset name
                - daily_budget: Daily budget
                - status: Adset status
        """
        pass
    
    @abstractmethod
    async def create_ad(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an ad on the platform.
        
        Args:
            params: Ad parameters including:
                - adset_id: Parent adset ID
                - creative_id: Creative ID
                - name: Ad name
                - copy: Ad copy text
                
        Returns:
            Dict containing:
                - id: Platform ad ID
                - creative_id: Creative ID
                - status: Ad status
        """
        pass
    
    @abstractmethod
    async def update_budget(
        self,
        adset_id: str,
        budget: float
    ) -> Dict[str, Any]:
        """
        Update adset budget.
        
        Args:
            adset_id: Adset ID
            budget: New daily budget in USD
            
        Returns:
            Dict containing:
                - status: Operation status
                - new_budget: Updated budget
        """
        pass
    
    @abstractmethod
    async def pause_adset(self, adset_id: str) -> Dict[str, Any]:
        """
        Pause an adset.
        
        Args:
            adset_id: Adset ID
            
        Returns:
            Dict containing:
                - status: Operation status
                - new_status: Updated status (paused)
        """
        pass
    
    @abstractmethod
    async def resume_adset(self, adset_id: str) -> Dict[str, Any]:
        """
        Resume a paused adset.
        
        Args:
            adset_id: Adset ID
            
        Returns:
            Dict containing:
                - status: Operation status
                - new_status: Updated status (active)
        """
        pass
    
    @abstractmethod
    async def get_campaign_status(
        self,
        campaign_id: str
    ) -> Dict[str, Any]:
        """
        Get campaign status and metrics.
        
        Args:
            campaign_id: Campaign ID
            
        Returns:
            Dict containing:
                - campaign_id: Campaign ID
                - name: Campaign name
                - status: Campaign status
                - daily_budget: Daily budget
                - spend_today: Today's spend
                - metrics: Performance metrics
        """
        pass
    
    @abstractmethod
    async def delete_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """
        Delete a campaign.
        
        Args:
            campaign_id: Campaign ID
            
        Returns:
            Dict containing:
                - status: Operation status
                - message: Confirmation message
        """
        pass
    
    def _format_error(
        self,
        error_code: str,
        error_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format error response in standard format.
        
        Args:
            error_code: Error code
            error_type: Error type
            message: Error message
            details: Additional error details
            
        Returns:
            Standardized error dict
        """
        return {
            "status": "error",
            "error": {
                "code": error_code,
                "type": error_type,
                "message": message,
                "details": details or {},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
