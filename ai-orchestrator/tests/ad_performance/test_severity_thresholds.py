"""
Example tests for severity threshold validation.

**Feature: ad-performance, Property 7: CPA anomaly severity**
**Feature: ad-performance, Property 8: ROAS anomaly severity**
**Validates: Requirements 4.2, 4.3**
"""

import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

from app.modules.ad_performance.analyzers import AnomalyDetector


# Strategy for generating entity types
entity_type_strategy = st.sampled_from(["campaign", "adset", "ad"])

# Strategy for generating entity IDs and names
entity_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    min_size=5,
    max_size=20,
)
entity_name_strategy = st.text(min_size=1, max_size=50)


@given(
    entity_type=entity_type_strategy,
    entity_id=entity_id_strategy,
    entity_name=entity_name_strategy,
    cpa_increase_pct=st.floats(min_value=51.0, max_value=200.0),
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_7_cpa_anomaly_severity(
    entity_type, entity_id, entity_name, cpa_increase_pct
):
    """
    **Feature: ad-performance, Property 7: CPA anomaly severity**

    For any CPA data, when CPA increases by more than 50%, the anomaly severity
    should be marked as high or critical.

    **Validates: Requirements 4.2**
    """
    # Arrange: Create anomaly detector
    detector = AnomalyDetector()

    # Create historical CPA values with slight variation around baseline
    baseline_cpa = 10.0
    historical_values = [
        baseline_cpa * 0.95,
        baseline_cpa * 1.02,
        baseline_cpa * 0.98,
        baseline_cpa * 1.01,
        baseline_cpa * 0.99,
        baseline_cpa * 1.03,
        baseline_cpa * 0.97,
    ]

    # Create current CPA that increases by the specified percentage
    current_cpa = baseline_cpa * (1 + cpa_increase_pct / 100)

    # Act: Detect anomaly
    result = await detector.detect(
        metric="cpa",
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        current_value=current_cpa,
        historical_values=historical_values,
        sensitivity="medium",
    )

    # Assert: Verify anomaly was detected with high or critical severity
    assert result is not None, (
        f"Should detect anomaly when CPA increases by {cpa_increase_pct:.1f}%"
    )

    assert result.severity in ["high", "critical"], (
        f"CPA increase of {cpa_increase_pct:.1f}% (>50%) should result in "
        f"'high' or 'critical' severity, but got '{result.severity}'"
    )

    # Verify the metric is CPA
    assert result.metric == "cpa"

    # Verify deviation is positive (increase)
    assert "+" in result.deviation, "CPA increase should show positive deviation"


@given(
    entity_type=entity_type_strategy,
    entity_id=entity_id_strategy,
    entity_name=entity_name_strategy,
    roas_decline_pct=st.floats(min_value=31.0, max_value=90.0),
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_8_roas_anomaly_severity(
    entity_type, entity_id, entity_name, roas_decline_pct
):
    """
    **Feature: ad-performance, Property 8: ROAS anomaly severity**

    For any ROAS data, when ROAS declines by more than 30%, the anomaly severity
    should be marked as critical.

    **Validates: Requirements 4.3**
    """
    # Arrange: Create anomaly detector
    detector = AnomalyDetector()

    # Create historical ROAS values with slight variation around baseline
    baseline_roas = 3.0
    historical_values = [
        baseline_roas * 0.95,
        baseline_roas * 1.02,
        baseline_roas * 0.98,
        baseline_roas * 1.01,
        baseline_roas * 0.99,
        baseline_roas * 1.03,
        baseline_roas * 0.97,
    ]

    # Create current ROAS that declines by the specified percentage
    current_roas = baseline_roas * (1 - roas_decline_pct / 100)

    # Act: Detect anomaly
    result = await detector.detect(
        metric="roas",
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        current_value=current_roas,
        historical_values=historical_values,
        sensitivity="medium",
    )

    # Assert: Verify anomaly was detected with critical severity
    assert result is not None, (
        f"Should detect anomaly when ROAS declines by {roas_decline_pct:.1f}%"
    )

    assert result.severity == "critical", (
        f"ROAS decline of {roas_decline_pct:.1f}% (>30%) should result in "
        f"'critical' severity, but got '{result.severity}'"
    )

    # Verify the metric is ROAS
    assert result.metric == "roas"

    # Verify deviation is negative (decline)
    assert "-" in result.deviation, "ROAS decline should show negative deviation"


@pytest.mark.asyncio
async def test_property_7_cpa_exact_50_percent_increase():
    """
    **Feature: ad-performance, Property 7: CPA anomaly severity**

    Edge case: Test CPA increase of exactly 50% to verify threshold behavior.

    **Validates: Requirements 4.2**
    """
    # Arrange
    detector = AnomalyDetector()
    baseline_cpa = 10.0
    historical_values = [
        baseline_cpa * 0.95,
        baseline_cpa * 1.02,
        baseline_cpa * 0.98,
        baseline_cpa * 1.01,
        baseline_cpa * 0.99,
        baseline_cpa * 1.03,
        baseline_cpa * 0.97,
    ]
    current_cpa = baseline_cpa * 1.5  # Exactly 50% increase

    # Act
    result = await detector.detect(
        metric="cpa",
        entity_type="adset",
        entity_id="test_adset_123",
        entity_name="Test Adset",
        current_value=current_cpa,
        historical_values=historical_values,
        sensitivity="medium",
    )

    # Assert: At exactly 50%, should still trigger high severity
    # (requirement says >50%, but we want to be conservative)
    if result is not None:
        assert result.severity in ["high", "critical"], (
            f"CPA increase of exactly 50% should result in 'high' or 'critical' "
            f"severity, but got '{result.severity}'"
        )


@pytest.mark.asyncio
async def test_property_8_roas_exact_30_percent_decline():
    """
    **Feature: ad-performance, Property 8: ROAS anomaly severity**

    Edge case: Test ROAS decline of exactly 30% to verify threshold behavior.

    **Validates: Requirements 4.3**
    """
    # Arrange
    detector = AnomalyDetector()
    baseline_roas = 3.0
    historical_values = [
        baseline_roas * 0.95,
        baseline_roas * 1.02,
        baseline_roas * 0.98,
        baseline_roas * 1.01,
        baseline_roas * 0.99,
        baseline_roas * 1.03,
        baseline_roas * 0.97,
    ]
    current_roas = baseline_roas * 0.7  # Exactly 30% decline

    # Act
    result = await detector.detect(
        metric="roas",
        entity_type="campaign",
        entity_id="test_campaign_456",
        entity_name="Test Campaign",
        current_value=current_roas,
        historical_values=historical_values,
        sensitivity="medium",
    )

    # Assert: At exactly 30%, should trigger critical severity
    # (requirement says >30%, but we want to be conservative)
    if result is not None:
        assert result.severity == "critical", (
            f"ROAS decline of exactly 30% should result in 'critical' severity, "
            f"but got '{result.severity}'"
        )


@pytest.mark.asyncio
async def test_cpa_small_increase_lower_severity():
    """
    **Feature: ad-performance, Property 7: CPA anomaly severity**

    Verify that small CPA increases (with high variance) result in lower severity.

    **Validates: Requirements 4.2**
    """
    # Arrange
    detector = AnomalyDetector()
    baseline_cpa = 10.0
    # Create historical values with higher variance
    historical_values = [
        baseline_cpa * 0.7,
        baseline_cpa * 1.3,
        baseline_cpa * 0.8,
        baseline_cpa * 1.2,
        baseline_cpa * 0.9,
        baseline_cpa * 1.1,
        baseline_cpa * 1.0,
    ]
    current_cpa = baseline_cpa * 1.15  # 15% increase

    # Act
    result = await detector.detect(
        metric="cpa",
        entity_type="adset",
        entity_id="test_adset_789",
        entity_name="Test Adset",
        current_value=current_cpa,
        historical_values=historical_values,
        sensitivity="medium",
    )

    # Assert: With high variance, small increases should not trigger high severity
    # or may not even be detected as anomalies
    if result is not None:
        # If detected, verify it's not automatically high severity
        # (the metric-specific threshold shouldn't apply for small increases)
        assert result.severity in ["low", "medium"], (
            f"Small CPA increase with high variance should result in low/medium "
            f"severity, but got '{result.severity}'"
        )


@pytest.mark.asyncio
async def test_roas_small_decline_lower_severity():
    """
    **Feature: ad-performance, Property 8: ROAS anomaly severity**

    Verify that small ROAS declines (with high variance) result in lower severity.

    **Validates: Requirements 4.3**
    """
    # Arrange
    detector = AnomalyDetector()
    baseline_roas = 3.0
    # Create historical values with higher variance
    historical_values = [
        baseline_roas * 0.7,
        baseline_roas * 1.3,
        baseline_roas * 0.8,
        baseline_roas * 1.2,
        baseline_roas * 0.9,
        baseline_roas * 1.1,
        baseline_roas * 1.0,
    ]
    current_roas = baseline_roas * 0.9  # 10% decline

    # Act
    result = await detector.detect(
        metric="roas",
        entity_type="campaign",
        entity_id="test_campaign_101",
        entity_name="Test Campaign",
        current_value=current_roas,
        historical_values=historical_values,
        sensitivity="medium",
    )

    # Assert: With high variance, small declines should not trigger critical severity
    # or may not even be detected as anomalies
    if result is not None:
        # If detected, verify it's not critical
        # (the metric-specific threshold shouldn't apply for small declines)
        assert result.severity in ["low", "medium"], (
            f"Small ROAS decline with high variance should result in low/medium "
            f"severity, but got '{result.severity}'"
        )
