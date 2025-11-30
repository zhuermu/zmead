"""
Property-based tests for Performance Analysis.

**Feature: ad-performance, Property 5: Performance analysis result completeness**
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
"""

import pytest
from datetime import date, timedelta
from hypothesis import given, settings, HealthCheck, assume
import hypothesis.strategies as st
from unittest.mock import AsyncMock

from app.modules.ad_performance.analyzers import PerformanceAnalyzer, AIAnalyzer
from app.modules.ad_performance.models import (
    PerformanceAnalysis,
    PeriodMetrics,
    MetricChange,
    AIAnalysis,
)


# Strategy for generating valid entity types
entity_type_strategy = st.sampled_from(["campaign", "adset", "ad"])

# Strategy for generating entity IDs
entity_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd")),
    min_size=1,
    max_size=20,
).filter(lambda x: len(x.strip()) > 0)

# Strategy for generating entity names
entity_name_strategy = st.text(min_size=1, max_size=50).filter(
    lambda x: len(x.strip()) > 0
)

# Strategy for generating valid metrics values
spend_strategy = st.floats(min_value=0, max_value=100000, allow_nan=False)
revenue_strategy = st.floats(min_value=0, max_value=500000, allow_nan=False)
conversions_strategy = st.integers(min_value=0, max_value=10000)
impressions_strategy = st.integers(min_value=0, max_value=10000000)
clicks_strategy = st.integers(min_value=0, max_value=100000)


# Strategy for generating a single metric data point
@st.composite
def metric_data_strategy(draw):
    """Generate a single metric data point."""
    spend = draw(spend_strategy)
    revenue = draw(revenue_strategy)
    conversions = draw(conversions_strategy)
    impressions = draw(impressions_strategy)
    clicks = draw(clicks_strategy)
    
    return {
        "spend": spend,
        "revenue": revenue,
        "conversions": conversions,
        "impressions": impressions,
        "clicks": clicks,
        "entity_id": draw(entity_id_strategy),
        "entity_name": draw(entity_name_strategy),
    }


# Strategy for generating a list of metric data points
metrics_list_strategy = st.lists(metric_data_strategy(), min_size=0, max_size=10)


