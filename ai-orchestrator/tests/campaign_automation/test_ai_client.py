"""
Tests for AIClient - AI-powered ad copy generation.

Requirements: 2.4, 2.5
"""

import pytest
from unittest.mock import AsyncMock

from app.modules.campaign_automation.clients.ai_client import AIClient
from app.services.gemini_client import GeminiClient, GeminiError, GeminiRateLimitError


@pytest.fixture
def mock_gemini_client():
    """Mock Gemini client"""
    return AsyncMock(spec=GeminiClient)


@pytest.fixture
def ai_client(mock_gemini_client):
    """AIClient instance with mocked Gemini client"""
    return AIClient(gemini_client=mock_gemini_client)


class TestAIClientInitialization:
    """Test AIClient initialization"""
    
    def test_initialization(self, mock_gemini_client):
        """Test AIClient initializes correctly"""
        client = AIClient(gemini_client=mock_gemini_client)
        
        assert client.gemini_client == mock_gemini_client
        assert client.MAX_COPY_LENGTH == 125
        assert client.DEFAULT_TEMPLATE == "限时优惠！立即购买"


class TestGenerateAdCopy:
    """Test ad copy generation with fallback strategy"""
    
    @pytest.mark.asyncio
    async def test_generate_with_pro_success(self, ai_client, mock_gemini_client):
        """Test successful generation with Gemini Pro"""
        mock_gemini_client.chat_completion = AsyncMock(
            return_value="限时优惠！立即购买 https://example.com/product"
        )
        
        result = await ai_client.generate_ad_copy(
            product_url="https://example.com/product",
            creative_id="creative_1",
            platform="meta",
        )
        
        assert result == "限时优惠！立即购买 https://example.com/product"
        mock_gemini_client.chat_completion.assert_called_once()
        mock_gemini_client.fast_completion.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_generate_with_flash_fallback(self, ai_client, mock_gemini_client):
        """Test fallback to Gemini Flash when Pro fails"""
        # Pro fails
        mock_gemini_client.chat_completion = AsyncMock(
            side_effect=GeminiRateLimitError("Rate limit exceeded")
        )
        
        # Flash succeeds
        mock_gemini_client.fast_completion = AsyncMock(
            return_value="限时优惠！立即购买 https://example.com/product"
        )
        
        result = await ai_client.generate_ad_copy(
            product_url="https://example.com/product",
            creative_id="creative_1",
            platform="meta",
        )
        
        assert result == "限时优惠！立即购买 https://example.com/product"
        mock_gemini_client.chat_completion.assert_called_once()
        mock_gemini_client.fast_completion.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_with_template_fallback(self, ai_client, mock_gemini_client):
        """Test fallback to template when both AI models fail"""
        # Both Pro and Flash fail
        mock_gemini_client.chat_completion = AsyncMock(
            side_effect=GeminiRateLimitError("Rate limit exceeded")
        )
        mock_gemini_client.fast_completion = AsyncMock(
            side_effect=GeminiError("API error", retryable=False)
        )
        
        result = await ai_client.generate_ad_copy(
            product_url="https://example.com/product",
            creative_id="creative_1",
            platform="meta",
        )
        
        assert result == "限时优惠！立即购买 https://example.com/product"
        mock_gemini_client.chat_completion.assert_called_once()
        mock_gemini_client.fast_completion.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_without_product_url(self, ai_client, mock_gemini_client):
        """Test generation without product URL returns template"""
        result = await ai_client.generate_ad_copy(
            product_url="",
            creative_id="creative_1",
            platform="meta",
        )
        
        assert result == "限时优惠！立即购买"
        mock_gemini_client.chat_completion.assert_not_called()
        mock_gemini_client.fast_completion.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_generate_with_custom_max_length(self, ai_client, mock_gemini_client):
        """Test generation with custom max length"""
        mock_gemini_client.chat_completion = AsyncMock(
            return_value="限时优惠！立即购买"
        )
        
        result = await ai_client.generate_ad_copy(
            product_url="https://example.com/product",
            creative_id="creative_1",
            platform="meta",
            max_length=50,
        )
        
        assert result == "限时优惠！立即购买"
        
        # Verify prompt includes custom max_length
        call_args = mock_gemini_client.chat_completion.call_args
        messages = call_args[1]["messages"]
        assert "50" in messages[0]["content"]


