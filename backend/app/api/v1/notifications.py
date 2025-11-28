"""Notification API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.notification import (
    NotificationListResponse,
    NotificationMarkAllReadResponse,
    NotificationMarkReadResponse,
    NotificationResponse,
    NotificationUnreadCountResponse,
)
from app.services.notification import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    unread_only: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationListResponse:
    """
    Get notifications for the current user.
    
    Returns a paginated list of notifications sorted by creation time (newest first).
    """
    service = NotificationService(db)

    notifications = await service.get_notifications(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        unread_only=unread_only,
    )

    unread_count = await service.get_unread_count(current_user.id)
    total = await service.get_total_count(current_user.id, unread_only=unread_only)

    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in notifications],
        total=total,
        unread_count=unread_count,
    )


@router.get("/unread", response_model=NotificationUnreadCountResponse)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationUnreadCountResponse:
    """
    Get the count of unread notifications for the current user.
    """
    service = NotificationService(db)
    count = await service.get_unread_count(current_user.id)
    return NotificationUnreadCountResponse(unread_count=count)


@router.put("/{notification_id}/read", response_model=NotificationMarkReadResponse)
async def mark_notification_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationMarkReadResponse:
    """
    Mark a specific notification as read.
    """
    service = NotificationService(db)
    success = await service.mark_as_read(current_user.id, notification_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or already read",
        )

    await db.commit()

    return NotificationMarkReadResponse(
        success=True,
        message="Notification marked as read",
    )


@router.put("/read-all", response_model=NotificationMarkAllReadResponse)
async def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationMarkAllReadResponse:
    """
    Mark all notifications as read for the current user.
    """
    service = NotificationService(db)
    marked_count = await service.mark_all_as_read(current_user.id)

    await db.commit()

    return NotificationMarkAllReadResponse(
        success=True,
        marked_count=marked_count,
        message=f"Marked {marked_count} notifications as read",
    )


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationResponse:
    """
    Get a specific notification by ID.
    """
    service = NotificationService(db)
    notification = await service.get_notification_by_id(
        user_id=current_user.id,
        notification_id=notification_id,
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    return NotificationResponse.model_validate(notification)
