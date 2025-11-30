"""
Tests for Platform Adapters

Tests the platform adapter infrastructure including routing and basic operations.
"""

import pytest
from app.modules.campaign_automation.adapters import (
    PlatformRouter,
    MetaAdapter,
    TikTokAdapter,
    GoogleAdapter
)


class TestPlatformRouter:
    """Test platform router functionality"""
    
    @pytest.fixture
    def router(self):
        """Create a platform router instance"""
        return PlatformRouter()
    
    def test_router_initialization(self, router):
        """Test that router initializes with all adapters"""
        supported = router.get_supported_platforms()
        assert "meta" in supported
        assert "tiktok" in supported
        assert "google" in supported
    
    def test_get_adapter_meta(self, router):
        """Test getting Meta adapter"""
        adapter = router.get_adapter("meta")
        assert adapter is not None
        assert isinstance(adapter, MetaAdapter)
    
    def test_get_adapter_tiktok(self, router):
        """Test getting TikTok adapter"""
        adapter = router.get_adapter("tiktok")
        assert adapter is not None
        assert isinstance(adapter, TikTokAdapter)
    
    def test_get_adapter_google(self, router):
        """Test getting Google adapter"""
        adapter = router.get_adapter("google")
        assert adapter is not None
        assert isinstance(adapter, GoogleAdapter)
    
    def test_get_adapter_unsupported(self, router):
        """Test getting unsupported adapter returns None"""
        adapter = router.get_adapter("unsupported_platform")
        assert adapter is None
    
    def test_is_supported_meta(self, router):
        """Test checking if Meta is supported"""
        assert router.is_supported("meta") is True
    
    def test_is_supported_unsupported(self, router):
        """Test checking if unsupported platform"""
        assert router.is_supported("unsupported") is False
    
    @pytest.mark.asyncio
    async def test_create_campaign_unsupported_platform(self, router):
        """Test creating campaign on unsupported platform returns error"""
        result = await router.create_campaign(
            platform="unsupported",
            params={"name": "Test Campaign"}
        )
        
        assert result["status"] == "error"
        assert result["error"]["code"] == "1001"
        assert "unsupported" in result["error"]["message"].lower()


class TestMetaAdapter:
    """Test Meta adapter functionality"""
    
    @pytest.fixture
    def adapter(self):
        """Create a Meta adapter instance"""
        return MetaAdapter()
    
    def test_adapter_initialization(self, adapter):
        """Test that adapter initializes correctly"""
        assert adapter.api_version == "v18.0"
        assert "facebook.com" in adapter.base_url
    
    @pytest.mark.asyncio
    async def test_create_campaign_missing_ad_account(self, adapter):
        """Test creating campaign without ad_account_id returns error"""
        result = await adapter.create_campaign({
            "name": "Test Campaign",
            "objective": "sales",
            "daily_budget": 100.0
        })
        
        assert result["status"] == "error"
        # Could be 1001 (missing param) or 5001 (SDK not installed)
        assert result["error"]["code"] in ["1001", "5001"]
    
    @pytest.mark.asyncio
    async def test_create_adset_missing_campaign_id(self, adapter):
        """Test creating adset without campaign_id returns error"""
        result = await adapter.create_adset({
            "name": "Test Adset",
            "daily_budget": 50.0,
            "targeting": {}
        })
        
        assert result["status"] == "error"
        # Could be 1001 (missing param) or 5001 (SDK not installed)
        assert result["error"]["code"] in ["1001", "5001"]
    
    @pytest.mark.asyncio
    async def test_create_ad_missing_adset_id(self, adapter):
        """Test creating ad without adset_id returns error"""
        result = await adapter.create_ad({
            "name": "Test Ad",
            "creative_id": "creative_123",
            "copy": "Test copy"
        })
        
        assert result["status"] == "error"
        # Could be 1001 (missing param) or 5001 (SDK not installed)
        assert result["error"]["code"] in ["1001", "5001"]