class TestCopyValidation:
    """Test copy validation and cleaning"""
    
    @pytest.mark.asyncio
    async def test_validate_removes_quotes(self, ai_client, mock_gemini_client):
        """Test that quotes are removed from generated copy"""
        mock_gemini_client.chat_completion = AsyncMock(
            return_value='"限时优惠！立即购买"'
        )
        
        result = await ai_client.generate_ad_copy(
            product_url="https://example.com/product",
            creative_id="creative_1",
            platform="meta",
        )
        
        assert result == "限时优惠！立即购买"
        assert not result.startswith('"')
        assert not result.endswith('"')
    
    @pytest.mark.asyncio
    async def test_validate_truncates_long_copy(self, ai_client, mock_gemini_client):
        """Test that long copy is truncated"""
        long_copy = "A" * 200  # 200 characters
        mock_gemini_client.chat_completion = AsyncMock(return_value=long_copy)
        
        result = await ai_client.generate_ad_copy(
            product_url="https://example.com/product",
            creative_id="creative_1",
            platform="meta",
            max_length=125,
        )
        
        assert len(result) <= 125
        assert result.endswith("...")
    
    @pytest.mark.asyncio
    async def test_validate_strips_whitespace(self, ai_client, mock_gemini_client):
        """Test that whitespace is stripped"""
        mock_gemini_client.chat_completion = AsyncMock(
            return_value="  限时优惠！立即购买  "
        )
        
        result = await ai_client.generate_ad_copy(
            product_url="https://example.com/product",
            creative_id="creative_1",
            platform="meta",
        )
        
        assert result == "限时优惠！立即购买"
        assert not result.startswith(" ")
        assert not result.endswith(" ")
    
    @pytest.mark.asyncio
    async def test_validate_empty_copy_returns_template(self, ai_client, mock_gemini_client):
        """Test that empty copy returns template"""
        mock_gemini_client.chat_completion = AsyncMock(return_value="")
        
        result = await ai_client.generate_ad_copy(
            product_url="https://example.com/product",
            creative_id="creative_1",
            platform="meta",
        )
        
        # When AI returns empty, _validate_copy returns DEFAULT_TEMPLATE
        assert result == "限时优惠！立即购买"


class TestPromptBuilding:
    """Test prompt building for different platforms"""
    
    @pytest.mark.asyncio
    async def test_prompt_includes_platform(self, ai_client, mock_gemini_client):
        """Test that prompt includes platform name"""
        mock_gemini_client.chat_completion = AsyncMock(
            return_value="限时优惠！立即购买"
        )
        
        await ai_client.generate_ad_copy(
            product_url="https://example.com/product",
            creative_id="creative_1",
            platform="tiktok",
        )
        
        call_args = mock_gemini_client.chat_completion.call_args
        messages = call_args[1]["messages"]
        prompt = messages[0]["content"]
        
        assert "tiktok" in prompt.lower()
    
    @pytest.mark.asyncio
    async def test_prompt_includes_product_url(self, ai_client, mock_gemini_client):
        """Test that prompt includes product URL"""
        mock_gemini_client.chat_completion = AsyncMock(
            return_value="限时优惠！立即购买"
        )
        
        product_url = "https://example.com/special-product"
        await ai_client.generate_ad_copy(
            product_url=product_url,
            creative_id="creative_1",
            platform="meta",
        )
        
        call_args = mock_gemini_client.chat_completion.call_args
        messages = call_args[1]["messages"]
        prompt = messages[0]["content"]
        
        assert product_url in prompt
    
    @pytest.mark.asyncio
    async def test_prompt_includes_max_length(self, ai_client, mock_gemini_client):
        """Test that prompt includes max length constraint"""
        mock_gemini_client.chat_completion = AsyncMock(
            return_value="限时优惠！立即购买"
        )
        
        await ai_client.generate_ad_copy(
            product_url="https://example.com/product",
            creative_id="creative_1",
            platform="meta",
            max_length=100,
        )
        
        call_args = mock_gemini_client.chat_completion.call_args
        messages = call_args[1]["messages"]
        prompt = messages[0]["content"]
        
        assert "100" in prompt


class TestTemperatureSetting:
    """Test temperature setting for creative generation"""
    
    @pytest.mark.asyncio
    async def test_uses_creative_temperature(self, ai_client, mock_gemini_client):
        """Test that creative temperature (0.7) is used"""
        mock_gemini_client.chat_completion = AsyncMock(
            return_value="限时优惠！立即购买"
        )
        
        await ai_client.generate_ad_copy(
            product_url="https://example.com/product",
            creative_id="creative_1",
            platform="meta",
        )
        
        call_args = mock_gemini_client.chat_completion.call_args
        assert call_args[1]["temperature"] == 0.7
