"""Ad Account service for managing advertising platform connections."""

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import token_encryption
from app.models.ad_account import AdAccount
from app.schemas.ad_account import (
    AdAccountCreate,
    AdAccountResponse,
    AdAccountUpdate,
)


class AdAccountService:
    """Service for managing ad account operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize ad account service with database session."""
        self.db = db

    def _encrypt_token(self, token: str) -> str:
        """Encrypt an OAuth token for storage."""
        return token_encryption.encrypt(token)

    def _decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt an OAuth token from storage."""
        return token_encryption.decrypt(encrypted_token)

    def _to_response(self, ad_account: AdAccount) -> AdAccountResponse:
        """Convert AdAccount model to response schema."""
        return AdAccountResponse(
            id=ad_account.id,
            user_id=ad_account.user_id,
            platform=ad_account.platform,
            platform_account_id=ad_account.platform_account_id,
            account_name=ad_account.account_name,
            status=ad_account.status,
            is_active=ad_account.is_active,
            is_manager=ad_account.is_manager,
            manager_account_id=ad_account.manager_account_id,
            token_expires_at=ad_account.token_expires_at,
            created_at=ad_account.created_at,
            updated_at=ad_account.updated_at,
            last_synced_at=ad_account.last_synced_at,
        )

    async def bind_ad_account(
        self, user_id: int, data: AdAccountCreate
    ) -> AdAccountResponse:
        """Bind a new ad account for a user."""
        # Check if account already exists for this user and platform
        stmt = select(AdAccount).where(
            AdAccount.user_id == user_id,
            AdAccount.platform == data.platform.value,
            AdAccount.platform_account_id == data.platform_account_id,
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing account with new tokens
            existing.access_token_encrypted = self._encrypt_token(data.access_token)
            if data.refresh_token:
                existing.refresh_token_encrypted = self._encrypt_token(data.refresh_token)
            existing.token_expires_at = data.token_expires_at
            existing.status = "active"
            existing.account_name = data.account_name
            existing.is_manager = data.is_manager
            existing.manager_account_id = data.manager_account_id
            existing.last_synced_at = datetime.now(UTC)
            await self.db.flush()
            await self.db.refresh(existing)
            return self._to_response(existing)

        # Create new ad account
        ad_account = AdAccount(
            user_id=user_id,
            platform=data.platform.value,
            platform_account_id=data.platform_account_id,
            account_name=data.account_name,
            access_token_encrypted=self._encrypt_token(data.access_token),
            refresh_token_encrypted=(
                self._encrypt_token(data.refresh_token) if data.refresh_token else None
            ),
            token_expires_at=data.token_expires_at,
            status="active",
            is_active=False,
            is_manager=data.is_manager,
            manager_account_id=data.manager_account_id,
            last_synced_at=datetime.now(UTC),
        )
        self.db.add(ad_account)
        await self.db.flush()
        await self.db.refresh(ad_account)
        return self._to_response(ad_account)

    async def get_oauth_available_accounts(
        self, user_id: int, platform: str, code: str, redirect_uri: str | None = None
    ) -> tuple[list[dict], str]:
        """
        Get available accounts from OAuth provider without binding them.

        Returns tuple of (account list, session_token).
        Session token is used to retrieve cached token data when binding.
        """
        import secrets
        import json
        from app.core.redis import get_redis
        from app.services.google_ads_client import get_google_ads_client

        if platform != "google":
            raise ValueError(f"Platform '{platform}' is not supported yet.")

        google_ads_client = get_google_ads_client()

        if not redirect_uri:
            redirect_uri = "http://localhost:3000/ad-accounts/callback"

        # Exchange code for tokens
        token_data = await google_ads_client.exchange_code_for_tokens(code, redirect_uri)

        # Get list of accessible accounts
        accounts = await google_ads_client.get_accessible_accounts(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"]
        )

        # Generate session token and cache the OAuth data
        session_token = secrets.token_urlsafe(32)
        redis_client = await get_redis()

        # Store token data and accounts in Redis with 10 minute expiry
        cache_key = f"oauth_session:{session_token}"
        cache_data = {
            "user_id": user_id,
            "platform": platform,
            "token_data": token_data,
            "accounts": accounts,
        }
        await redis_client.setex(
            cache_key,
            600,  # 10 minutes
            json.dumps(cache_data, default=str)
        )

        return accounts, session_token

    async def bind_selected_oauth_accounts(
        self, user_id: int, platform: str, session_token: str, selected_account_ids: list[str]
    ) -> list[AdAccountResponse]:
        """
        Bind only selected accounts after user chooses which ones to connect.
        Uses session_token to retrieve cached OAuth data from Redis.
        """
        import json
        from app.core.redis import get_redis
        from app.schemas.ad_account import AdPlatform

        if platform != "google":
            raise ValueError(f"Platform '{platform}' is not supported yet.")

        # Retrieve cached OAuth data from Redis
        redis_client = await get_redis()
        cache_key = f"oauth_session:{session_token}"
        cached_data_str = await redis_client.get(cache_key)

        if not cached_data_str:
            raise ValueError("OAuth session expired or invalid. Please try connecting again.")

        cached_data = json.loads(cached_data_str)

        # Verify user_id matches
        if cached_data["user_id"] != user_id:
            raise ValueError("Invalid session token")

        token_data = cached_data["token_data"]
        all_accounts = cached_data["accounts"]

        # Filter to only selected accounts
        selected_accounts = [
            acc for acc in all_accounts
            if acc["id"] in selected_account_ids
        ]

        if not selected_accounts:
            raise ValueError("No valid accounts selected")

        # Bind selected accounts
        bound_accounts = []
        for account_info in selected_accounts:
            account_data = AdAccountCreate(
                platform=AdPlatform(platform),
                platform_account_id=account_info["id"],
                account_name=account_info["name"],
                access_token=token_data["access_token"],
                refresh_token=token_data["refresh_token"],
                token_expires_at=token_data["expires_at"],
                is_manager=account_info.get("is_manager", False),
                manager_account_id=account_info.get("manager_id"),
            )
            bound_account = await self.bind_ad_account(user_id, account_data)
            bound_accounts.append(bound_account)

        # Delete the session token after use
        await redis_client.delete(cache_key)

        return bound_accounts

    async def bind_ad_account_from_oauth(
        self, user_id: int, platform: str, code: str, state: str | None = None, redirect_uri: str | None = None
    ) -> AdAccountResponse:
        """
        Bind ad account from OAuth callback.

        Exchanges OAuth code for tokens and fetches account details from the platform API.
        """
        from app.schemas.ad_account import AdAccountCreate, AdPlatform
        from app.services.google_ads_client import get_google_ads_client

        # Only Google Ads is supported for now
        if platform != "google":
            raise ValueError(f"Platform '{platform}' is not supported yet. Only 'google' is currently supported.")

        # Get Google Ads client
        google_ads_client = get_google_ads_client()

        # Exchange OAuth code for tokens
        if not redirect_uri:
            redirect_uri = "http://localhost:3000/ad-accounts/callback"

        token_data = await google_ads_client.exchange_code_for_tokens(code, redirect_uri)

        # Get list of accessible accounts
        accounts = await google_ads_client.get_accessible_accounts(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"]
        )

        if not accounts:
            raise ValueError("No Google Ads accounts found. Please make sure you have at least one Google Ads account.")

        # Bind all accessible accounts
        bound_accounts = []
        for account_info in accounts:
            account_data = AdAccountCreate(
                platform=AdPlatform(platform),
                platform_account_id=account_info["id"],
                account_name=account_info["name"],
                access_token=token_data["access_token"],
                refresh_token=token_data["refresh_token"],
                token_expires_at=token_data["expires_at"],
                is_manager=account_info.get("is_manager", False),
                manager_account_id=account_info.get("manager_id"),
            )
            bound_account = await self.bind_ad_account(user_id, account_data)
            bound_accounts.append(bound_account)

        # Return the first bound account as the primary response
        return bound_accounts[0]


    async def list_ad_accounts(self, user_id: int) -> list[AdAccountResponse]:
        """List all ad accounts for a user."""
        stmt = select(AdAccount).where(AdAccount.user_id == user_id).order_by(
            AdAccount.created_at.desc()
        )
        result = await self.db.execute(stmt)
        accounts = result.scalars().all()
        return [self._to_response(acc) for acc in accounts]

    async def get_ad_account(
        self, user_id: int, account_id: int
    ) -> AdAccountResponse | None:
        """Get a specific ad account by ID."""
        stmt = select(AdAccount).where(
            AdAccount.id == account_id,
            AdAccount.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        ad_account = result.scalar_one_or_none()
        if not ad_account:
            return None
        return self._to_response(ad_account)

    async def get_ad_account_model(
        self, user_id: int, account_id: int
    ) -> AdAccount | None:
        """Get the raw AdAccount model (for internal use)."""
        stmt = select(AdAccount).where(
            AdAccount.id == account_id,
            AdAccount.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_ad_account(
        self, user_id: int, account_id: int, data: AdAccountUpdate
    ) -> AdAccountResponse | None:
        """Update an ad account."""
        ad_account = await self.get_ad_account_model(user_id, account_id)
        if not ad_account:
            return None

        # If setting this account as active, deactivate others for same platform
        if data.is_active is True:
            await self.db.execute(
                update(AdAccount)
                .where(
                    AdAccount.user_id == user_id,
                    AdAccount.platform == ad_account.platform,
                    AdAccount.id != account_id,
                )
                .values(is_active=False)
            )
            ad_account.is_active = True

        if data.account_name is not None:
            ad_account.account_name = data.account_name

        if data.is_active is False:
            ad_account.is_active = False

        await self.db.flush()
        await self.db.refresh(ad_account)
        return self._to_response(ad_account)

    async def unbind_ad_account(self, user_id: int, account_id: int) -> bool:
        """Unbind (delete) an ad account."""
        ad_account = await self.get_ad_account_model(user_id, account_id)
        if not ad_account:
            return False

        await self.db.delete(ad_account)
        await self.db.flush()
        return True

    async def get_decrypted_access_token(
        self, user_id: int, account_id: int
    ) -> str | None:
        """Get decrypted access token for an ad account."""
        ad_account = await self.get_ad_account_model(user_id, account_id)
        if not ad_account:
            return None
        return self._decrypt_token(ad_account.access_token_encrypted)

    async def get_decrypted_refresh_token(
        self, user_id: int, account_id: int
    ) -> str | None:
        """Get decrypted refresh token for an ad account."""
        ad_account = await self.get_ad_account_model(user_id, account_id)
        if not ad_account or not ad_account.refresh_token_encrypted:
            return None
        return self._decrypt_token(ad_account.refresh_token_encrypted)

    async def update_tokens(
        self,
        account_id: int,
        access_token: str,
        refresh_token: str | None = None,
        expires_at: datetime | None = None,
    ) -> bool:
        """Update tokens for an ad account (used after refresh)."""
        stmt = select(AdAccount).where(AdAccount.id == account_id)
        result = await self.db.execute(stmt)
        ad_account = result.scalar_one_or_none()
        if not ad_account:
            return False

        ad_account.access_token_encrypted = self._encrypt_token(access_token)
        if refresh_token:
            ad_account.refresh_token_encrypted = self._encrypt_token(refresh_token)
        if expires_at:
            ad_account.token_expires_at = expires_at
        ad_account.status = "active"
        ad_account.last_synced_at = datetime.now(UTC)

        await self.db.flush()
        return True

    async def mark_token_expired(self, account_id: int) -> bool:
        """Mark an ad account's token as expired."""
        stmt = select(AdAccount).where(AdAccount.id == account_id)
        result = await self.db.execute(stmt)
        ad_account = result.scalar_one_or_none()
        if not ad_account:
            return False

        ad_account.status = "expired"
        await self.db.flush()
        return True

    async def get_active_ad_account(
        self, user_id: int, platform: str
    ) -> AdAccountResponse | None:
        """Get the currently active ad account for a platform."""
        stmt = select(AdAccount).where(
            AdAccount.user_id == user_id,
            AdAccount.platform == platform,
            AdAccount.is_active == True,
        )
        result = await self.db.execute(stmt)
        ad_account = result.scalar_one_or_none()
        if not ad_account:
            return None
        return self._to_response(ad_account)

    async def set_active_ad_account(
        self, user_id: int, account_id: int
    ) -> AdAccountResponse | None:
        """Set an ad account as the active one for its platform."""
        return await self.update_ad_account(
            user_id, account_id, AdAccountUpdate(is_active=True)
        )
