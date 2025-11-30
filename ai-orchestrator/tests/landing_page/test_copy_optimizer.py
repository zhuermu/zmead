"""
Tests for CopyOptimizer.

Tests the copy optimization functionality including:
- Response format with optimized_text, improvements, and confidence_score (Task 7.2)
- Fallback behavior returning original text on failure (Task 7.3)

Requirements: 4.1, 4.4, 4.5
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.landing_page.optimizers.copy_optimizer import (
    CopyOptimizer,
    CopyOptimizationResponse,
)
from app.modules.landing_page.models import OptimizationResult
from app.services.gemini_client import GeminiError


class TestCopyOptimizerResponseFormat:
    """Tests for optimization response format (Task 7.2).
    
    Requirements: 4.4
    """

    @pytest.mark.asyncio
    async def test_optimize_returns_correct_response_format(self):
        """Test that optimize returns OptimizationResult with all required fields."""
        # Arrange
        mock_gemini = MagicMock()
        mock_gemini.structured_output = AsyncMock(
            return_value=CopyOptimizationResponse(
                optimized_text="Experience Premium Sound Quality",
                improvements=[
                    "Added emotional appeal",
                    "Created urgency",
                    "Highlighted value proposition",
                ],
                confidence_score=0.92,
            )
        )
        
        optimizer = CopyOptimizer(gemini_client=mock_gemini)
        
        # Act
        result = await optimizer.optimize(
            current_text="Buy our headphones",
            section="hero",
            optimization_goal="increase_conversion",
        )
        
        # Assert
        assert isinstance(result, OptimizationResult)
        assert result.optimized_text == "Experience Premium Sound Quality"
        assert len(result.improvements) == 3
        assert "Added emotional appeal" in result.improvements
        assert result.confidence_score == 0.92
        assert result.fallback is False

    @pytest.mark.asyncio
    async def test_optimize_includes_confidence_score(self):
        """Test that confidence_score is included in the response."""
        # Arrange
        mock_gemini = MagicMock()
        mock_gemini.structured_output = AsyncMock(
            return_value=CopyOptimizationResponse(
                optimized_text="Optimized text",
                improvements=["Improvement 1"],
                confidence_score=0.85,
            )
        )
        
        optimizer = CopyOptimizer(gemini_client=mock_gemini)
        
        # Act
        result = await optimizer.optimize(
            current_text="Original text",
            section="cta",
            optimization_goal="urgency",
        )
        
        # Assert
        assert result.confidence_score == 0.85
        assert 0 <= result.confidence_score <= 1

    @pytest.mark.asyncio
    async def test_optimize_includes_improvements_list(self):
        """Test that improvements list is included in the response."""
        # Arrange
        mock_gemini = MagicMock()
        mock_gemini.structured_output = AsyncMock(
            return_value=CopyOptimizationResponse(
                optimized_text="Get Yours Now - Limited Time!",
                improvements=[
                    "Added urgency with 'Limited Time'",
                    "Used action verb 'Get'",
                    "Made it more personal with 'Yours'",
                ],
                confidence_score=0.88,
            )
        )
        
        optimizer = CopyOptimizer(gemini_client=mock_gemini)
        
        # Act
        result = await optimizer.optimize(
            current_text="Buy Now",
            section="cta",
            optimization_goal="urgency",
        )
        
        # Assert
        assert isinstance(result.improvements, list)
        assert len(result.improvements) == 3
        assert all(isinstance(imp, str) for imp in result.improvements)


class TestCopyOptimizerFallback:
    """Tests for fallback behavior (Task 7.3).
    
    Requirements: 4.5
    """

    @pytest.mark.asyncio
    async def test_fallback_on_gemini_error(self):
        """Test that original text is returned on Gemini API error."""
        # Arrange
        mock_gemini = MagicMock()
        mock_gemini.structured_output = AsyncMock(
            side_effect=GeminiError("API rate limit exceeded", code="RATE_LIMIT")
        )
        
        optimizer = CopyOptimizer(gemini_client=mock_gemini)
        original_text = "Buy our amazing product"
        
        # Act
        result = await optimizer.optimize(
            current_text=original_text,
            section="hero",
            optimization_goal="increase_conversion",
        )
        
        # Assert
        assert result.optimized_text == original_text
        assert result.improvements == []
        assert result.confidence_score == 0.0
        assert result.fallback is True

    @pytest.mark.asyncio
    async def test_fallback_on_unexpected_error(self):
        """Test that original text is returned on unexpected errors."""
        # Arrange
        mock_gemini = MagicMock()
        mock_gemini.structured_output = AsyncMock(
            side_effect=Exception("Unexpected error")
        )
        
        optimizer = CopyOptimizer(gemini_client=mock_gemini)
        original_text = "Shop now for great deals"
        
        # Act
        result = await optimizer.optimize(
            current_text=original_text,
            section="cta",
            optimization_goal="emotional_appeal",
        )
        
        # Assert
        assert result.optimized_text == original_text
        assert result.improvements == []
        assert result.confidence_score == 0.0
        assert result.fallback is True

    @pytest.mark.asyncio
    async def test_fallback_on_empty_text(self):
        """Test that empty text returns fallback result."""
        # Arrange
        mock_gemini = MagicMock()
        optimizer = CopyOptimizer(gemini_client=mock_gemini)
        
        # Act
        result = await optimizer.optimize(
            current_text="",
            section="hero",
            optimization_goal="increase_conversion",
        )
        
        # Assert
        assert result.optimized_text == ""
        assert result.improvements == []
        assert result.confidence_score == 0.0
        assert result.fallback is True
        # Gemini should not be called for empty text
        mock_gemini.structured_output.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_on_whitespace_only_text(self):
        """Test that whitespace-only text returns fallback result."""
        # Arrange
        mock_gemini = MagicMock()
        optimizer = CopyOptimizer(gemini_client=mock_gemini)
        
        # Act
        result = await optimizer.optimize(
            current_text="   \n\t  ",
            section="hero",
            optimization_goal="increase_conversion",
        )
        
        # Assert
        assert result.optimized_text == "   \n\t  "
        assert result.fallback is True
        mock_gemini.structured_output.assert_not_called()


class TestCopyOptimizerSections:
    """Tests for section-specific optimization."""

    @pytest.mark.asyncio
    async def test_optimize_hero_section(self):
        """Test optimization for hero section."""
        # Arrange
        mock_gemini = MagicMock()
        mock_gemini.structured_output = AsyncMock(
            return_value=CopyOptimizationResponse(
                optimized_text="Transform Your Sound Experience",
                improvements=["Added transformation language"],
                confidence_score=0.9,
            )
        )
        
        optimizer = CopyOptimizer(gemini_client=mock_gemini)
        
        # Act
        result = await optimizer.optimize(
            current_text="Good headphones",
            section="hero",
            optimization_goal="emotional_appeal",
        )
        
        # Assert
        assert result.optimized_text == "Transform Your Sound Experience"
        assert result.fallback is False

    @pytest.mark.asyncio
    async def test_optimize_cta_section(self):
        """Test optimization for CTA section."""
        # Arrange
        mock_gemini = MagicMock()
        mock_gemini.structured_output = AsyncMock(
            return_value=CopyOptimizationResponse(
                optimized_text="Claim Your Discount Now",
                improvements=["Added action verb", "Created urgency"],
                confidence_score=0.87,
            )
        )
        
        optimizer = CopyOptimizer(gemini_client=mock_gemini)
        
        # Act
        result = await optimizer.optimize(
            current_text="Buy",
            section="cta",
            optimization_goal="urgency",
        )
        
        # Assert
        assert result.optimized_text == "Claim Your Discount Now"
        assert result.fallback is False

    @pytest.mark.asyncio
    async def test_optimize_unsupported_section_uses_default(self):
        """Test that unsupported sections use default prompt."""
        # Arrange
        mock_gemini = MagicMock()
        mock_gemini.structured_output = AsyncMock(
            return_value=CopyOptimizationResponse(
                optimized_text="Optimized text",
                improvements=["General improvement"],
                confidence_score=0.8,
            )
        )
        
        optimizer = CopyOptimizer(gemini_client=mock_gemini)
        
        # Act
        result = await optimizer.optimize(
            current_text="Some text",
            section="unknown_section",
            optimization_goal="increase_conversion",
        )
        
        # Assert
        assert result.optimized_text == "Optimized text"
        assert result.fallback is False


class TestCopyOptimizerGoals:
    """Tests for optimization goals."""

    @pytest.mark.asyncio
    async def test_optimize_with_conversion_goal(self):
        """Test optimization with increase_conversion goal."""
        # Arrange
        mock_gemini = MagicMock()
        mock_gemini.structured_output = AsyncMock(
            return_value=CopyOptimizationResponse(
                optimized_text="Limited Time: 50% Off Premium Headphones",
                improvements=["Added scarcity", "Included discount"],
                confidence_score=0.91,
            )
        )
        
        optimizer = CopyOptimizer(gemini_client=mock_gemini)
        
        # Act
        result = await optimizer.optimize(
            current_text="Premium Headphones",
            section="hero",
            optimization_goal="increase_conversion",
        )
        
        # Assert
        assert "Limited Time" in result.optimized_text
        assert result.fallback is False

    @pytest.mark.asyncio
    async def test_optimize_with_context(self):
        """Test optimization with product context."""
        # Arrange
        mock_gemini = MagicMock()
        mock_gemini.structured_output = AsyncMock(
            return_value=CopyOptimizationResponse(
                optimized_text="Experience Studio-Quality Sound - $79.99",
                improvements=["Added price", "Highlighted quality"],
                confidence_score=0.89,
            )
        )
        
        optimizer = CopyOptimizer(gemini_client=mock_gemini)
        
        context = {
            "product_info": {
                "title": "Premium Wireless Headphones",
                "price": 79.99,
                "currency": "USD",
                "features": ["Noise cancellation", "30-hour battery"],
            }
        }
        
        # Act
        result = await optimizer.optimize(
            current_text="Good headphones",
            section="hero",
            optimization_goal="increase_conversion",
            context=context,
        )
        
        # Assert
        assert result.optimized_text == "Experience Studio-Quality Sound - $79.99"
        assert result.fallback is False
