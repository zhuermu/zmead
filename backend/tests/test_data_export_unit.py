"""Unit tests for data export service helper methods."""

from datetime import UTC, datetime
from decimal import Decimal

from app.services.data_export import DataExportService


class TestDataExportHelpers:
    """Test data export helper methods."""

    def test_generate_readme(self) -> None:
        """Test README generation."""
        from app.models.user import User
        
        user = User(
            id=1,
            email="test@example.com",
            display_name="Test User",
            oauth_provider="google",
            oauth_id="google_123",
        )
        
        service = DataExportService(None)  # type: ignore
        readme = service._generate_readme(user)
        
        assert "AAE Data Export" in readme
        assert "test@example.com" in readme
        assert "Test User" in readme
        assert "user_profile.json" in readme

    def test_generate_credit_csv(self) -> None:
        """Test credit CSV generation."""
        service = DataExportService(None)  # type: ignore
        
        transactions = [
            {
                "created_at": "2024-01-01T00:00:00",
                "type": "deduct",
                "amount": 10.0,
                "from_gifted": 10.0,
                "from_purchased": 0.0,
                "balance_after": 90.0,
                "operation_type": "generate_creative",
                "operation_id": "op_123",
                "details": {"model": "imagen"},
            }
        ]
        
        csv_content = service._generate_credit_csv(transactions)
        
        assert "Date,Type,Amount" in csv_content
        assert "deduct" in csv_content
        assert "10.0" in csv_content
        assert "generate_creative" in csv_content

    def test_generate_metrics_csv(self) -> None:
        """Test metrics CSV generation."""
        service = DataExportService(None)  # type: ignore
        
        metrics = [
            {
                "timestamp": "2024-01-01T00:00:00",
                "ad_account_id": 1,
                "entity_type": "campaign",
                "entity_id": "camp_123",
                "entity_name": "Test Campaign",
                "impressions": 1000,
                "clicks": 50,
                "spend": 25.0,
                "conversions": 5,
                "revenue": 100.0,
                "ctr": 5.0,
                "cpc": 0.5,
                "cpa": 5.0,
                "roas": 4.0,
            }
        ]
        
        csv_content = service._generate_metrics_csv(metrics)
        
        assert "Timestamp,Ad Account ID" in csv_content
        assert "campaign" in csv_content
        assert "1000" in csv_content

    def test_generate_performance_summary(self) -> None:
        """Test performance summary generation."""
        service = DataExportService(None)  # type: ignore
        
        metrics = [
            {
                "impressions": 1000,
                "clicks": 50,
                "spend": 25.0,
                "conversions": 5,
                "revenue": 100.0,
            },
            {
                "impressions": 2000,
                "clicks": 100,
                "spend": 50.0,
                "conversions": 10,
                "revenue": 200.0,
            },
        ]
        
        summary = service._generate_performance_summary(metrics)
        
        assert "Total Impressions,3000" in summary
        assert "Total Clicks,150" in summary
        assert "Total Spend,75.00" in summary
        assert "Total Conversions,15" in summary
        assert "Total Revenue,300.00" in summary
