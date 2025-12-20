"""Tests for data export service."""

import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ad_account import AdAccount
from app.models.campaign import Campaign
from app.models.creative import Creative
from app.models.credit_transaction import CreditTransaction
from app.models.landing_page import LandingPage
from app.models.notification import Notification
from app.models.report_metrics import ReportMetrics
from app.models.user import User
from app.services.data_export import DataExportService


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        id=1,  # Explicitly set ID for SQLite compatibility
        email="test@example.com",
        display_name="Test User",
        oauth_provider="google",
        oauth_id="google_123",
        gifted_credits=Decimal("100.00"),
        purchased_credits=Decimal("50.00"),
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_data(db_session: AsyncSession, test_user: User) -> dict:
    """Create test data for export."""
    # Create ad account
    ad_account = AdAccount(
        user_id=test_user.id,
        platform="meta",
        platform_account_id="act_123",
        account_name="Test Account",
        access_token_encrypted="encrypted_token",
        status="active",
    )
    db_session.add(ad_account)
    await db_session.flush()
    
    # Create creative
    creative = Creative(
        user_id=test_user.id,
        file_url="s3://bucket/creative.jpg",
        cdn_url="https://cdn.example.com/creative.jpg",
        file_type="image",
        file_size=1024000,
        name="Test Creative",
        status="active",
    )
    db_session.add(creative)
    await db_session.flush()
    
    # Create landing page
    landing_page = LandingPage(
        user_id=test_user.id,
        name="Test Landing Page",
        url="https://example.com/lp",
        s3_key="landing_pages/lp_123.html",
        product_url="https://example.com/product",
        status="published",
    )
    db_session.add(landing_page)
    await db_session.flush()
    
    # Create campaign
    campaign = Campaign(
        user_id=test_user.id,
        ad_account_id=ad_account.id,
        platform="meta",
        name="Test Campaign",
        objective="conversions",
        budget=Decimal("100.00"),
        status="active",
    )
    db_session.add(campaign)
    await db_session.flush()
    
    # Create credit transaction
    transaction = CreditTransaction(
        user_id=test_user.id,
        type="deduct",
        amount=Decimal("10.00"),
        from_gifted=Decimal("10.00"),
        from_purchased=Decimal("0.00"),
        balance_after=Decimal("140.00"),
        operation_type="generate_creative",
    )
    db_session.add(transaction)
    await db_session.flush()
    
    # Create notification
    notification = Notification(
        user_id=test_user.id,
        type="general",
        category="creative_ready",
        title="Creative Ready",
        message="Your creative is ready",
        is_read=False,
    )
    db_session.add(notification)
    await db_session.flush()
    
    # Create report metrics
    metrics = ReportMetrics(
        timestamp=datetime.now(UTC),
        user_id=test_user.id,
        ad_account_id=ad_account.id,
        entity_type="campaign",
        entity_id="camp_123",
        entity_name="Test Campaign",
        impressions=1000,
        clicks=50,
        spend=Decimal("25.00"),
        conversions=5,
        revenue=Decimal("100.00"),
        ctr=5.0,
        cpc=Decimal("0.50"),
        cpa=Decimal("5.00"),
        roas=4.0,
    )
    db_session.add(metrics)
    await db_session.flush()
    
    await db_session.commit()
    
    return {
        "ad_account": ad_account,
        "creative": creative,
        "landing_page": landing_page,
        "campaign": campaign,
        "transaction": transaction,
        "notification": notification,
        "metrics": metrics,
    }


class TestDataExportService:
    """Test data export service."""

    async def test_collect_user_profile(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Test collecting user profile data."""
        service = DataExportService(db_session)
        profile = await service._collect_user_profile(test_user)
        
        assert profile["id"] == test_user.id
        assert profile["email"] == test_user.email
        assert profile["display_name"] == test_user.display_name
        assert profile["gifted_credits"] == 100.0
        assert profile["purchased_credits"] == 50.0
        assert profile["total_credits"] == 150.0

    async def test_collect_ad_accounts(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_data: dict,
    ) -> None:
        """Test collecting ad accounts data."""
        service = DataExportService(db_session)
        accounts = await service._collect_ad_accounts(test_user.id)
        
        assert len(accounts) == 1
        assert accounts[0]["platform"] == "meta"
        assert accounts[0]["account_name"] == "Test Account"
        assert "access_token_encrypted" not in accounts[0]
        assert "note" in accounts[0]

    async def test_collect_credit_history(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_data: dict,
    ) -> None:
        """Test collecting credit history."""
        service = DataExportService(db_session)
        history = await service._collect_credit_history(test_user.id)
        
        assert len(history) == 1
        assert history[0]["type"] == "deduct"
        assert history[0]["amount"] == 10.0
        assert history[0]["operation_type"] == "generate_creative"

    async def test_collect_creatives(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_data: dict,
    ) -> None:
        """Test collecting creatives data."""
        service = DataExportService(db_session)
        creatives = await service._collect_creatives(test_user.id)
        
        assert len(creatives) == 1
        assert creatives[0]["name"] == "Test Creative"
        assert creatives[0]["file_type"] == "image"

    async def test_collect_campaigns(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_data: dict,
    ) -> None:
        """Test collecting campaigns data."""
        service = DataExportService(db_session)
        campaigns = await service._collect_campaigns(test_user.id)
        
        assert len(campaigns) == 1
        assert campaigns[0]["name"] == "Test Campaign"
        assert campaigns[0]["platform"] == "meta"

    async def test_collect_reports(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_data: dict,
    ) -> None:
        """Test collecting report metrics."""
        service = DataExportService(db_session)
        reports = await service._collect_reports(test_user.id)
        
        assert len(reports) == 1
        assert reports[0]["entity_type"] == "campaign"
        assert reports[0]["impressions"] == 1000
        assert reports[0]["clicks"] == 50

    async def test_generate_credit_csv(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_data: dict,
    ) -> None:
        """Test generating credit CSV."""
        service = DataExportService(db_session)
        history = await service._collect_credit_history(test_user.id)
        csv_content = service._generate_credit_csv(history)
        
        assert "Date,Type,Amount" in csv_content
        assert "deduct" in csv_content
        assert "10.0" in csv_content

    async def test_generate_metrics_csv(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_data: dict,
    ) -> None:
        """Test generating metrics CSV."""
        service = DataExportService(db_session)
        reports = await service._collect_reports(test_user.id)
        csv_content = service._generate_metrics_csv(reports)
        
        assert "Timestamp,Ad Account ID" in csv_content
        assert "campaign" in csv_content
        assert "1000" in csv_content  # impressions

    async def test_generate_performance_summary(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_data: dict,
    ) -> None:
        """Test generating performance summary."""
        service = DataExportService(db_session)
        reports = await service._collect_reports(test_user.id)
        summary = service._generate_performance_summary(reports)
        
        assert "Total Impressions,1000" in summary
        assert "Total Clicks,50" in summary
        assert "Total Spend,25.00" in summary

    async def test_generate_readme(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Test generating README."""
        service = DataExportService(db_session)
        readme = service._generate_readme(test_user)
        
        assert "AAE Data Export" in readme
        assert test_user.email in readme
        assert test_user.display_name in readme
        assert "user_profile.json" in readme
        assert "credit_history.csv" in readme
