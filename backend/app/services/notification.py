"""Notification service for managing user notifications."""

from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


class NotificationType(str, Enum):
    """Notification urgency types."""

    URGENT = "urgent"
    IMPORTANT = "important"
    GENERAL = "general"


class NotificationCategory(str, Enum):
    """Notification categories."""

    TOKEN_EXPIRED = "token_expired"
    AD_REJECTED = "ad_rejected"
    CREDIT_LOW = "credit_low"
    CREDIT_DEPLETED = "credit_depleted"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    REPORT_READY = "report_ready"
    CREATIVE_READY = "creative_ready"
    LANDING_PAGE_READY = "landing_page_ready"
    BUDGET_EXHAUSTED = "budget_exhausted"
    AD_PAUSED = "ad_paused"
    OPTIMIZATION_SUGGESTION = "optimization_suggestion"
    WEEKLY_SUMMARY = "weekly_summary"
    NEW_FEATURE = "new_feature"
    SYSTEM_MAINTENANCE = "system_maintenance"
    SYSTEM = "system"


# Categories that are always urgent and bypass user preferences
URGENT_CATEGORIES = {
    NotificationCategory.TOKEN_EXPIRED,
    NotificationCategory.AD_REJECTED,
    NotificationCategory.CREDIT_DEPLETED,
    NotificationCategory.BUDGET_EXHAUSTED,
    NotificationCategory.AD_PAUSED,
}