class TestPerformanceAnalyzerProperties:
    """Property tests for PerformanceAnalyzer."""

    @given(
        entity_type=entity_type_strategy,
        entity_id=entity_id_strategy,
        entity_name=entity_name_strategy,
        current_data=metrics_list_strategy,
        historical_data=metrics_list_strategy,
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @pytest.mark.asyncio
    async def test_property_5_performance_analysis_result_completeness(
        self,
        entity_type,
        entity_id,
        entity_name,
        current_data,
        historical_data,
    ):
        """
        **Feature: ad-performance, Property 5: Performance analysis result completeness**

        For any entity (campaign/adset/ad) and date range, calling analyze_performance
        should return a result containing:
        - current_period with spend, revenue, roas, conversions, cpa
        - previous_period with spend, revenue, roas, conversions, cpa
        - changes with percentage format strings
        - insights list

        **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
        """
        # Arrange
        analyzer = PerformanceAnalyzer()
        
        # Act
        result = await analyzer.analyze_entity(
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            current_data=current_data,
            historical_data=historical_data,
        )
        
        # Assert: Result is a PerformanceAnalysis
        assert isinstance(result, PerformanceAnalysis), (
            "Result should be a PerformanceAnalysis instance"
        )
        
        # Assert: Entity info is correct
        assert result.entity_id == entity_id, "entity_id should match input"
        assert result.entity_name == entity_name, "entity_name should match input"
        
        # Assert: current_period has all required fields
        assert isinstance(result.current_period, PeriodMetrics), (
            "current_period should be PeriodMetrics"
        )
        assert hasattr(result.current_period, "spend"), "current_period should have spend"
        assert hasattr(result.current_period, "revenue"), "current_period should have revenue"
        assert hasattr(result.current_period, "roas"), "current_period should have roas"
        assert hasattr(result.current_period, "conversions"), (
            "current_period should have conversions"
        )
        assert hasattr(result.current_period, "cpa"), "current_period should have cpa"
        
        # Assert: previous_period has all required fields
        assert isinstance(result.previous_period, PeriodMetrics), (
            "previous_period should be PeriodMetrics"
        )
        assert hasattr(result.previous_period, "spend"), "previous_period should have spend"
        assert hasattr(result.previous_period, "revenue"), "previous_period should have revenue"
        assert hasattr(result.previous_period, "roas"), "previous_period should have roas"
        assert hasattr(result.previous_period, "conversions"), (
            "previous_period should have conversions"
        )
        assert hasattr(result.previous_period, "cpa"), "previous_period should have cpa"
        
        # Assert: changes has all required fields with percentage format
        assert isinstance(result.changes, MetricChange), "changes should be MetricChange"
        assert hasattr(result.changes, "spend"), "changes should have spend"
        assert hasattr(result.changes, "revenue"), "changes should have revenue"
        assert hasattr(result.changes, "roas"), "changes should have roas"
        assert hasattr(result.changes, "conversions"), "changes should have conversions"
        assert hasattr(result.changes, "cpa"), "changes should have cpa"
        
        # Assert: changes are in percentage format (e.g., "+4.2%" or "-10.5%" or "N/A")
        for field in ["spend", "revenue", "roas", "conversions", "cpa"]:
            change_value = getattr(result.changes, field)
            assert isinstance(change_value, str), f"changes.{field} should be a string"
            assert (
                change_value == "N/A" or 
                change_value.endswith("%")
            ), f"changes.{field} should be percentage format or N/A, got {change_value}"
        
        # Assert: insights is a list
        assert isinstance(result.insights, list), "insights should be a list"
        for insight in result.insights:
            assert isinstance(insight, str), "Each insight should be a string"

    @given(
        current_spend=st.floats(min_value=0.01, max_value=100000, allow_nan=False, allow_infinity=False),
        current_revenue=st.floats(min_value=0, max_value=500000, allow_nan=False, allow_infinity=False),
        current_conversions=conversions_strategy,
        previous_spend=st.floats(min_value=0.01, max_value=100000, allow_nan=False, allow_infinity=False),
        previous_revenue=st.floats(min_value=0, max_value=500000, allow_nan=False, allow_infinity=False),
        previous_conversions=conversions_strategy,
    )
    @settings(max_examples=100)
    def test_period_metrics_calculation_consistency(
        self,
        current_spend,
        current_revenue,
        current_conversions,
        previous_spend,
        previous_revenue,
        previous_conversions,
    ):
        """
        Test that period metrics are calculated consistently.
        
        For any valid metrics, the calculated ROAS and CPA should be consistent
        with the formula: ROAS = revenue/spend, CPA = spend/conversions.
        
        Note: We use min_value=0.01 for spend to avoid division by very small
        numbers that would produce infinity.
        """
        # Arrange
        analyzer = PerformanceAnalyzer()
        
        current_data = [{
            "spend": current_spend,
            "revenue": current_revenue,
            "conversions": current_conversions,
        }]
        
        # Act
        metrics = analyzer._calculate_period_metrics(current_data)
        
        # Assert: ROAS calculation is correct
        if current_spend > 0:
            expected_roas = current_revenue / current_spend
            # Use relative tolerance for large values
            if expected_roas > 0:
                assert abs(metrics.roas - expected_roas) / max(expected_roas, 1) < 0.0001, (
                    f"ROAS should be {expected_roas}, got {metrics.roas}"
                )
            else:
                assert abs(metrics.roas - expected_roas) < 0.0001, (
                    f"ROAS should be {expected_roas}, got {metrics.roas}"
                )
        else:
            assert metrics.roas == 0.0, "ROAS should be 0 when spend is 0"
        
        # Assert: CPA calculation is correct
        if current_conversions > 0:
            expected_cpa = current_spend / current_conversions
            # Use relative tolerance for large values
            if expected_cpa > 0:
                assert abs(metrics.cpa - expected_cpa) / max(expected_cpa, 1) < 0.0001, (
                    f"CPA should be {expected_cpa}, got {metrics.cpa}"
                )
            else:
                assert abs(metrics.cpa - expected_cpa) < 0.0001, (
                    f"CPA should be {expected_cpa}, got {metrics.cpa}"
                )
        else:
            assert metrics.cpa == 0.0, "CPA should be 0 when conversions is 0"

    @given(
        current_value=st.floats(min_value=0.01, max_value=100000, allow_nan=False),
        previous_value=st.floats(min_value=0.01, max_value=100000, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_percentage_change_format(self, current_value, previous_value):
        """
        Test that percentage changes are formatted correctly.
        
        For any two positive values, the change should be formatted as "+X.X%" or "-X.X%".
        """
        # Arrange
        analyzer = PerformanceAnalyzer()
        
        # Act
        change = analyzer._format_percentage_change(current_value, previous_value)
        
        # Assert: Format is correct
        assert isinstance(change, str), "Change should be a string"
        assert change.endswith("%"), f"Change should end with %, got {change}"
        
        # Assert: Sign is correct
        expected_change = ((current_value - previous_value) / previous_value) * 100
        if expected_change > 0:
            assert change.startswith("+"), f"Positive change should start with +, got {change}"
        elif expected_change < 0:
            assert change.startswith("-"), f"Negative change should start with -, got {change}"

    @given(
        start_date=st.dates(min_value=date(2024, 2, 1), max_value=date(2024, 11, 30)),
        end_date=st.dates(min_value=date(2024, 2, 1), max_value=date(2024, 11, 30)),
        comparison_period=st.sampled_from(["previous_week", "previous_month"]),
    )
    @settings(max_examples=100)
    def test_comparison_date_range_calculation(
        self, start_date, end_date, comparison_period
    ):
        """
        Test that comparison date ranges are calculated correctly.
        
        The comparison period should always be before the current period.
        """
        # Ensure start_date <= end_date
        if end_date < start_date:
            start_date, end_date = end_date, start_date
        
        # Act
        comp_start, comp_end = PerformanceAnalyzer.get_comparison_date_range(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            comparison_period=comparison_period,
        )
        
        # Assert: Comparison period is before current period
        comp_end_date = date.fromisoformat(comp_end)
        assert comp_end_date < start_date, (
            f"Comparison end {comp_end} should be before current start {start_date}"
        )
        
        # Assert: Comparison dates are valid
        comp_start_date = date.fromisoformat(comp_start)
        assert comp_start_date <= comp_end_date, (
            f"Comparison start {comp_start} should be <= end {comp_end}"
        )


class TestAIAnalyzerProperties:
    """Property tests for AIAnalyzer with mocked Gemini client."""

    @given(
        spend=spend_strategy,
        revenue=revenue_strategy,
        conversions=conversions_strategy,
    )
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @pytest.mark.asyncio
    async def test_ai_analyzer_returns_valid_analysis(
        self, spend, revenue, conversions
    ):
        """
        Test that AIAnalyzer returns valid AIAnalysis structure.
        
        For any valid metrics, the AI analyzer should return an AIAnalysis
        with key_insights (list of strings) and trends (dict).
        """
        # Arrange
        mock_gemini = AsyncMock()
        mock_gemini.structured_output = AsyncMock(side_effect=Exception("Mock error"))
        mock_gemini.chat_completion = AsyncMock(
            return_value='{"key_insights": ["Test insight"], "trends": {"roas_trend": "stable"}}'
        )
        
        analyzer = AIAnalyzer(gemini_client=mock_gemini)
        
        # Calculate derived metrics
        roas = revenue / spend if spend > 0 else 0.0
        cpa = spend / conversions if conversions > 0 else 0.0
        
        current_period = PeriodMetrics(
            spend=spend,
            revenue=revenue,
            roas=roas,
            conversions=conversions,
            cpa=cpa,
        )
        
        previous_period = PeriodMetrics(
            spend=spend * 0.9,
            revenue=revenue * 0.9,
            roas=roas,
            conversions=max(0, conversions - 1),
            cpa=cpa,
        )
        
        changes = MetricChange(
            spend="+10.0%",
            revenue="+10.0%",
            roas="0.0%",
            conversions="+5.0%",
            cpa="+5.0%",
        )
        
        # Act
        result = await analyzer.analyze_metrics(
            current_period=current_period,
            previous_period=previous_period,
            changes=changes,
        )
        
        # Assert: Result is AIAnalysis
        assert isinstance(result, AIAnalysis), "Result should be AIAnalysis"
        
        # Assert: key_insights is a list of strings
        assert isinstance(result.key_insights, list), "key_insights should be a list"
        for insight in result.key_insights:
            assert isinstance(insight, str), "Each insight should be a string"
        
        # Assert: trends is a dict
        assert isinstance(result.trends, dict), "trends should be a dict"

    @given(
        change_str=st.sampled_from([
            "+10.5%", "-5.2%", "0.0%", "+100.0%", "-50.0%", "N/A"
        ])
    )
    @settings(max_examples=100)
    def test_determine_trend_consistency(self, change_str):
        """
        Test that trend determination is consistent.
        
        For any change string, the trend should be one of:
        "improving", "declining", or "stable".
        """
        # Arrange
        analyzer = AIAnalyzer(gemini_client=AsyncMock())
        
        # Act
        trend = analyzer._determine_trend(change_str)
        
        # Assert: Trend is valid
        assert trend in ["improving", "declining", "stable"], (
            f"Trend should be improving/declining/stable, got {trend}"
        )
        
        # Assert: Trend matches change direction
        if change_str == "N/A":
            assert trend == "stable", "N/A should result in stable trend"
        else:
            try:
                change_val = float(change_str.replace("%", ""))
                if change_val > 5:
                    assert trend == "improving", f"Change {change_str} should be improving"
                elif change_val < -5:
                    assert trend == "declining", f"Change {change_str} should be declining"
                else:
                    assert trend == "stable", f"Change {change_str} should be stable"
            except ValueError:
                pass  # Invalid format, trend can be anything
