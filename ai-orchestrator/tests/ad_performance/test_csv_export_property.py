"""
Property-based tests for CSV export functionality.

**Feature: ad-performance, Property 13: CSV export data completeness**
**Validates: Requirements 6.1, 6.2**
"""

import pytest
import pandas as pd
import os
from datetime import date
from hypothesis import given, settings, HealthCheck
import hypothesis.strategies as st

from app.modules.ad_performance.exporters import CSVExporter


# Strategy for generating valid metrics data
@st.composite
def metrics_data_strategy(draw):
    """Generate valid metrics data for CSV export."""
    num_metrics = draw(st.integers(min_value=1, max_value=20))

    metrics = []
    for _ in range(num_metrics):
        metric = {
            "entity_id": draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")))),
            "entity_name": draw(st.text(min_size=1, max_size=100)),
            "entity_type": draw(st.sampled_from(["campaign", "adset", "ad"])),
            "platform": draw(st.sampled_from(["meta", "tiktok", "google"])),
            "date": draw(st.dates(min_value=date(2024, 1, 1), max_value=date(2024, 12, 31))).isoformat(),
            "spend": draw(st.floats(min_value=0, max_value=100000, allow_nan=False, allow_infinity=False)),
            "revenue": draw(st.floats(min_value=0, max_value=500000, allow_nan=False, allow_infinity=False)),
            "roas": draw(st.floats(min_value=0, max_value=20, allow_nan=False, allow_infinity=False)),
            "conversions": draw(st.integers(min_value=0, max_value=10000)),
            "cpa": draw(st.floats(min_value=0, max_value=1000, allow_nan=False, allow_infinity=False)),
            "impressions": draw(st.integers(min_value=0, max_value=10000000)),
            "clicks": draw(st.integers(min_value=0, max_value=100000)),
            "ctr": draw(st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False)),
        }
        metrics.append(metric)

    return {"metrics": metrics}


@given(data=metrics_data_strategy())
@settings(
    max_examples=100,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None,
)
@pytest.mark.asyncio
async def test_property_13_csv_export_data_completeness(data):
    """
    **Feature: ad-performance, Property 13: CSV export data completeness**

    For any report data, the exported CSV file should contain all data rows
    and columns, and the data should be consistent with the original data.

    **Validates: Requirements 6.1, 6.2**
    """
    # Arrange
    exporter = CSVExporter()
    original_metrics = data["metrics"]
    original_count = len(original_metrics)

    # Act: Export to CSV
    file_path = await exporter.export(data)

    try:
        # Assert: File should exist
        assert os.path.exists(file_path), f"CSV file should exist at {file_path}"

        # Read the CSV file back
        df = pd.read_csv(file_path)

        # Assert: Row count should match
        assert len(df) == original_count, (
            f"CSV should have {original_count} rows, got {len(df)}"
        )

        # Assert: All required columns should exist
        required_columns = [
            "entity_id",
            "entity_name",
            "entity_type",
            "platform",
            "date",
            "spend",
            "revenue",
            "roas",
            "conversions",
            "cpa",
        ]

        for col in required_columns:
            assert col in df.columns, f"CSV should contain column '{col}'"

        # Assert: Data consistency - verify each row
        for idx, original_metric in enumerate(original_metrics):
            csv_row = df.iloc[idx]

            # Check string fields (convert to string for comparison to handle numeric strings)
            assert str(csv_row["entity_id"]) == str(original_metric["entity_id"]), (
                f"Row {idx}: entity_id mismatch"
            )
            assert str(csv_row["entity_name"]) == str(original_metric["entity_name"]), (
                f"Row {idx}: entity_name mismatch"
            )
            assert str(csv_row["entity_type"]) == str(original_metric["entity_type"]), (
                f"Row {idx}: entity_type mismatch"
            )
            assert str(csv_row["platform"]) == str(original_metric["platform"]), (
                f"Row {idx}: platform mismatch"
            )
            assert str(csv_row["date"]) == str(original_metric["date"]), (
                f"Row {idx}: date mismatch"
            )

            # Check numeric fields (with tolerance for floating point)
            assert abs(csv_row["spend"] - original_metric["spend"]) < 0.01, (
                f"Row {idx}: spend mismatch"
            )
            assert abs(csv_row["revenue"] - original_metric["revenue"]) < 0.01, (
                f"Row {idx}: revenue mismatch"
            )
            assert abs(csv_row["roas"] - original_metric["roas"]) < 0.01, (
                f"Row {idx}: roas mismatch"
            )
            assert csv_row["conversions"] == original_metric["conversions"], (
                f"Row {idx}: conversions mismatch"
            )
            assert abs(csv_row["cpa"] - original_metric["cpa"]) < 0.01, (
                f"Row {idx}: cpa mismatch"
            )

        # Assert: Data completeness validation should pass
        assert exporter.validate_data_completeness(data), (
            "Data completeness validation should pass"
        )

    finally:
        # Cleanup: Remove the test file
        if os.path.exists(file_path):
            os.remove(file_path)


@pytest.mark.asyncio
async def test_csv_export_with_empty_data_fails():
    """Test that CSV export fails with empty data."""
    exporter = CSVExporter()

    with pytest.raises(ValueError, match="Metrics list cannot be empty"):
        await exporter.export({"metrics": []})


@pytest.mark.asyncio
async def test_csv_export_with_missing_metrics_key_fails():
    """Test that CSV export fails when metrics key is missing."""
    exporter = CSVExporter()

    with pytest.raises(ValueError, match="Data must contain 'metrics' key"):
        await exporter.export({"data": []})


@pytest.mark.asyncio
async def test_csv_export_with_invalid_data_type_fails():
    """Test that CSV export fails with invalid data type."""
    exporter = CSVExporter()

    with pytest.raises(ValueError, match="Data must be a dictionary"):
        await exporter.export([])


@pytest.mark.asyncio
async def test_csv_export_with_missing_required_fields_fails():
    """Test that CSV export fails when required fields are missing."""
    exporter = CSVExporter()

    data = {
        "metrics": [
            {
                "entity_id": "123",
                "entity_name": "Test",
                # Missing other required fields
            }
        ]
    }

    with pytest.raises(ValueError, match="Missing required columns"):
        await exporter.export(data)
