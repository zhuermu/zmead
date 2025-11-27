"""MCP tools for notification management.

Implements tools for managing user notifications:
- create_notification: Create a new notification
- get_notifications: Get list of notifications
- mark_notification_read: Mark a notification as read
- get_unread_count: Get count of unread notifications
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.registry import tool
from app.mcp.types import MCPToolParameter
from app.services.notification import (
    NotificationCategory,
    NotificationService,
    NotificationType,
)


@tool(
    name="create_notification",
    description="Create a new notification for the user. Urgent notifications are sent via both in-app and email.",
    parameters=[
        MCPToolParameter(
            name="notification_type",
            type="string",
            description="Urgency level of the notification",
            required=True,
            enum=["urgent", "important", "general"],
        ),
        MCPToolParameter(
            name="category",
            type="string",
            description="Category of the notification",
            required=True,
            enum=[
                "token_expired", "ad_rejected", "credit_low", "credit_depleted",
                "payment_success", "payment_failed", "report_ready", "creative_ready",
                "landing_page_ready", "budget_exhausted", "ad_paused",
                "optimization_suggestion", "weekly_summary", "new_feature",
                "system_maintenance", "system"
            ],
        ),
        MCPToolParameter(
            name="title",
            type="string",
            description="Notification title",
            required=True,
        ),
        MCPToolParameter(
            name="message",
            type="string",
            description="Notification message body",
            required=True,
        ),
        MCPToolParameter(
            name="action_url",
            type="string",
            description="URL for the action button",
            required=False,
        ),
        MCPToolParameter(
            name="action_text",
            type="string",
            description="Text for the action button",
            required=False,
        ),
        MCPToolParameter(
            name="extra_data",
            type="object",
            description="Additional metadata",
            required=False,
        ),
    ],
    category="notification",
)
async def create_notification(
    user_id: int,
    db: AsyncSession,
    notification_type: str,
    category: str,
    title: str,
    message: str,
    action_url: str | None = None,
    action_text: str | None = None,
    extra_data: dict | None = None,
) -> dict[str, Any]:
    """Create a new notification."""
    service = NotificationService(db)

    notification = await service.create_notification(
        user_id=user_id,
        notification_type=NotificationType(notification_type),
        category=NotificationCategory(category),
        title=title,
        message=message,
        action_url=action_url,
        action_text=action_text,
        extra_data=extra_data,
    )

    return {
        "id": notification.id,
        "user_id": notification.user_id,
        "type": notification.type,
        "category": notification.category,
        "title": notification.title,
        "message": notification.message,
        "action_url": notification.action_url,
        "action_text": notification.action_text,
        "is_read": notification.is_read,
        "sent_via": notification.sent_via or [],
        "extra_data": notification.extra_data or {},
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
    }


@tool(
    name="get_notifications",
    description="Get a list of notifications for the user with pagination.",
    parameters=[
        MCPToolParameter(
            name="limit",
            type="integer",
            description="Maximum number of notifications to return",
            required=False,
            default=50,
        ),
        MCPToolParameter(
            name="offset",
            type="integer",
            description="Number of notifications to skip",
            required=False,
            default=0,
        ),
        MCPToolParameter(
            name="unread_only",
            type="boolean",
            description="If true, only return unread notifications",
            required=False,
            default=False,
        ),
    ],
    category="notification",
)
async def get_notifications(
    user_id: int,
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    unread_only: bool = False,
) -> dict[str, Any]:
    """Get list of notifications."""
    # Validate limit
    limit = min(limit, 100)

    service = NotificationService(db)
    notifications = await service.get_notifications(
        user_id=user_id,
        limit=limit,
        offset=offset,
        unread_only=unread_only,
    )

    total = await service.get_total_count(user_id, unread_only=unread_only)

    # Convert to serializable format
    items = [
        {
            "id": n.id,
            "type": n.type,
            "category": n.category,
            "title": n.title,
            "message": n.message,
            "action_url": n.action_url,
            "action_text": n.action_text,
            "is_read": n.is_read,
            "read_at": n.read_at.isoformat() if n.read_at else None,
            "sent_via": n.sent_via or [],
            "extra_data": n.extra_data or {},
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifications
    ]

    return {
        "notifications": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(items) < total,
    }


@tool(
    name="mark_notification_read",
    description="Mark a specific notification as read.",
    parameters=[
        MCPToolParameter(
            name="notification_id",
            type="integer",
            description="ID of the notification to mark as read",
            required=True,
        ),
    ],
    category="notification",
)
async def mark_notification_read(
    user_id: int,
    db: AsyncSession,
    notification_id: int,
) -> dict[str, Any]:
    """Mark a notification as read."""
    service = NotificationService(db)
    success = await service.mark_as_read(user_id, notification_id)

    if not success:
        raise ValueError(f"Notification {notification_id} not found")

    return {
        "notification_id": notification_id,
        "marked_read": True,
    }


@tool(
    name="mark_all_notifications_read",
    description="Mark all notifications as read for the user.",
    parameters=[],
    category="notification",
)
async def mark_all_notifications_read(
    user_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    """Mark all notifications as read."""
    service = NotificationService(db)
    count = await service.mark_all_as_read(user_id)

    return {
        "marked_read_count": count,
    }


@tool(
    name="get_unread_count",
    description="Get the count of unread notifications for the user.",
    parameters=[],
    category="notification",
)
async def get_unread_count(
    user_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    """Get count of unread notifications."""
    service = NotificationService(db)
    count = await service.get_unread_count(user_id)

    return {
        "unread_count": count,
    }