class NotificationService:
    """Service for managing notifications."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize notification service with database session."""
        self.db = db

    async def create_notification(
        self,
        user_id: int,
        notification_type: NotificationType,
        category: NotificationCategory,
        title: str,
        message: str,
        action_url: str | None = None,
        action_text: str | None = None,
        extra_data: dict | None = None,
        send_email: bool = False,
        user_preferences: dict | None = None,
    ) -> Notification:
        """
        Create a new notification for a user.
        
        Args:
            user_id: The user to notify
            notification_type: Urgency level (urgent, important, general)
            category: Category of notification
            title: Notification title
            message: Notification message body
            action_url: Optional URL for action button
            action_text: Optional text for action button
            extra_data: Additional metadata
            send_email: Force email sending
            user_preferences: User's notification preferences
        
        Returns:
            Created Notification object
        """
        sent_via = []

        # Determine channels based on type and preferences
        is_urgent = (
            notification_type == NotificationType.URGENT
            or category in URGENT_CATEGORIES
        )

        # Check user preferences for in-app notifications
        in_app_enabled = True
        email_enabled = False

        if user_preferences:
            in_app_enabled = user_preferences.get("in_app_enabled", True)
            email_enabled = user_preferences.get("email_enabled", False)

            # Check category-specific preferences
            category_prefs = user_preferences.get("category_preferences", {})
            if category.value in category_prefs:
                cat_pref = category_prefs[category.value]
                in_app_enabled = cat_pref.get("in_app", in_app_enabled)
                email_enabled = cat_pref.get("email", email_enabled)

        # Urgent notifications always get both channels regardless of preferences
        if is_urgent:
            sent_via = ["in_app", "email"]
        else:
            if in_app_enabled:
                sent_via.append("in_app")
            if email_enabled or send_email:
                sent_via.append("email")

        # If no channels enabled, at least send in-app
        if not sent_via:
            sent_via = ["in_app"]

        notification = Notification(
            user_id=user_id,
            type=notification_type.value,
            category=category.value,
            title=title,
            message=message,
            action_url=action_url,
            action_text=action_text,
            extra_data=extra_data or {},
            sent_via=sent_via,
        )
        self.db.add(notification)
        await self.db.flush()
        await self.db.refresh(notification)

        # Send email if required
        if "email" in sent_via:
            await self._send_email_notification(user_id, notification)

        return notification

    async def _send_email_notification(
        self,
        user_id: int,
        notification: Notification,
    ) -> None:
        """
        Send email notification to user.
        
        Fetches user email and sends notification via email service.
        """
        from app.models.user import User
        from app.services.email import EmailService, EmailTemplate

        # Get user email
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return

        email_service = EmailService()

        # Map notification category to email template
        template_map = {
            NotificationCategory.TOKEN_EXPIRED.value: EmailTemplate.TOKEN_EXPIRED,
            NotificationCategory.AD_REJECTED.value: EmailTemplate.AD_REJECTED,
            NotificationCategory.CREDIT_LOW.value: EmailTemplate.CREDIT_LOW,
            NotificationCategory.CREDIT_DEPLETED.value: EmailTemplate.CREDIT_DEPLETED,
            NotificationCategory.PAYMENT_SUCCESS.value: EmailTemplate.PAYMENT_SUCCESS,
            NotificationCategory.REPORT_READY.value: EmailTemplate.REPORT_READY,
            NotificationCategory.CREATIVE_READY.value: EmailTemplate.CREATIVE_READY,
            NotificationCategory.LANDING_PAGE_READY.value: EmailTemplate.LANDING_PAGE_READY,
        }

        template = template_map.get(
            notification.category,
            EmailTemplate.GENERAL_NOTIFICATION,
        )

        # Build template data from notification
        template_data = {
            "title": notification.title,
            "message": notification.message,
            "action_url": notification.action_url or "",
            "action_text": notification.action_text or "",
            **notification.extra_data,
        }

        await email_service.send_notification_email(
            to_email=user.email,
            to_name=user.display_name,
            subject=notification.title,
            template=template,
            template_data=template_data,
        )

    async def get_notifications(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
    ) -> list[Notification]:
        """Get notifications for a user."""
        stmt = select(Notification).where(Notification.user_id == user_id)

        if unread_only:
            stmt = stmt.where(Notification.is_read == False)  # noqa: E712

        stmt = stmt.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_unread_count(self, user_id: int) -> int:
        """Get count of unread notifications for a user."""
        stmt = select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read == False,  # noqa: E712
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def get_total_count(
        self,
        user_id: int,
        unread_only: bool = False,
    ) -> int:
        """Get total count of notifications for a user."""
        stmt = select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
        )
        if unread_only:
            stmt = stmt.where(Notification.is_read == False)  # noqa: E712
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def mark_as_read(self, user_id: int, notification_id: int) -> bool:
        """Mark a notification as read."""
        stmt = (
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
            .values(is_read=True, read_at=datetime.now(UTC))
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount > 0

    async def mark_all_as_read(self, user_id: int) -> int:
        """Mark all notifications as read for a user."""
        stmt = (
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read == False,  # noqa: E712
            )
            .values(is_read=True, read_at=datetime.now(UTC))
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount

    async def get_notification_by_id(
        self,
        user_id: int,
        notification_id: int,
    ) -> Notification | None:
        """Get a specific notification by ID."""
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # Convenience methods for creating specific notification types

    async def create_token_expired_notification(
        self,
        user_id: int,
        platform: str,
        account_name: str,
    ) -> Notification:
        """Create a notification for expired ad account token."""
        return await self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.URGENT,
            category=NotificationCategory.TOKEN_EXPIRED,
            title=f"{platform.title()} Ad Account Authorization Expired",
            message=(
                f"Your {platform.title()} ad account '{account_name}' authorization has expired. "
                "Please re-authorize to continue managing your ads."
            ),
            action_url="/settings/ad-accounts",
            action_text="Re-authorize",
            extra_data={"platform": platform, "account_name": account_name},
        )

    async def create_credit_low_notification(
        self,
        user_id: int,
        current_balance: Decimal,
        threshold: int = 50,
    ) -> Notification:
        """Create a notification for low credit balance."""
        return await self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.IMPORTANT,
            category=NotificationCategory.CREDIT_LOW,
            title="Credit Balance Running Low",
            message=(
                f"Your credit balance is {current_balance:.2f} credits, "
                f"which is below the warning threshold of {threshold} credits. "
                "Consider recharging to avoid service interruption."
            ),
            action_url="/billing/recharge",
            action_text="Recharge Now",
            extra_data={
                "current_balance": str(current_balance),
                "threshold": threshold,
            },
        )

    async def create_credit_depleted_notification(
        self,
        user_id: int,
    ) -> Notification:
        """Create a notification for depleted credit balance."""
        return await self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.URGENT,
            category=NotificationCategory.CREDIT_DEPLETED,
            title="Credit Balance Depleted",
            message=(
                "Your credit balance has been depleted. "
                "Please recharge to continue using AI features."
            ),
            action_url="/billing/recharge",
            action_text="Recharge Now",
        )

    async def create_payment_success_notification(
        self,
        user_id: int,
        amount: Decimal,
        credits_added: Decimal,
    ) -> Notification:
        """Create a notification for successful payment."""
        return await self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.GENERAL,
            category=NotificationCategory.PAYMENT_SUCCESS,
            title="Payment Successful",
            message=(
                f"Your payment of ¥{amount:.2f} was successful. "
                f"{credits_added:.2f} credits have been added to your account."
            ),
            action_url="/billing",
            action_text="View Balance",
            extra_data={
                "amount": str(amount),
                "credits_added": str(credits_added),
            },
        )

    async def create_report_ready_notification(
        self,
        user_id: int,
        report_type: str,
        report_date: str,
    ) -> Notification:
        """Create a notification for report generation completion."""
        return await self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.IMPORTANT,
            category=NotificationCategory.REPORT_READY,
            title=f"{report_type} Report Ready",
            message=f"Your {report_type.lower()} report for {report_date} is ready to view.",
            action_url="/reports",
            action_text="View Report",
            extra_data={
                "report_type": report_type,
                "report_date": report_date,
            },
        )

    async def create_creative_ready_notification(
        self,
        user_id: int,
        creative_count: int,
    ) -> Notification:
        """Create a notification for creative generation completion."""
        return await self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.IMPORTANT,
            category=NotificationCategory.CREATIVE_READY,
            title="Creatives Generated",
            message=f"{creative_count} new creative(s) have been generated and are ready for review.",
            action_url="/creatives",
            action_text="View Creatives",
            extra_data={"creative_count": creative_count},
        )

    async def create_landing_page_ready_notification(
        self,
        user_id: int,
        landing_page_name: str,
    ) -> Notification:
        """Create a notification for landing page generation completion."""
        return await self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.IMPORTANT,
            category=NotificationCategory.LANDING_PAGE_READY,
            title="Landing Page Ready",
            message=f"Your landing page '{landing_page_name}' has been generated and is ready for review.",
            action_url="/landing-pages",
            action_text="View Landing Page",
            extra_data={"landing_page_name": landing_page_name},
        )

    async def create_ad_rejected_notification(
        self,
        user_id: int,
        platform: str,
        ad_name: str,
        rejection_reason: str,
    ) -> Notification:
        """Create a notification for ad rejection."""
        return await self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.URGENT,
            category=NotificationCategory.AD_REJECTED,
            title=f"Ad Rejected on {platform.title()}",
            message=(
                f"Your ad '{ad_name}' was rejected by {platform.title()}. "
                f"Reason: {rejection_reason}"
            ),
            action_url="/campaigns",
            action_text="View Campaign",
            extra_data={
                "platform": platform,
                "ad_name": ad_name,
                "rejection_reason": rejection_reason,
            },
        )

    async def create_optimization_suggestion_notification(
        self,
        user_id: int,
        suggestion_summary: str,
    ) -> Notification:
        """Create a notification for AI optimization suggestions."""
        return await self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.IMPORTANT,
            category=NotificationCategory.OPTIMIZATION_SUGGESTION,
            title="AI Optimization Suggestions Available",
            message=suggestion_summary,
            action_url="/dashboard",
            action_text="View Suggestions",
        )
