"""Token refresh background tasks."""

import asyncio
from datetime import UTC, datetime, timedelta

import httpx
from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import token_encryption
from app.models.ad_account import AdAccount


async def _get_async_session() -> AsyncSession:
    """Create an async database session for background tasks."""
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return async_session()


async def _refresh_meta_token(refresh_token: str) -> dict | None:
    """Refresh Meta (Facebook) OAuth token."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.facebook.com/v18.0/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": settings.facebook_client_id,
                    "client_secret": settings.facebook_client_secret,
                    "fb_exchange_token": refresh_token,
                },
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "access_token": data.get("access_token"),
                    "expires_in": data.get("expires_in", 5184000),  # Default 60 days
                }
    except Exception:
        pass
    return None


async def _refresh_google_token(refresh_token: str) -> dict | None:
    """Refresh Google OAuth token."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "access_token": data.get("access_token"),
                    "expires_in": data.get("expires_in", 3600),
                }
    except Exception:
        pass
    return None


async def _refresh_tiktok_token(refresh_token: str) -> dict | None:
    """Refresh TikTok OAuth token."""
    # TikTok token refresh implementation
    # Note: TikTok uses a different OAuth flow, this is a placeholder
    return None


async def _refresh_token_for_account(
    db: AsyncSession, account: AdAccount
) -> tuple[bool, str]:
    """Attempt to refresh token for a single ad account."""
    if not account.refresh_token_encrypted:
        return False, "No refresh token available"

    try:
        refresh_token = token_encryption.decrypt(account.refresh_token_encrypted)
    except Exception:
        return False, "Failed to decrypt refresh token"

    # Call platform-specific refresh
    result = None
    if account.platform == "meta":
        result = await _refresh_meta_token(refresh_token)
    elif account.platform == "google":
        result = await _refresh_google_token(refresh_token)
    elif account.platform == "tiktok":
        result = await _refresh_tiktok_token(refresh_token)

    if result and result.get("access_token"):
        # Update tokens in database
        account.access_token_encrypted = token_encryption.encrypt(result["access_token"])
        expires_in = result.get("expires_in", 3600)
        account.token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
        account.status = "active"
        account.last_synced_at = datetime.now(UTC)
        await db.flush()
        return True, "Token refreshed successfully"

    return False, "Token refresh failed"


async def _create_token_expired_notification(
    db: AsyncSession, account: AdAccount
) -> None:
    """Create notification for token expiry."""
    from app.services.notification import (
        NotificationCategory,
        NotificationService,
        NotificationType,
    )

    notification_service = NotificationService(db)
    await notification_service.create_notification(
        user_id=account.user_id,
        notification_type=NotificationType.URGENT,
        category=NotificationCategory.TOKEN_EXPIRED,
        title=f"{account.platform.title()} Ad Account Authorization Expired",
        message=(
            f"Your {account.platform.title()} ad account '{account.account_name}' "
            "authorization has expired. Please re-authorize to continue managing your ads."
        ),
        action_url="/settings/ad-accounts",
        action_text="Re-authorize",
        extra_data={
            "platform": account.platform,
            "account_name": account.account_name,
            "account_id": account.id,
        },
        send_email=True,
    )


async def _check_and_refresh_tokens() -> dict:
    """Check all ad accounts for expiring tokens and refresh them."""
    db = await _get_async_session()
    results = {
        "checked": 0,
        "refreshed": 0,
        "failed": 0,
        "expired": 0,
        "errors": [],
    }

    try:
        # Find accounts with tokens expiring within 24 hours
        expiry_threshold = datetime.now(UTC) + timedelta(hours=24)

        stmt = select(AdAccount).where(
            AdAccount.status == "active",
            AdAccount.token_expires_at.isnot(None),
            AdAccount.token_expires_at <= expiry_threshold,
        )
        result = await db.execute(stmt)
        accounts = result.scalars().all()

        results["checked"] = len(accounts)

        for account in accounts:
            success, message = await _refresh_token_for_account(db, account)

            if success:
                results["refreshed"] += 1
            else:
                results["failed"] += 1
                results["errors"].append({
                    "account_id": account.id,
                    "platform": account.platform,
                    "error": message,
                })

                # Mark as expired and create notification
                account.status = "expired"
                await _create_token_expired_notification(db, account)
                results["expired"] += 1

        await db.commit()

    except Exception as e:
        results["errors"].append({"error": str(e)})
        await db.rollback()
    finally:
        await db.close()

    return results


@shared_task(
    name="app.tasks.token_refresh.check_token_expiry",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def check_token_expiry(self) -> dict:
    """Celery task to check and refresh expiring tokens."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(_check_and_refresh_tokens())


async def _refresh_single_account(account_id: int) -> dict:
    """Refresh token for a single ad account."""
    db = await _get_async_session()
    result = {"success": False, "message": "", "account_id": account_id}

    try:
        stmt = select(AdAccount).where(AdAccount.id == account_id)
        db_result = await db.execute(stmt)
        account = db_result.scalar_one_or_none()

        if not account:
            result["message"] = "Account not found"
            return result

        success, message = await _refresh_token_for_account(db, account)
        result["success"] = success
        result["message"] = message

        if not success:
            account.status = "expired"
            await _create_token_expired_notification(db, account)

        await db.commit()

    except Exception as e:
        result["message"] = str(e)
        await db.rollback()
    finally:
        await db.close()

    return result


@shared_task(
    name="app.tasks.token_refresh.refresh_ad_account_token",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def refresh_ad_account_token(self, account_id: int) -> dict:
    """Celery task to refresh token for a specific ad account."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(_refresh_single_account(account_id))