class TestTikTokAdapter:
    """Test TikTok adapter functionality"""
    
    @pytest.fixture
    def adapter(self):
        """Create a TikTok adapter instance"""
        return TikTokAdapter()
    
    def test_adapter_initialization(self, adapter):
        """Test that adapter initializes correctly"""
        assert adapter.api_version == "v1.3"
        assert "tiktok.com" in adapter.base_url
    
    @pytest.mark.asyncio
    async def test_create_campaign_missing_advertiser_id(self, adapter):
        """Test creating campaign without advertiser_id returns error"""
        result = await adapter.create_campaign({
            "name": "Test Campaign",
            "objective": "sales",
            "daily_budget": 100.0
        })
        
        assert result["status"] == "error"
        assert result["error"]["code"] == "1001"
        assert "advertiser_id" in result["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_create_campaign_with_advertiser_id(self, adapter):
        """Test creating campaign with advertiser_id succeeds (mock)"""
        result = await adapter.create_campaign({
            "name": "Test Campaign",
            "objective": "sales",
            "daily_budget": 100.0,
            "advertiser_id": "advertiser_123"
        })
        
        # Mock implementation should succeed
        assert "id" in result
        assert result["name"] == "Test Campaign"
        assert result["status"] == "active"


class TestGoogleAdapter:
    """Test Google adapter functionality"""
    
    @pytest.fixture
    def adapter(self):
        """Create a Google adapter instance"""
        return GoogleAdapter()
    
    def test_adapter_initialization(self, adapter):
        """Test that adapter initializes correctly"""
        assert adapter.api_version == "v14"
        assert "googleads.googleapis.com" in adapter.base_url
    
    @pytest.mark.asyncio
    async def test_create_campaign_missing_customer_id(self, adapter):
        """Test creating campaign without customer_id returns error"""
        result = await adapter.create_campaign({
            "name": "Test Campaign",
            "objective": "sales",
            "daily_budget": 100.0
        })
        
        assert result["status"] == "error"
        assert result["error"]["code"] == "1001"
        assert "customer_id" in result["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_create_campaign_with_customer_id(self, adapter):
        """Test creating campaign with customer_id succeeds (mock)"""
        result = await adapter.create_campaign({
            "name": "Test Campaign",
            "objective": "sales",
            "daily_budget": 100.0,
            "customer_id": "customer_123"
        })
        
        # Mock implementation should succeed
        assert "id" in result
        assert result["name"] == "Test Campaign"
        assert result["status"] == "active"


class TestPlatformConsistency:
    """Test that all adapters provide consistent interfaces"""
    
    @pytest.fixture(params=["meta", "tiktok", "google"])
    def adapter(self, request):
        """Parametrized fixture to test all adapters"""
        router = PlatformRouter()
        return router.get_adapter(request.param)
    
    @pytest.mark.asyncio
    async def test_all_adapters_have_create_campaign(self, adapter):
        """Test that all adapters implement create_campaign"""
        assert hasattr(adapter, "create_campaign")
        assert callable(adapter.create_campaign)
    
    @pytest.mark.asyncio
    async def test_all_adapters_have_create_adset(self, adapter):
        """Test that all adapters implement create_adset"""
        assert hasattr(adapter, "create_adset")
        assert callable(adapter.create_adset)
    
    @pytest.mark.asyncio
    async def test_all_adapters_have_create_ad(self, adapter):
        """Test that all adapters implement create_ad"""
        assert hasattr(adapter, "create_ad")
        assert callable(adapter.create_ad)
    
    @pytest.mark.asyncio
    async def test_all_adapters_have_update_budget(self, adapter):
        """Test that all adapters implement update_budget"""
        assert hasattr(adapter, "update_budget")
        assert callable(adapter.update_budget)
    
    @pytest.mark.asyncio
    async def test_all_adapters_have_pause_adset(self, adapter):
        """Test that all adapters implement pause_adset"""
        assert hasattr(adapter, "pause_adset")
        assert callable(adapter.pause_adset)
    
    @pytest.mark.asyncio
    async def test_all_adapters_have_resume_adset(self, adapter):
        """Test that all adapters implement resume_adset"""
        assert hasattr(adapter, "resume_adset")
        assert callable(adapter.resume_adset)
    
    @pytest.mark.asyncio
    async def test_all_adapters_have_get_campaign_status(self, adapter):
        """Test that all adapters implement get_campaign_status"""
        assert hasattr(adapter, "get_campaign_status")
        assert callable(adapter.get_campaign_status)
    
    @pytest.mark.asyncio
    async def test_all_adapters_have_delete_campaign(self, adapter):
        """Test that all adapters implement delete_campaign"""
        assert hasattr(adapter, "delete_campaign")
        assert callable(adapter.delete_campaign)
