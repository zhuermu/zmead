"""
Integration tests for Ad Creative module.

Tests the complete creative generation and credit flow.

Requirements: All
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.modules.ad_creative.capability import AdCreative
from app.modules.ad_creative.models import (
    Creative,
    ProductInfo,
    GeneratedImage,
    GetCreativesRequest,
)
from app.modules.ad_creative.managers.creative_manager import CreativeManager
from app.modules.ad_creative.utils.credit_checker import CreditChecker


class TestAdCreativeCapability:
    """Integration tests for AdCreative capability."""

    @pytest.mark.asyncio
    async def test_get_creatives_returns_list(
        self,
        mock_mcp_client,
        mock_gemini_client,
        sample_creative,
    ):
        """Test get_creatives action returns creative list."""
        # Setup mock
        mock_mcp_client.call_tool.return_value = {
            "creatives": [sample_creative],
            "total": 1,
        }

        # Create capability with mocked clients
        capability = AdCreative(
            mcp_client=mock_mcp_client,
            gemini_client=mock_gemini_client,
        )

        # Execute
        result = await capability.execute(
            action="get_creatives",
            parameters={"limit": 10},
            context={"user_id": "user_123"},
        )

        # Verify
        assert result["status"] == "success"
        assert len(result["creatives"]) == 1
        assert result["total"] == 1
        mock_mcp_client.call_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_creative_success(
        self,
        mock_mcp_client,
        mock_gemini_client,
    ):
        """Test delete_creative action succeeds."""
        # Setup mock
        mock_mcp_client.call_tool.return_value = {"deleted": True}

        # Create capability with mocked clients
        capability = AdCreative(
            mcp_client=mock_mcp_client,
            gemini_client=mock_gemini_client,
        )

        # Execute
        result = await capability.execute(
            action="delete_creative",
            parameters={"creative_id": "creative_123"},
            context={"user_id": "user_456"},
        )

        # Verify
        assert result["status"] == "success"
        assert "删除成功" in result["message"]

    @pytest.mark.asyncio
    async def test_unknown_action_returns_error(
        self,
        mock_mcp_client,
        mock_gemini_client,
    ):
        """Test unknown action returns error."""
        capability = AdCreative(
            mcp_client=mock_mcp_client,
            gemini_client=mock_gemini_client,
        )

        result = await capability.execute(
            action="unknown_action",
            parameters={},
            context={"user_id": "user_123"},
        )

        assert result["status"] == "error"
        assert result["error"]["code"] == "1001"
        assert "unknown_action" in result["error"]["message"].lower()


class TestCreativeManager:
    """Integration tests for CreativeManager."""

    @pytest.mark.asyncio
    async def test_get_creatives_with_filters(
        self,
        mock_mcp_client,
        sample_creative,
    ):
        """Test get_creatives with filter parameters."""
        # Setup mock
        mock_mcp_client.call_tool.return_value = {
            "creatives": [sample_creative],
            "total": 1,
        }

        manager = CreativeManager(mcp_client=mock_mcp_client)

        # Execute with filters
        request = GetCreativesRequest(
            filters={"platform": "tiktok"},
            sort_by="score",
            sort_order="desc",
            limit=20,
        )
        result = await manager.get_creatives(
            user_id="user_123",
            request=request,
        )

        # Verify
        assert result.status == "success"
        assert len(result.creatives) == 1
        assert result.creatives[0].platform == "tiktok"

    @pytest.mark.asyncio
    async def test_capacity_warning_when_over_100(
        self,
        mock_mcp_client,
        sample_creative,
    ):
        """Test capacity warning is set when total > 100."""
        # Setup mock with 101 creatives
        mock_mcp_client.call_tool.return_value = {
            "creatives": [sample_creative],
            "total": 101,
        }

        manager = CreativeManager(mcp_client=mock_mcp_client)

        result = await manager.get_creatives(user_id="user_123")

        # Verify capacity warning
        assert result.capacity_warning is True

    @pytest.mark.asyncio
    async def test_sorting_by_score_descending(
        self,
        mock_mcp_client,
    ):
        """Test creatives are sorted by score descending."""
        # Setup mock with multiple creatives
        creatives = [
            {**self._base_creative(), "creative_id": "1", "score": 70},
            {**self._base_creative(), "creative_id": "2", "score": 90},
            {**self._base_creative(), "creative_id": "3", "score": 80},
        ]
        mock_mcp_client.call_tool.return_value = {
            "creatives": creatives,
            "total": 3,
        }

        manager = CreativeManager(mcp_client=mock_mcp_client)

        result = await manager.get_creatives(user_id="user_123")

        # Verify sorted by score descending
        scores = [c.score for c in result.creatives]
        assert scores == [90, 80, 70]

    def _base_creative(self):
        """Return base creative dict for testing."""
        return {
            "user_id": "user_123",
            "url": "https://example.com/image.png",
            "aspect_ratio": "1:1",
            "created_at": "2024-01-15T10:00:00Z",
        }


class TestCreditChecker:
    """Integration tests for CreditChecker."""

    @pytest.mark.asyncio
    async def test_calculate_cost_normal_rate(self):
        """Test normal rate calculation (< 10 images)."""
        checker = CreditChecker()

        cost = checker.calculate_cost("image_generation", 5)

        assert cost == 2.5  # 5 * 0.5

    @pytest.mark.asyncio
    async def test_calculate_cost_bulk_discount(self):
        """Test bulk discount rate (>= 10 images)."""
        checker = CreditChecker()

        cost = checker.calculate_cost("image_generation", 10)

        assert cost == 4.0  # 10 * 0.4 (bulk rate)

    @pytest.mark.asyncio
    async def test_calculate_cost_bulk_discount_large(self):
        """Test bulk discount for large orders."""
        checker = CreditChecker()

        cost = checker.calculate_cost("image_generation", 50)

        assert cost == 20.0  # 50 * 0.4 (bulk rate)

    @pytest.mark.asyncio
    async def test_calculate_cost_analysis(self):
        """Test creative analysis cost."""
        checker = CreditChecker()

        cost = checker.calculate_cost("creative_analysis", 1)

        assert cost == 0.2

    @pytest.mark.asyncio
    async def test_calculate_cost_competitor_analysis(self):
        """Test competitor analysis cost."""
        checker = CreditChecker()

        cost = checker.calculate_cost("competitor_analysis", 1)

        assert cost == 1.0

    @pytest.mark.asyncio
    async def test_check_and_reserve_sufficient_credits(
        self,
        mock_mcp_client,
    ):
        """Test check_and_reserve with sufficient credits."""
        # Setup mock
        mock_mcp_client.check_credit = AsyncMock(return_value={
            "sufficient": True,
            "available": 100.0,
        })

        checker = CreditChecker(mcp_client=mock_mcp_client)

        result = await checker.check_and_reserve(
            user_id="user_123",
            operation="image_generation",
            count=5,
        )

        assert result.allowed is True
        assert result.required_credits == 2.5
        assert result.available_credits == 100.0

    @pytest.mark.asyncio
    async def test_check_and_reserve_insufficient_credits(
        self,
        mock_mcp_client,
    ):
        """Test check_and_reserve with insufficient credits."""
        # Setup mock
        mock_mcp_client.check_credit = AsyncMock(return_value={
            "sufficient": False,
            "available": 1.0,
        })

        checker = CreditChecker(mcp_client=mock_mcp_client)

        result = await checker.check_and_reserve(
            user_id="user_123",
            operation="image_generation",
            count=5,
        )

        assert result.allowed is False
        assert result.error_code == "6011"
        assert "余额不足" in result.error_message


class TestCacheManager:
    """Integration tests for CacheManager."""

    @pytest.mark.asyncio
    async def test_cache_disabled_without_redis(self):
        """Test cache is disabled when no Redis client."""
        from app.modules.ad_creative.utils.cache_manager import CacheManager

        manager = CacheManager(redis_client=None)

        assert manager.enabled is False

        # Operations should return None/False gracefully
        result = await manager.get_product_info("https://example.com/product")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_product_info_roundtrip(
        self,
        mock_redis_client,
    ):
        """Test caching and retrieving product info."""
        from app.modules.ad_creative.utils.cache_manager import CacheManager
        import json

        # Setup mock to return cached value
        product_data = {
            "title": "Test Product",
            "price": 29.99,
            "currency": "USD",
            "images": ["https://example.com/img.jpg"],
            "description": "Test description",
            "selling_points": ["Point 1"],
            "source": "shopify",
        }
        mock_redis_client.get = AsyncMock(return_value=json.dumps(product_data))

        manager = CacheManager(redis_client=mock_redis_client)

        # Get cached value
        result = await manager.get_product_info("https://example.com/product")

        assert result is not None
        assert result.title == "Test Product"
        assert result.price == 29.99


class TestAspectRatioHandler:
    """Integration tests for AspectRatioHandler."""

    def test_platform_to_aspect_ratio_mapping(self):
        """Test platform to aspect ratio mapping."""
        from app.modules.ad_creative.utils.aspect_ratio import AspectRatioHandler

        handler = AspectRatioHandler()

        assert handler.get_ratio_for_platform("tiktok") == "9:16"
        assert handler.get_ratio_for_platform("instagram") == "1:1"
        assert handler.get_ratio_for_platform("facebook") == "4:5"

    def test_get_dimensions_for_aspect_ratio(self):
        """Test getting dimensions for aspect ratio."""
        from app.modules.ad_creative.utils.aspect_ratio import AspectRatioHandler

        handler = AspectRatioHandler()

        width, height = handler.get_dimensions("9:16")
        assert width == 1080
        assert height == 1920

        width, height = handler.get_dimensions("1:1")
        assert width == 1080
        assert height == 1080

    def test_custom_aspect_ratio_parsing(self):
        """Test parsing custom aspect ratio."""
        from app.modules.ad_creative.utils.aspect_ratio import AspectRatioHandler

        handler = AspectRatioHandler()

        # Custom ratio should be parsed
        width, height = handler.get_dimensions("16:9")
        assert width > 0
        assert height > 0


class TestFileValidator:
    """Integration tests for FileValidator."""

    def test_validate_valid_jpeg(self):
        """Test validation of valid JPEG file."""
        from app.modules.ad_creative.utils.validators import FileValidator

        validator = FileValidator()

        # JPEG magic bytes (FF D8 FF)
        jpeg_data = b"\xff\xd8\xff\xe0" + b"\x00" * 1000

        result = validator.validate(
            file_data=jpeg_data,
            file_type="image/jpeg",
            file_size=len(jpeg_data),
        )

        assert result.is_valid is True
        assert result.detected_type == "image/jpeg"

    def test_validate_valid_png(self):
        """Test validation of valid PNG file."""
        from app.modules.ad_creative.utils.validators import FileValidator

        validator = FileValidator()

        # PNG magic bytes
        png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 1000

        result = validator.validate(
            file_data=png_data,
            file_type="image/png",
            file_size=len(png_data),
        )

        assert result.is_valid is True
        assert result.detected_type == "image/png"

    def test_validate_invalid_file_type(self):
        """Test validation rejects invalid file type."""
        from app.modules.ad_creative.utils.validators import FileValidator

        validator = FileValidator()

        result = validator.validate(
            file_data=b"test data",
            file_type="application/pdf",
            file_size=9,
        )

        assert result.is_valid is False
        assert "格式" in result.error_message or "format" in result.error_message.lower()

    def test_validate_file_too_large(self):
        """Test validation rejects files over 10MB."""
        from app.modules.ad_creative.utils.validators import FileValidator

        validator = FileValidator()

        # 11MB file
        large_size = 11 * 1024 * 1024

        result = validator.validate(
            file_data=b"\xff\xd8\xff",  # JPEG header (minimum for magic number)
            file_type="image/jpeg",
            file_size=large_size,
        )

        assert result.is_valid is False
        assert "大小" in result.error_message or "10" in result.error_message
