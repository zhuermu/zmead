"""
Tests for Landing Page A/B Test Manager.

Tests the ABTestManager class for landing page A/B testing functionality,
including test creation, traffic distribution, chi-square analysis,
winner identification, and recommendation generation.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.modules.landing_page.managers.ab_test_manager import ABTestManager
from app.modules.landing_page.models import VariantStats


class TestABTestManagerCreate:
    """Tests for A/B test creation (Requirements 6.1, 6.2)"""

    @pytest.fixture
    def ab_test_manager(self):
        """Create ABTestManager with mocked dependencies"""
        mcp_client = AsyncMock()
        mcp_client.call_tool = AsyncMock(return_value={"status": "success"})
        return ABTestManager(mcp_client=mcp_client)

    @pytest.mark.asyncio
    async def test_create_test_success(self, ab_test_manager):
        """Test successful A/B test creation"""
        result = await ab_test_manager.create_test(
            test_name="Headline Test",
            landing_page_id="lp_123",
            variants=[
                {"name": "Variant A", "changes": {"hero.headline": "Title A"}},
                {"name": "Variant B", "changes": {"hero.headline": "Title B"}},
            ],
            traffic_split=[50, 50],
            duration_days=7,
            context={"user_id": "user_123"},
        )

        assert result["status"] == "success"
        assert result["test_id"] is not None
        assert result["test_id"].startswith("test_")
        assert len(result["variant_urls"]) == 2
        assert "?variant=a" in result["variant_urls"][0]
        assert "?variant=b" in result["variant_urls"][1]

    @pytest.mark.asyncio
    async def test_create_test_invalid_traffic_split(self, ab_test_manager):
        """Test that invalid traffic split raises error"""
        with pytest.raises(ValueError, match="must sum to 100"):
            await ab_test_manager.create_test(
                test_name="Test",
                landing_page_id="lp_123",
                variants=[
                    {"name": "A", "changes": {}},
                    {"name": "B", "changes": {}},
                ],
                traffic_split=[40, 40],  # Sum is 80, not 100
                duration_days=7,
                context={"user_id": "user_123"},
            )

    @pytest.mark.asyncio
    async def test_create_test_mismatched_variants_and_split(self, ab_test_manager):
        """Test that mismatched variants and traffic split raises error"""
        with pytest.raises(ValueError, match="must match"):
            await ab_test_manager.create_test(
                test_name="Test",
                landing_page_id="lp_123",
                variants=[
                    {"name": "A", "changes": {}},
                    {"name": "B", "changes": {}},
                ],
                traffic_split=[50, 30, 20],  # 3 splits for 2 variants
                duration_days=7,
                context={"user_id": "user_123"},
            )

    @pytest.mark.asyncio
    async def test_create_test_three_variants(self, ab_test_manager):
        """Test A/B test creation with three variants"""
        result = await ab_test_manager.create_test(
            test_name="Three Way Test",
            landing_page_id="lp_456",
            variants=[
                {"name": "Control", "changes": {}},
                {"name": "Variant A", "changes": {"hero.headline": "New A"}},
                {"name": "Variant B", "changes": {"hero.headline": "New B"}},
            ],
            traffic_split=[34, 33, 33],
            duration_days=14,
            context={"user_id": "user_123"},
        )

        assert result["status"] == "success"
        assert len(result["variant_urls"]) == 3


class TestTrafficDistribution:
    """Tests for traffic distribution (Requirement 6.2)"""

    @pytest.fixture
    def ab_test_manager(self):
        return ABTestManager()

    def test_allocate_traffic_deterministic(self, ab_test_manager):
        """Test that same session_id always gets same variant"""
        traffic_split = [50, 50]
        session_id = "session_abc123"

        # Call multiple times with same session_id
        results = [
            ab_test_manager.allocate_traffic(traffic_split, session_id)
            for _ in range(10)
        ]

        # All results should be the same
        assert len(set(results)) == 1

    def test_allocate_traffic_distribution(self, ab_test_manager):
        """Test that traffic is distributed according to split"""
        traffic_split = [70, 30]

        # Generate many allocations with different session IDs
        allocations = [
            ab_test_manager.allocate_traffic(traffic_split, f"session_{i}")
            for i in range(1000)
        ]

        # Count allocations to each variant
        variant_0_count = allocations.count(0)
        variant_1_count = allocations.count(1)

        # Should be roughly 70/30 (allow 10% tolerance)
        assert 600 <= variant_0_count <= 800
        assert 200 <= variant_1_count <= 400

    def test_allocate_traffic_random_without_session(self, ab_test_manager):
        """Test random allocation when no session_id provided"""
        traffic_split = [50, 50]

        # Generate allocations without session_id
        allocations = [
            ab_test_manager.allocate_traffic(traffic_split, None)
            for _ in range(100)
        ]

        # Should have both variants represented
        assert 0 in allocations
        assert 1 in allocations

    def test_generate_variant_cookie(self, ab_test_manager):
        """Test cookie generation for session consistency"""
        cookie = ab_test_manager.generate_variant_cookie("test_123", 0)

        assert cookie["name"] == "aae_ab_variant"
        assert cookie["value"] == "test_123:0"
        assert cookie["http_only"] is True
        assert cookie["secure"] is True


class TestChiSquareAnalysis:
    """Tests for chi-square statistical analysis (Requirement 6.3)"""

    @pytest.fixture
    def ab_test_manager(self):
        return ABTestManager()

    def test_chi_square_significant_difference(self, ab_test_manager):
        """Test chi-square detects significant difference"""
        # Variant A: 5% conversion, Variant B: 10% conversion
        variant_stats = [
            VariantStats(variant="A", visits=1000, conversions=50, conversion_rate=5.0),
            VariantStats(variant="B", visits=1000, conversions=100, conversion_rate=10.0),
        ]

        result = ab_test_manager.chi_square_test(variant_stats)

        assert result.is_significant is True
        assert result.p_value < 0.05
        assert result.chi_square > 0

    def test_chi_square_no_significant_difference(self, ab_test_manager):
        """Test chi-square when no significant difference"""
        # Both variants have similar conversion rates
        variant_stats = [
            VariantStats(variant="A", visits=1000, conversions=100, conversion_rate=10.0),
            VariantStats(variant="B", visits=1000, conversions=102, conversion_rate=10.2),
        ]

        result = ab_test_manager.chi_square_test(variant_stats)

        assert result.is_significant is False
        assert result.p_value >= 0.05

    def test_chi_square_three_variants(self, ab_test_manager):
        """Test chi-square with three variants"""
        variant_stats = [
            VariantStats(variant="A", visits=1000, conversions=50, conversion_rate=5.0),
            VariantStats(variant="B", visits=1000, conversions=100, conversion_rate=10.0),
            VariantStats(variant="C", visits=1000, conversions=150, conversion_rate=15.0),
        ]

        result = ab_test_manager.chi_square_test(variant_stats)

        # Should detect significant difference
        assert result.is_significant is True
        assert result.p_value < 0.05


class TestWinnerIdentification:
    """Tests for winner identification (Requirements 6.4, 6.5)"""

    @pytest.fixture
    def ab_test_manager(self):
        mcp_client = AsyncMock()
        return ABTestManager(mcp_client=mcp_client)

    @pytest.mark.asyncio
    async def test_analyze_identifies_winner(self, ab_test_manager):
        """Test that analysis identifies winner when significant"""
        # Mock test data with significant difference
        # Both variants need >= 100 conversions for valid analysis
        ab_test_manager._get_test_data = AsyncMock(return_value={
            "test_id": "test_123",
            "variant_stats": [
                {"variant": "A", "visits": 2000, "conversions": 100},
                {"variant": "B", "visits": 2000, "conversions": 300},
            ],
        })

        result = await ab_test_manager.analyze_test(
            test_id="test_123",
            context={"user_id": "user_123"},
        )

        assert result.winner is not None
        assert result.winner.variant == "B"
        assert result.is_significant is True
        assert result.winner.confidence > 95

    @pytest.mark.asyncio
    async def test_analyze_insufficient_samples(self, ab_test_manager):
        """Test that analysis returns insufficient data message"""
        # Mock test data with insufficient conversions
        ab_test_manager._get_test_data = AsyncMock(return_value={
            "test_id": "test_123",
            "variant_stats": [
                {"variant": "A", "visits": 100, "conversions": 5},
                {"variant": "B", "visits": 100, "conversions": 10},
            ],
        })

        result = await ab_test_manager.analyze_test(
            test_id="test_123",
            context={"user_id": "user_123"},
        )

        assert result.winner is None
        assert result.is_significant is False
        assert "数据不足" in result.recommendation

    @pytest.mark.asyncio
    async def test_analyze_no_significant_difference(self, ab_test_manager):
        """Test analysis when no significant difference"""
        # Mock test data with similar performance
        ab_test_manager._get_test_data = AsyncMock(return_value={
            "test_id": "test_123",
            "variant_stats": [
                {"variant": "A", "visits": 1000, "conversions": 100},
                {"variant": "B", "visits": 1000, "conversions": 102},
            ],
        })

        result = await ab_test_manager.analyze_test(
            test_id="test_123",
            context={"user_id": "user_123"},
        )

        assert result.winner is None
        assert result.is_significant is False


class TestRecommendationGeneration:
    """Tests for recommendation generation (Requirement 6.6)"""

    @pytest.fixture
    def ab_test_manager(self):
        return ABTestManager()

    def test_recommendation_with_winner(self, ab_test_manager):
        """Test recommendation when winner is identified"""
        from app.modules.landing_page.models import ABTestWinner, ChiSquareResult

        results = [
            VariantStats(variant="A", visits=1000, conversions=50, conversion_rate=5.0),
            VariantStats(variant="B", visits=1000, conversions=100, conversion_rate=10.0),
        ]
        winner = ABTestWinner(variant="B", confidence=95.0, improvement="+100%")
        chi_result = ChiSquareResult(chi_square=25.0, p_value=0.001, is_significant=True)

        recommendation = ab_test_manager._generate_recommendation(
            results, winner, chi_result
        )

        assert "B" in recommendation
        assert "主版本" in recommendation

    def test_recommendation_without_winner(self, ab_test_manager):
        """Test recommendation when no winner"""
        from app.modules.landing_page.models import ChiSquareResult

        results = [
            VariantStats(variant="A", visits=1000, conversions=100, conversion_rate=10.0),
            VariantStats(variant="B", visits=1000, conversions=102, conversion_rate=10.2),
        ]
        chi_result = ChiSquareResult(chi_square=0.1, p_value=0.75, is_significant=False)

        recommendation = ab_test_manager._generate_recommendation(
            results, None, chi_result
        )

        assert "继续测试" in recommendation or "任一版本" in recommendation

