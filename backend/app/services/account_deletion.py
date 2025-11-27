"""Account deletion service for GDPR compliance."""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.storage import S3Storage
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


class AccountDeletionError(Exception):
    """Exception raised when account deletion fails."""
    pass


class AccountDeletionService:
    """Service for permanently deleting user accounts and all associated data."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize account deletion service."""
        self.db = db
        self.email_service = EmailService()
        self.creatives_storage = S3Storage(settings.s3_bucket_creatives)
        self.landing_pages_storage = S3Storage(settings.s3_bucket_landing_pages)
        self.exports_storage = S3Storage(settings.s3_bucket_exports)

    async def delete_user_account(self, user: User) -> dict[str, Any]:
        """
        Permanently delete user account and all associated data.
        
        This operation:
        1. Deletes all S3 files (creatives, landing pages, exports)
        2. Deletes all database records (cascading to related tables)
        3. Sends confirmation email
        4. Implements rollback on failure
        
        Args:
            user: User object to delete
            
        Returns:
            dict with deletion summary
            
        Raises:
            AccountDeletionError: If deletion fails
        """
        deletion_summary = {
            "user_id": user.id,
            "email": user.email,
            "started_at": datetime.now(UTC).isoformat(),
            "s3_files_deleted": {
                "creatives": 0,
                "landing_pages": 0,
                "exports": 0,
            },
            "database_records_deleted": {
                "ad_accounts": 0,
                "creatives": 0,
                "campaigns": 0,
                "landing_pages": 0,
                "credit_transactions": 0,
                "report_metrics": 0,
                "notifications": 0,
            },
            "status": "in_progress",
        }

        try:
            logger.info(f"Starting account deletion for user {user.id} ({user.email})")

            # Step 1: Collect all S3 file keys before deletion
            s3_files_to_delete = await self._collect_s3_files(user.id)
            
            # Step 2: Delete S3 files
            await self._delete_s3_files(s3_files_to_delete, deletion_summary)
            
            # Step 3: Count database records before deletion
            await self._count_database_records(user.id, deletion_summary)
            
            # Step 4: Delete database records (with transaction)
            # The User model has cascade="all, delete-orphan" on relationships,
            # so deleting the user will cascade to all related records
            await self.db.delete(user)
            await self.db.flush()
            
            # Step 5: Commit transaction
            await self.db.commit()
            
            deletion_summary["status"] = "completed"
            deletion_summary["completed_at"] = datetime.now(UTC).isoformat()
            
            logger.info(
                f"Account deletion completed for user {user.id}. "
                f"Deleted {deletion_summary['s3_files_deleted']} S3 files and "
                f"{sum(deletion_summary['database_records_deleted'].values())} database records."
            )
            
            # Step 6: Send confirmation email (best effort, don't fail if this fails)
            try:
                await self._send_deletion_confirmation_email(user)
            except Exception as e:
                logger.warning(f"Failed to send deletion confirmation email: {e}")
            
            return deletion_summary

        except Exception as e:
            # Rollback transaction on any error
            await self.db.rollback()
            
            deletion_summary["status"] = "failed"
            deletion_summary["error"] = str(e)
            deletion_summary["failed_at"] = datetime.now(UTC).isoformat()
            
            logger.error(f"Account deletion failed for user {user.id}: {e}", exc_info=True)
            
            raise AccountDeletionError(
                f"Failed to delete account: {str(e)}"
            ) from e

    async def _collect_s3_files(self, user_id: int) -> dict[str, list[str]]:
        """
        Collect all S3 file keys for a user.
        
        Returns:
            dict with lists of S3 keys for each bucket
        """
        s3_files = {
            "creatives": [],
            "landing_pages": [],
            "exports": [],
        }

        # Collect creative file keys
        stmt = select(Creative).where(
            Creative.user_id == user_id,
            Creative.status == 'active'
        )
        result = await self.db.execute(stmt)
        creatives = result.scalars().all()
        
        for creative in creatives:
            # Extract S3 key from file_url (format: s3://bucket/key or https://...)
            if creative.file_url:
                s3_key = self._extract_s3_key(creative.file_url)
                if s3_key:
                    s3_files["creatives"].append(s3_key)

        # Collect landing page file keys
        stmt = select(LandingPage).where(LandingPage.user_id == user_id)
        result = await self.db.execute(stmt)
        landing_pages = result.scalars().all()
        
        for page in landing_pages:
            if page.s3_key:
                s3_files["landing_pages"].append(page.s3_key)

        # Collect export file keys (pattern: exports/user_{user_id}_*.zip)
        # Note: We'll use a prefix-based deletion for exports
        s3_files["exports"].append(f"exports/user_{user_id}_")

        return s3_files

    def _extract_s3_key(self, url: str) -> str | None:
        """
        Extract S3 key from URL.
        
        Handles formats:
        - s3://bucket/key
        - https://bucket.s3.region.amazonaws.com/key
        - https://cdn.domain.com/key
        """
        if url.startswith("s3://"):
            # Format: s3://bucket/key
            parts = url.replace("s3://", "").split("/", 1)
            return parts[1] if len(parts) > 1 else None
        elif ".s3." in url or ".amazonaws.com" in url:
            # Format: https://bucket.s3.region.amazonaws.com/key
            parts = url.split("/", 3)
            return parts[3] if len(parts) > 3 else None
        elif url.startswith("http"):
            # Format: https://cdn.domain.com/key (CloudFront)
            parts = url.split("/", 3)
            return parts[3] if len(parts) > 3 else None
        return None

    async def _delete_s3_files(
        self,
        s3_files: dict[str, list[str]],
        deletion_summary: dict[str, Any]
    ) -> None:
        """Delete all S3 files for a user."""
        # Delete creative files
        for key in s3_files["creatives"]:
            try:
                self.creatives_storage.delete_file(key)
                deletion_summary["s3_files_deleted"]["creatives"] += 1
                logger.debug(f"Deleted creative file: {key}")
            except Exception as e:
                logger.warning(f"Failed to delete creative file {key}: {e}")

        # Delete landing page files
        for key in s3_files["landing_pages"]:
            try:
                self.landing_pages_storage.delete_file(key)
                deletion_summary["s3_files_deleted"]["landing_pages"] += 1
                logger.debug(f"Deleted landing page file: {key}")
            except Exception as e:
                logger.warning(f"Failed to delete landing page file {key}: {e}")

        # Delete export files (prefix-based)
        for prefix in s3_files["exports"]:
            try:
                # List and delete all files with this prefix
                deleted_count = self._delete_files_by_prefix(
                    self.exports_storage,
                    prefix
                )
                deletion_summary["s3_files_deleted"]["exports"] += deleted_count
                logger.debug(f"Deleted {deleted_count} export files with prefix: {prefix}")
            except Exception as e:
                logger.warning(f"Failed to delete export files with prefix {prefix}: {e}")

    def _delete_files_by_prefix(self, storage: S3Storage, prefix: str) -> int:
        """
        Delete all files in a bucket with a given prefix.
        
        Returns:
            Number of files deleted
        """
        try:
            # List objects with prefix
            response = storage.client.list_objects_v2(
                Bucket=storage.bucket,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                return 0
            
            # Delete all objects
            objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
            
            if objects_to_delete:
                storage.client.delete_objects(
                    Bucket=storage.bucket,
                    Delete={'Objects': objects_to_delete}
                )
            
            return len(objects_to_delete)
        except Exception as e:
            logger.error(f"Failed to delete files by prefix {prefix}: {e}")
            return 0

    async def _count_database_records(
        self,
        user_id: int,
        deletion_summary: dict[str, Any]
    ) -> None:
        """Count database records before deletion."""
        # Count ad accounts
        stmt = select(AdAccount).where(AdAccount.user_id == user_id)
        result = await self.db.execute(stmt)
        deletion_summary["database_records_deleted"]["ad_accounts"] = len(
            result.scalars().all()
        )

        # Count creatives
        stmt = select(Creative).where(Creative.user_id == user_id)
        result = await self.db.execute(stmt)
        deletion_summary["database_records_deleted"]["creatives"] = len(
            result.scalars().all()
        )

        # Count campaigns
        stmt = select(Campaign).where(Campaign.user_id == user_id)
        result = await self.db.execute(stmt)
        deletion_summary["database_records_deleted"]["campaigns"] = len(
            result.scalars().all()
        )

        # Count landing pages
        stmt = select(LandingPage).where(LandingPage.user_id == user_id)
        result = await self.db.execute(stmt)
        deletion_summary["database_records_deleted"]["landing_pages"] = len(
            result.scalars().all()
        )

        # Count credit transactions
        stmt = select(CreditTransaction).where(CreditTransaction.user_id == user_id)
        result = await self.db.execute(stmt)
        deletion_summary["database_records_deleted"]["credit_transactions"] = len(
            result.scalars().all()
        )

        # Count report metrics
        stmt = select(ReportMetrics).where(ReportMetrics.user_id == user_id)
        result = await self.db.execute(stmt)
        deletion_summary["database_records_deleted"]["report_metrics"] = len(
            result.scalars().all()
        )

        # Count notifications
        stmt = select(Notification).where(Notification.user_id == user_id)
        result = await self.db.execute(stmt)
        deletion_summary["database_records_deleted"]["notifications"] = len(
            result.scalars().all()
        )

    async def _send_deletion_confirmation_email(self, user: User) -> None:
        """Send email confirmation after account deletion."""
        try:
            await self.email_service.send_notification_email(
                to_email=user.email,
                to_name=user.display_name,
                subject="Your AAE Account Has Been Deleted",
                template=EmailTemplate.GENERAL_NOTIFICATION,
                template_data={
                    "title": "Account Deletion Confirmed",
                    "message": (
                        f"Your AAE account ({user.email}) has been permanently deleted. "
                        "All your data, including creatives, landing pages, campaigns, and reports, "
                        "has been removed from our systems. "
                        "\n\n"
                        "If you did not request this deletion, please contact our support team immediately."
                    ),
                    "action_url": f"{settings.frontend_url}/contact",
                    "action_text": "Contact Support"
                }
            )
            logger.info(f"Deletion confirmation email sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send deletion confirmation email: {e}")
            # Don't raise - email failure shouldn't fail the deletion
