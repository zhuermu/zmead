"""Admin API endpoints for user management."""

import math
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSuperAdmin, DbSession, is_super_admin
from app.models.user import User
from app.schemas.user import (
    AdminUserListItem,
    AdminUserListResponse,
    UserApprovalRequest,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    admin: CurrentSuperAdmin,
    db: DbSession,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    filter_approved: bool | None = Query(
        None, description="Filter by approval status (None = all users)"
    ),
    search: str | None = Query(None, max_length=255, description="Search by email or name"),
) -> AdminUserListResponse:
    """List all users (super admin only)."""
    # Build query
    query = select(User)

    # Apply filters
    if filter_approved is not None:
        query = query.where(User.is_approved == filter_approved)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (User.email.ilike(search_pattern))
            | (User.display_name.ilike(search_pattern))
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(User.created_at.desc())

    # Execute query
    result = await db.execute(query)
    users = result.scalars().all()

    # Build response
    user_items = [
        AdminUserListItem(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            oauth_provider=user.oauth_provider,
            total_credits=user.total_credits,
            is_active=user.is_active,
            is_approved=user.is_approved,
            is_super_admin=is_super_admin(user.email),
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )
        for user in users
    ]

    return AdminUserListResponse(
        users=user_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.put("/users/{user_id}/approval")
async def update_user_approval(
    user_id: int,
    request: UserApprovalRequest,
    admin: CurrentSuperAdmin,
    db: DbSession,
) -> dict[str, str]:
    """Approve or reject a user (super admin only)."""
    # Find user
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Don't allow modifying super admin approval status
    if is_super_admin(user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify approval status of super admin",
        )

    # Update approval status
    user.is_approved = request.approved

    await db.flush()
    await db.commit()

    action = "approved" if request.approved else "rejected"
    return {
        "message": f"User {user.email} has been {action}",
        "user_id": str(user_id),
        "approved": str(request.approved),
    }


@router.get("/users/{user_id}")
async def get_user_detail(
    user_id: int,
    admin: CurrentSuperAdmin,
    db: DbSession,
) -> AdminUserListItem:
    """Get detailed user information (super admin only)."""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return AdminUserListItem(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        oauth_provider=user.oauth_provider,
        total_credits=user.total_credits,
        is_active=user.is_active,
        is_approved=user.is_approved,
        is_super_admin=is_super_admin(user.email),
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.get("/stats")
async def get_admin_stats(
    admin: CurrentSuperAdmin,
    db: DbSession,
) -> dict:
    """Get platform statistics (super admin only)."""
    # Total users
    total_users_stmt = select(func.count()).select_from(User)
    total_users = (await db.execute(total_users_stmt)).scalar_one()

    # Approved users
    approved_users_stmt = select(func.count()).select_from(User).where(User.is_approved == True)
    approved_users = (await db.execute(approved_users_stmt)).scalar_one()

    # Pending users
    pending_users = total_users - approved_users

    # Active users (logged in within last 7 days)
    from datetime import timedelta
    seven_days_ago = datetime.now(UTC) - timedelta(days=7)
    active_users_stmt = (
        select(func.count())
        .select_from(User)
        .where(User.last_login_at >= seven_days_ago)
    )
    active_users = (await db.execute(active_users_stmt)).scalar_one()

    return {
        "total_users": total_users,
        "approved_users": approved_users,
        "pending_users": pending_users,
        "active_users_7d": active_users,
    }
