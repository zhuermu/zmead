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
        )
        self.db.add(ad_account)
        await self.db.flush()
        await self.db.refresh(ad_account)
        return self._to_response(ad_account)

    async def bind_ad_account_from_oauth(
        self, user_id: int, platform: str, code: str, state: str | None = None
    ) -> AdAccountResponse:
        """
        Bind ad account from OAuth callback.
        
        This is a simplified implementation for MVP.
        In production, this would:
        1. Exchange the OAuth code for access/refresh tokens
        2. Fetch account details from the platform API
        3. Store the encrypted tokens
        """
        from datetime import timedelta
        
        # Simulate OAuth token exchange
        # In production, call the actual platform OAuth endpoints
        mock_access_token = f"mock_access_token_{platform}_{code[:10]}"
        mock_refresh_token = f"mock_refresh_token_{platform}_{code[:10]}"
        mock_account_id = f"{platform}_account_{user_id}"
        mock_account_name = f"{platform.upper()} Ad Account"
        
        # Token expires in 60 days
        expires_at = datetime.now(UTC) + timedelta(days=60)
        
        # Create account data
        from app.schemas.ad_account import AdAccountCreate, AdPlatform
        
        account_data = AdAccountCreate(
            platform=AdPlatform(platform),
            platform_account_id=mock_account_id,
            account_name=mock_account_name,
            access_token=mock_access_token,
            refresh_token=mock_refresh_token,
            token_expires_at=expires_at,
        )
        
        return await self.bind_ad_account(user_id, account_data)


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
