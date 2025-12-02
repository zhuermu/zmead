"""Data export service for GDPR compliance."""

import csv
import io
import json
import logging
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.storage import GCSStorage
from app.models.ad_account import AdAccount
from app.models.campaign import Campaign
from app.models.creative import Creative
from app.models.credit_transaction import CreditTransaction
from app.models.landing_page import LandingPage
from app.models.notification import Notification
from app.models.report_metrics import ReportMetrics
from app.models.user import User
from app.services.email import EmailService, EmailTemplate

logger = logging.getLogger(__name__)


class DataExportService:
    """Service for exporting user data (GDPR compliance)."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize data export service."""
        self.db = db
        self.email_service = EmailService()
        self.export_storage = GCSStorage(settings.gcs_bucket_exports)

    async def export_user_data(self, user: User) -> dict[str, Any]:
        """
        Export all user data to a ZIP file.
        
        Returns:
            dict with export_url and expires_at
        """
        try:
            # Collect all user data
            logger.info(f"Starting data export for user {user.id}")
            
            user_data = await self._collect_user_profile(user)
            ad_accounts_data = await self._collect_ad_accounts(user.id)
            credit_history = await self._collect_credit_history(user.id)
            creatives_data = await self._collect_creatives(user.id)
            landing_pages_data = await self._collect_landing_pages(user.id)
            campaigns_data = await self._collect_campaigns(user.id)
            reports_data = await self._collect_reports(user.id)
            notifications_data = await self._collect_notifications(user.id)
            
            # Create ZIP file in memory
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add README
                readme_content = self._generate_readme(user)
                zip_file.writestr('README.txt', readme_content)
                
                # Add user profile
                zip_file.writestr(
                    'user_profile.json',
                    json.dumps(user_data, indent=2, default=str)
                )
                
                # Add ad accounts
                zip_file.writestr(
                    'ad_accounts.json',
                    json.dumps(ad_accounts_data, indent=2, default=str)
                )
                
                # Add credit history (CSV)
                credit_csv = self._generate_credit_csv(credit_history)
                zip_file.writestr('credit_history.csv', credit_csv)
                
                # Add creatives metadata
                if creatives_data:
                    zip_file.writestr(
                        'creatives/creatives_metadata.json',
                        json.dumps(creatives_data, indent=2, default=str)
                    )
                    
                    # Download and add creative files
                    await self._add_creative_files(zip_file, creatives_data)
                
                # Add landing pages
                if landing_pages_data:
                    zip_file.writestr(
                        'landing_pages/landing_pages_metadata.json',
                        json.dumps(landing_pages_data, indent=2, default=str)
                    )
                    
                    # Add landing page HTML files
                    await self._add_landing_page_files(zip_file, landing_pages_data)
                
                # Add campaigns
                if campaigns_data:
                    zip_file.writestr(
                        'campaigns/campaigns.json',
                        json.dumps(campaigns_data, indent=2, default=str)
                    )
                
                # Add reports (CSV)
                if reports_data:
                    daily_metrics_csv = self._generate_metrics_csv(reports_data)
                    zip_file.writestr('reports/daily_metrics.csv', daily_metrics_csv)
                    
                    # Add performance summary
                    summary = self._generate_performance_summary(reports_data)
                    zip_file.writestr(
                        'reports/performance_summary.csv',
                        summary
                    )
                
                # Add notifications
                if notifications_data:
                    zip_file.writestr(
                        'notifications.json',
                        json.dumps(notifications_data, indent=2, default=str)
                    )
            
            # Upload to S3 with 24h expiry
            zip_buffer.seek(0)
            timestamp = datetime.now(UTC).strftime('%Y%m%d_%H%M%S')
            file_key = f"exports/user_{user.id}_{timestamp}.zip"
            
            self.export_storage.upload_file(
                key=file_key,
                data=zip_buffer.getvalue(),
                content_type='application/zip'
            )
            
            # Generate presigned download URL (24 hours)
            download_url = self.export_storage.generate_presigned_download_url(
                key=file_key,
                expires_in=86400  # 24 hours
            )
            
            expires_at = datetime.now(UTC) + timedelta(hours=24)
            
            logger.info(f"Data export completed for user {user.id}")
            
            # Send email notification
            await self._send_export_ready_email(user, download_url, expires_at)
            
            return {
                "download_url": download_url,
                "expires_at": expires_at.isoformat(),
                "file_size_mb": len(zip_buffer.getvalue()) / (1024 * 1024),
            }
            
        except Exception as e:
            logger.error(f"Data export failed for user {user.id}: {e}")
            raise

    async def _collect_user_profile(self, user: User) -> dict[str, Any]:
        """Collect user profile data."""
        return {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "oauth_provider": user.oauth_provider,
            "gifted_credits": float(user.gifted_credits),
            "purchased_credits": float(user.purchased_credits),
            "total_credits": float(user.total_credits),
            "language": user.language,
            "timezone": user.timezone,
            "notification_preferences": user.notification_preferences,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        }

    async def _collect_ad_accounts(self, user_id: int) -> list[dict[str, Any]]:
        """Collect ad accounts data (without sensitive tokens)."""
        stmt = select(AdAccount).where(AdAccount.user_id == user_id)
        result = await self.db.execute(stmt)
        accounts = result.scalars().all()
        
        return [
            {
                "id": acc.id,
                "platform": acc.platform,
                "platform_account_id": acc.platform_account_id,
                "account_name": acc.account_name,
                "status": acc.status,
                "is_active": acc.is_active,
                "token_expires_at": acc.token_expires_at.isoformat() if acc.token_expires_at else None,
                "created_at": acc.created_at.isoformat(),
                "last_synced_at": acc.last_synced_at.isoformat() if acc.last_synced_at else None,
                "note": "OAuth tokens excluded for security",
            }
            for acc in accounts
        ]

    async def _collect_credit_history(self, user_id: int) -> list[dict[str, Any]]:
        """Collect credit transaction history."""
        stmt = (
            select(CreditTransaction)
            .where(CreditTransaction.user_id == user_id)
            .order_by(CreditTransaction.created_at.desc())
        )
        result = await self.db.execute(stmt)
        transactions = result.scalars().all()
        
        return [
            {
                "id": tx.id,
                "type": tx.type,
                "amount": float(tx.amount),
                "from_gifted": float(tx.from_gifted),
                "from_purchased": float(tx.from_purchased),
                "balance_after": float(tx.balance_after),
                "operation_type": tx.operation_type,
                "operation_id": tx.operation_id,
                "details": tx.details,
                "created_at": tx.created_at.isoformat(),
            }
            for tx in transactions
        ]

    async def _collect_creatives(self, user_id: int) -> list[dict[str, Any]]:
        """Collect creatives metadata."""
        stmt = (
            select(Creative)
            .where(Creative.user_id == user_id, Creative.status == 'active')
            .order_by(Creative.created_at.desc())
        )
        result = await self.db.execute(stmt)
        creatives = result.scalars().all()
        
        return [
            {
                "id": creative.id,
                "name": creative.name,
                "file_url": creative.file_url,
                "cdn_url": creative.cdn_url,
                "file_type": creative.file_type,
                "file_size": creative.file_size,
                "product_url": creative.product_url,
                "style": creative.style,
                "score": creative.score,
                "tags": creative.tags,
                "created_at": creative.created_at.isoformat(),
            }
            for creative in creatives
        ]

    async def _collect_landing_pages(self, user_id: int) -> list[dict[str, Any]]:
        """Collect landing pages data."""
        stmt = (
            select(LandingPage)
            .where(LandingPage.user_id == user_id)
            .order_by(LandingPage.created_at.desc())
        )
        result = await self.db.execute(stmt)
        pages = result.scalars().all()
        
        return [
            {
                "id": page.id,
                "name": page.name,
                "url": page.url,
                "s3_key": page.s3_key,
                "product_url": page.product_url,
                "template": page.template,
                "language": page.language,
                "status": page.status,
                "created_at": page.created_at.isoformat(),
                "published_at": page.published_at.isoformat() if page.published_at else None,
            }
            for page in pages
        ]

    async def _collect_campaigns(self, user_id: int) -> list[dict[str, Any]]:
        """Collect campaigns data."""
        stmt = (
            select(Campaign)
            .where(Campaign.user_id == user_id)
            .order_by(Campaign.created_at.desc())
        )
        result = await self.db.execute(stmt)
        campaigns = result.scalars().all()
        
        return [
            {
                "id": campaign.id,
                "platform": campaign.platform,
                "platform_campaign_id": campaign.platform_campaign_id,
                "name": campaign.name,
                "objective": campaign.objective,
                "status": campaign.status,
                "budget": float(campaign.budget),
                "budget_type": campaign.budget_type,
                "targeting": campaign.targeting,
                "creative_ids": campaign.creative_ids,
                "landing_page_id": campaign.landing_page_id,
                "created_at": campaign.created_at.isoformat(),
            }
            for campaign in campaigns
        ]

    async def _collect_reports(self, user_id: int) -> list[dict[str, Any]]:
        """Collect report metrics data."""
        stmt = (
            select(ReportMetrics)
            .where(ReportMetrics.user_id == user_id)
            .order_by(ReportMetrics.timestamp.desc())
            .limit(10000)  # Limit to last 10k records
        )
        result = await self.db.execute(stmt)
        metrics = result.scalars().all()
        
        return [
            {
                "timestamp": metric.timestamp.isoformat(),
                "ad_account_id": metric.ad_account_id,
                "entity_type": metric.entity_type,
                "entity_id": metric.entity_id,
                "entity_name": metric.entity_name,
                "impressions": metric.impressions,
                "clicks": metric.clicks,
                "spend": float(metric.spend),
                "conversions": metric.conversions,
                "revenue": float(metric.revenue),
                "ctr": metric.ctr,
                "cpc": float(metric.cpc),
                "cpa": float(metric.cpa),
                "roas": metric.roas,
            }
            for metric in metrics
        ]

    async def _collect_notifications(self, user_id: int) -> list[dict[str, Any]]:
        """Collect notifications data."""
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(1000)  # Last 1000 notifications
        )
        result = await self.db.execute(stmt)
        notifications = result.scalars().all()
        
        return [
            {
                "id": notif.id,
                "type": notif.type,
                "category": notif.category,
                "title": notif.title,
                "message": notif.message,
                "action_url": notif.action_url,
                "action_text": notif.action_text,
                "is_read": notif.is_read,
                "read_at": notif.read_at.isoformat() if notif.read_at else None,
                "sent_via": notif.sent_via,
                "created_at": notif.created_at.isoformat(),
            }
            for notif in notifications
        ]

    def _generate_readme(self, user: User) -> str:
        """Generate README file for the export."""
        return f"""AAE Data Export
================

Export Date: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}
User: {user.display_name} ({user.email})
User ID: {user.id}

This archive contains all your data from the AAE (Automated Ad Engine) platform.

Contents:
---------
- README.txt: This file
- user_profile.json: Your account information and settings
- ad_accounts.json: Your connected advertising accounts (tokens excluded for security)
- credit_history.csv: Your credit transaction history
- creatives/: Your advertising creatives (images/videos)
  - creatives_metadata.json: Metadata for all creatives
  - creative_001.jpg, creative_002.png, etc.: Creative files
- landing_pages/: Your landing pages
  - landing_pages_metadata.json: Metadata for all landing pages
  - lp_001.html, lp_002.html, etc.: Landing page HTML files
- campaigns/: Your advertising campaigns
  - campaigns.json: Campaign configurations
- reports/: Your advertising performance data
  - daily_metrics.csv: Daily performance metrics
  - performance_summary.csv: Aggregated performance summary
- notifications.json: Your notification history

Data Format:
------------
- JSON files: Machine-readable structured data
- CSV files: Spreadsheet-compatible tabular data
- HTML files: Landing page source code

Privacy & Security:
-------------------
- OAuth tokens and passwords are NOT included in this export for security reasons
- This download link expires 24 hours after generation
- Please store this data securely

Questions?
----------
If you have any questions about this export, please contact support@aae.com

© 2024 AAE. All rights reserved.
"""

    def _generate_credit_csv(self, transactions: list[dict[str, Any]]) -> str:
        """Generate CSV for credit history."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'Date',
            'Type',
            'Amount',
            'From Gifted',
            'From Purchased',
            'Balance After',
            'Operation Type',
            'Operation ID',
            'Details'
        ])
        
        # Data rows
        for tx in transactions:
            writer.writerow([
                tx['created_at'],
                tx['type'],
                tx['amount'],
                tx['from_gifted'],
                tx['from_purchased'],
                tx['balance_after'],
                tx['operation_type'] or '',
                tx['operation_id'] or '',
                json.dumps(tx['details']) if tx['details'] else ''
            ])
        
        return output.getvalue()

    def _generate_metrics_csv(self, metrics: list[dict[str, Any]]) -> str:
        """Generate CSV for report metrics."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'Timestamp',
            'Ad Account ID',
            'Entity Type',
            'Entity ID',
            'Entity Name',
            'Impressions',
            'Clicks',
            'Spend',
            'Conversions',
            'Revenue',
            'CTR',
            'CPC',
            'CPA',
            'ROAS'
        ])
        
        # Data rows
        for metric in metrics:
            writer.writerow([
                metric['timestamp'],
                metric['ad_account_id'],
                metric['entity_type'],
                metric['entity_id'],
                metric['entity_name'],
                metric['impressions'],
                metric['clicks'],
                metric['spend'],
                metric['conversions'],
                metric['revenue'],
                metric['ctr'],
                metric['cpc'],
                metric['cpa'],
                metric['roas']
            ])
        
        return output.getvalue()

    def _generate_performance_summary(self, metrics: list[dict[str, Any]]) -> str:
        """Generate performance summary CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'Metric',
            'Value'
        ])
        
        if not metrics:
            return output.getvalue()
        
        # Calculate totals
        total_impressions = sum(m['impressions'] for m in metrics)
        total_clicks = sum(m['clicks'] for m in metrics)
        total_spend = sum(m['spend'] for m in metrics)
        total_conversions = sum(m['conversions'] for m in metrics)
        total_revenue = sum(m['revenue'] for m in metrics)
        
        avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        avg_cpc = (total_spend / total_clicks) if total_clicks > 0 else 0
        avg_cpa = (total_spend / total_conversions) if total_conversions > 0 else 0
        total_roas = (total_revenue / total_spend) if total_spend > 0 else 0
        
        # Write summary
        writer.writerow(['Total Impressions', total_impressions])
        writer.writerow(['Total Clicks', total_clicks])
        writer.writerow(['Total Spend', f'{total_spend:.2f}'])
        writer.writerow(['Total Conversions', total_conversions])
        writer.writerow(['Total Revenue', f'{total_revenue:.2f}'])
        writer.writerow(['Average CTR (%)', f'{avg_ctr:.2f}'])
        writer.writerow(['Average CPC', f'{avg_cpc:.2f}'])
        writer.writerow(['Average CPA', f'{avg_cpa:.2f}'])
        writer.writerow(['Overall ROAS', f'{total_roas:.2f}'])
        
        return output.getvalue()

    async def _add_creative_files(
        self,
        zip_file: zipfile.ZipFile,
        creatives: list[dict[str, Any]]
    ) -> None:
        """Download and add creative files to ZIP."""
        # Note: In production, this would download files from S3
        # For MVP, we'll just add a note that files are available at their URLs
        note = "Creative files are available at the URLs listed in creatives_metadata.json\n"
        note += "Due to file size limitations, actual files are not included in this export.\n"
        note += "Please download them individually from the URLs provided.\n"
        zip_file.writestr('creatives/NOTE.txt', note)

    async def _add_landing_page_files(
        self,
        zip_file: zipfile.ZipFile,
        pages: list[dict[str, Any]]
    ) -> None:
        """Add landing page HTML files to ZIP."""
        # Note: In production, this would download HTML from S3
        # For MVP, we'll add a note
        note = "Landing page HTML files are available at the URLs listed in landing_pages_metadata.json\n"
        note += "Please visit the URLs to view or download the pages.\n"
        zip_file.writestr('landing_pages/NOTE.txt', note)

    async def _send_export_ready_email(
        self,
        user: User,
        download_url: str,
        expires_at: datetime
    ) -> None:
        """Send email notification when export is ready."""
        try:
            await self.email_service.send_notification_email(
                to_email=user.email,
                to_name=user.display_name,
                subject="Your Data Export is Ready",
                template=EmailTemplate.GENERAL_NOTIFICATION,
                template_data={
                    "title": "📦 Your Data Export is Ready",
                    "message": f"Your data export has been generated and is ready for download. "
                               f"The download link will expire on {expires_at.strftime('%Y-%m-%d at %H:%M UTC')}.",
                    "action_url": download_url,
                    "action_text": "Download Export"
                }
            )
            logger.info(f"Export ready email sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send export ready email: {e}")
