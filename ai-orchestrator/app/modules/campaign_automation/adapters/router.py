"""
Platform Router

Routes requests to the appropriate platform adapter based on the platform parameter.
"""

import logging
from typing import Any, Dict, Optional
from .base import PlatformAdapter
from .meta_adapter import MetaAdapter
from .tiktok_adapter import TikTokAdapter
from .google_adapter import GoogleAdapter

logger = logging.getLogger(__name__)


class PlatformRouter:
    """
    Routes requests to the appropriate platform adapter.
    
    Maintains a registry of platform adapters and provides a unified
    interface for platform operations.
    """
    
    def __init__(self):
        """Initialize platform adapters."""
        self._adapters: Dict[str, PlatformAdapter] = {
            "meta": MetaAdapter(),
            "tiktok": TikTokAdapter(),
            "google": GoogleAdapter()
        }
        
        logger.info(
            f"Initialized platform router with adapters: {list(self._adapters.keys())}"
        )
    
    def get_adapter(self, platform: str) -> Optional[PlatformAdapter]:
        """
        Get the adapter for the specified platform.
        
        Args:
            platform: Platform name (meta, tiktok, google)
            
        Returns:
            PlatformAdapter instance or None if platform not supported
        """
        adapter = self._adapters.get(platform.lower())
        
        if not adapter:
            logger.warning(
                f"Unsupported platform requested: {platform}",
                extra={"platform": platform}
            )
        
        return adapter
    
    def is_supported(self, platform: str) -> bool:
        """
        Check if a platform is supported.
        
        Args:
            platform: Platform name
            
        Returns:
            True if platform is supported, False otherwise
        """
        return platform.lower() in self._adapters
    
    def get_supported_platforms(self) -> list[str]:
        """
        Get list of supported platforms.
        
        Returns:
            List of supported platform names
        """
        return list(self._adapters.keys())
    
    async def create_campaign(
        self,
        platform: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a campaign on the specified platform.
        
        Args:
            platform: Platform name
            params: Campaign parameters
            
        Returns:
            Campaign creation result
        """
        adapter = self.get_adapter(platform)
        
        if not adapter:
            return self._format_error(
                "1001",
                "INVALID_REQUEST",
                f"Unsupported platform: {platform}",
                {"supported_platforms": self.get_supported_platforms()}
            )
        
        return await adapter.create_campaign(params)
    
    async def create_adset(
        self,
        platform: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create an adset on the specified platform.
        
        Args:
            platform: Platform name
            params: Adset parameters
            
        Returns:
            Adset creation result
        """
        adapter = self.get_adapter(platform)
        
        if not adapter:
            return self._format_error(
                "1001",
                "INVALID_REQUEST",
                f"Unsupported platform: {platform}",
                {"supported_platforms": self.get_supported_platforms()}
            )
        
        return await adapter.create_adset(params)
    
    async def create_ad(
        self,
        platform: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create an ad on the specified platform.
        
        Args:
            platform: Platform name
            params: Ad parameters
            
        Returns:
            Ad creation result
        """
        adapter = self.get_adapter(platform)
        
        if not adapter:
            return self._format_error(
                "1001",
                "INVALID_REQUEST",
                f"Unsupported platform: {platform}",
                {"supported_platforms": self.get_supported_platforms()}
            )
        
        return await adapter.create_ad(params)
    
    async def update_budget(
        self,
        platform: str,
        adset_id: str,
        budget: float
    ) -> Dict[str, Any]:
        """
        Update adset budget on the specified platform.
        
        Args:
            platform: Platform name
            adset_id: Adset ID
            budget: New budget
            
        Returns:
            Budget update result
        """
        adapter = self.get_adapter(platform)
        
        if not adapter:
            return self._format_error(
                "1001",
                "INVALID_REQUEST",
                f"Unsupported platform: {platform}",
                {"supported_platforms": self.get_supported_platforms()}
            )
        
        return await adapter.update_budget(adset_id, budget)
    
    async def pause_adset(
        self,
        platform: str,
        adset_id: str
    ) -> Dict[str, Any]:
        """
        Pause an adset on the specified platform.
        
        Args:
            platform: Platform name
            adset_id: Adset ID
            
        Returns:
            Pause operation result
        """
        adapter = self.get_adapter(platform)
        
        if not adapter:
            return self._format_error(
                "1001",
                "INVALID_REQUEST",
                f"Unsupported platform: {platform}",
                {"supported_platforms": self.get_supported_platforms()}
            )
        
        return await adapter.pause_adset(adset_id)
    
    async def resume_adset(
        self,
        platform: str,
        adset_id: str
    ) -> Dict[str, Any]:
        """
        Resume an adset on the specified platform.
        
        Args:
            platform: Platform name
            adset_id: Adset ID
            
        Returns:
            Resume operation result
        """
        adapter = self.get_adapter(platform)
        
        if not adapter:
            return self._format_error(
                "1001",
                "INVALID_REQUEST",
                f"Unsupported platform: {platform}",
                {"supported_platforms": self.get_supported_platforms()}
            )
        
        return await adapter.resume_adset(adset_id)
    
    async def get_campaign_status(
        self,
        platform: str,
        campaign_id: str
    ) -> Dict[str, Any]:
        """
        Get campaign status from the specified platform.
        
        Args:
            platform: Platform name
            campaign_id: Campaign ID
            
        Returns:
            Campaign status
        """
        adapter = self.get_adapter(platform)
        
        if not adapter:
            return self._format_error(
                "1001",
                "INVALID_REQUEST",
                f"Unsupported platform: {platform}",
                {"supported_platforms": self.get_supported_platforms()}
            )
        
        return await adapter.get_campaign_status(campaign_id)
    
    async def delete_campaign(
        self,
        platform: str,
        campaign_id: str
    ) -> Dict[str, Any]:
        """
        Delete a campaign on the specified platform.
        
        Args:
            platform: Platform name
            campaign_id: Campaign ID
            
        Returns:
            Delete operation result
        """
        adapter = self.get_adapter(platform)
        
        if not adapter:
            return self._format_error(
                "1001",
                "INVALID_REQUEST",
                f"Unsupported platform: {platform}",
                {"supported_platforms": self.get_supported_platforms()}
            )
        
        return await adapter.delete_campaign(campaign_id)
    
    def _format_error(
        self,
        error_code: str,
        error_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format error response in standard format."""
        from datetime import datetime, timezone
        
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
