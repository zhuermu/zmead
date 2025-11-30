"""
Property-based tests for anomaly detection.

**Feature: ad-performance, Property 6: Anomaly detection identification**
**Validates: Requirements 4.1, 4.4, 4.5**
"""

import pytest
from datetime import datetime
from hypothesis import given, settings, assume
import hypothesis.strategies as st
import numpy as np

from app.modules.ad_performance.analyzers import AnomalyDetector


# Strategy for generating valid metrics
metric_strategy = st.sampled_from(["roas", "cpa", "ctr"])

# Strategy for generating entity types
entity_type_strategy = st.sampled_from(["campaign", "adset", "ad"])

# Strategy for generating entity IDs and names
entity_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    min_size=5,
    max_size=20,
)
entity_name_strategy = st.text(min_size=1, max_size=50)

# Strategy for generating sensitivity levels
sensitivity_strategy = st.sampled_from(["low", "medium", "high"])

# Strategy for generating historical values (positive floats)
historical_values_strategy = st.lists(
    st.floats(min_value=0.1, max_value=1000.0, allow_nan=False, allow_infinity=False),
    min_size=3,
    max_size=30,
)


@given(
    metric=metric_strategy,
    entity_type=entity_type_strategy,
    entity_id=entity_id_strategy,
    entity_name=entity_name_strategy,
    historical_values=historical_values_strategy,
    sensitivity=sensitivity_strategy,
    deviation_multiplier=st.floats(min_value=3.5, max_value=10.0),
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_6_anomaly_detection_identification(
    metric,
    entity_type,
    entity_id,
    entity_name,
    historical_values,
    sensitivity,
    deviation_multiplier,
):
    """
    **Feature: ad-performance, Property 6: Anomaly detection identification**

    For any metric data, when the current value deviates from the historical mean
    beyond the threshold, detect_anomalies should identify it as an anomaly and
    return data containing deviation, severity, and recommendation.

    **Validates: Requirements 4.1, 4.4, 4.5**
    """
    # Arrange: Create anomaly detector
    detector = AnomalyDetector()

    # Calculate mean and std from historical values
    mean = float(np.mean(historical_values))
    std = float(np.std(historical_values))

    # Skip if std is too small (no variation in data)
    assume(std > 0.01)

    # Create an anomalous current value by deviating significantly from mean
    # Use deviation_multiplier (>= 3.5) to ensure it exceeds all sensitivity thresholds
    # (low=3.0, medium=2.5, high=2.0)
    current_value = mean + (std * deviation_multiplier)

    # Act: Detect anomaly
    result = await detector.detect(
        metric=metric,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        current_value=current_value,
        historical_values=historical_values,
        sensitivity=sensitivity,
    )

    # Assert: Verify anomaly was detected
    assert result is not None, (
        f"Should detect anomaly when current value ({current_value:.2f}) "
        f"deviates {deviation_multiplier:.2f} std devs from mean ({mean:.2f})"
    )

    # Verify anomaly structure contains required fields
    assert hasattr(result, "metric"), "Anomaly should have metric field"
    assert hasattr(result, "entity_type"), "Anomaly should have entity_type field"
    assert hasattr(result, "entity_id"), "Anomaly should have entity_id field"
    assert hasattr(result, "entity_name"), "Anomaly should have entity_name field"
    assert hasattr(result, "current_value"), "Anomaly should have current_value field"
    assert hasattr(result, "expected_value"), (
        "Anomaly should have expected_value field"
    )
    assert hasattr(result, "deviation"), "Anomaly should have deviation field"
    assert hasattr(result, "severity"), "Anomaly should have severity field"
    assert hasattr(result, "recommendation"), (
        "Anomaly should have recommendation field"
    )

    # Verify field values
    assert result.metric == metric
    assert result.entity_type == entity_type
    assert result.entity_id == entity_id
    assert result.entity_name == entity_name
    assert result.current_value == current_value

    # Verify expected_value is close to historical mean
    assert abs(result.expected_value - mean) < 0.01, (
        f"Expected value ({result.expected_value}) should be close to mean ({mean})"
    )

    # Verify deviation is a percentage string
    assert isinstance(result.deviation, str), "Deviation should be a string"
    assert "%" in result.deviation, "Deviation should contain '%' symbol"

    # Verify severity is valid
    assert result.severity in ["low", "medium", "high", "critical"], (
        f"Severity should be valid level, got {result.severity}"
    )

    # Verify recommendation is not empty
    assert isinstance(result.recommendation, str), "Recommendation should be a string"
    assert len(result.recommendation) > 0, "Recommendation should not be empty"


@given(
    metric=metric_strategy,
    entity_type=entity_type_strategy,
    entity_id=entity_id_strategy,
    entity_name=entity_name_strategy,
    historical_values=historical_values_strategy,
    sensitivity=sensitivity_strategy,
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_6_no_anomaly_when_within_threshold(
    metric,
    entity_type,
    entity_id,
    entity_name,
    historical_values,
    sensitivity,
):
    """
    **Feature: ad-performance, Property 6: Anomaly detection identification**

    For any metric data, when the current value is within the normal range
    (within threshold), detect_anomalies should NOT identify it as an anomaly.

    **Validates: Requirements 4.1, 4.4, 4.5**
    """
    # Arrange: Create anomaly detector
    detector = AnomalyDetector()

    # Calculate mean from historical values
    mean = float(np.mean(historical_values))
    std = float(np.std(historical_values))

    # Skip if std is too small
    assume(std > 0.01)

    # Create a normal current value (within 1 std dev of mean)
    current_value = mean + (std * 0.5)

    # Act: Detect anomaly
    result = await detector.detect(
        metric=metric,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        current_value=current_value,
        historical_values=historical_values,
        sensitivity=sensitivity,
    )

    # Assert: Verify no anomaly was detected
    assert result is None, (
        f"Should NOT detect anomaly when current value ({current_value:.2f}) "
        f"is within normal range (mean={mean:.2f}, std={std:.2f})"
    )


@given(
    metric=metric_strategy,
    entity_type=entity_type_strategy,
    entity_id=entity_id_strategy,
    entity_name=entity_name_strategy,
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_property_6_insufficient_data_returns_none(
    metric, entity_type, entity_id, entity_name
):
    """
    **Feature: ad-performance, Property 6: Anomaly detection identification**

    For any metric data, when there is insufficient historical data (< 3 points),
    detect_anomalies should return None.

    **Validates: Requirements 4.1, 4.4, 4.5**
    """
    # Arrange: Create anomaly detector
    detector = AnomalyDetector()

    # Create insufficient historical data (< 3 points)
    historical_values = [10.0, 20.0]
    current_value = 100.0

    # Act: Detect anomaly
    result = await detector.detect(
        metric=metric,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        current_value=current_value,
        historical_values=historical_values,
        sensitivity="medium",
    )

    # Assert: Verify None is returned
    assert result is None, (
        "Should return None when historical data has fewer than 3 points"
    )
