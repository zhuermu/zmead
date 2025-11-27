"""User service for user management operations."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserUpdateRequest


class UserService:
    """Service for handling user management operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize user service with database session."""
        self.db = db

    async def get_user_by_id(self, user_id: int) -> User | None:
        """Get user by ID."""
        stmt = select(User).where(User.id == user_id, User.is_active == True)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email."""
        stmt = select(User).where(User.email == email, User.is_active == True)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_user(
        self,
        user: User,
        update_data: UserUpdateRequest,
    ) -> User:
        """Update user profile."""
        update_dict = update_data.model_dump(exclude_unset=True)

        for field, value in update_dict.items():
            if value is not None:
                setattr(user, field, value)

        user.updated_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def delete_user(self, user: User) -> bool:
        """
        Delete user account (soft delete by setting is_active to False).
        
        Note: For full GDPR compliance, this should also:
        - Delete all user data from S3 (creatives, landing pages)
        - Delete all related database records
        - Send confirmation email
        
        This is a simplified implementation that performs soft delete.
        Full implementation will be done in the data export/deletion task.
        """
        user.is_active = False
        user.updated_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def hard_delete_user(self, user: User) -> dict:
        """
        Permanently delete user and all associated data.
        
        This method delegates to AccountDeletionService which:
        - Deletes all S3 files (creatives, landing pages, exports)
        - Deletes all database records (cascading to related tables)
        - Sends confirmation email
        - Implements rollback on failure
        
        Returns:
            dict with deletion summary
            
        Raises:
            AccountDeletionError: If deletion fails
        """
        from app.services.account_deletion import AccountDeletionService
        
        deletion_service = AccountDeletionService(self.db)
        return await deletion_service.delete_user_account(user)

    async def request_data_export(self, user: User) -> str:
        """
        Request data export for user.
        Returns a job ID that can be used to check status.
        
        Creates a background task to:
        1. Collect all user data
        2. Generate ZIP file
        3. Upload to S3 with 24h expiry
        4. Send email notification
        """
        import uuid
        from app.core.redis import get_redis
        import json
        import asyncio
        
        job_id = str(uuid.uuid4())
        redis = get_redis()
        
        # Store job status in Redis
        job_data = {
            "user_id": user.id,
            "status": "processing",
            "created_at": datetime.now(UTC).isoformat(),
        }
        await redis.set(
            f"export_job:{job_id}",
            json.dumps(job_data),
            ex=86400  # 24 hours
        )
        
        # Trigger background task to generate export
        asyncio.create_task(self._process_data_export(job_id, user))
        
        return job_id

    async def _process_data_export(self, job_id: str, user: User) -> None:
        """Process data export in background."""
        import json
        from app.core.redis import get_redis
        from app.services.data_export import DataExportService
        
        redis = get_redis()
        
        try:
            # Generate export
            export_service = DataExportService(self.db)
            result = await export_service.export_user_data(user)
            
            # Update job status
            job_data = {
                "user_id": user.id,
                "status": "completed",
                "download_url": result["download_url"],
                "expires_at": result["expires_at"],
                "file_size_mb": result["file_size_mb"],
                "completed_at": datetime.now(UTC).isoformat(),
            }
            
            await redis.set(
                f"export_job:{job_id}",
                json.dumps(job_data),
                ex=86400  # 24 hours
            )
            
        except Exception as e:
            # Update job status with error
            job_data = {
                "user_id": user.id,
                "status": "failed",
                "error": str(e),
                "failed_at": datetime.now(UTC).isoformat(),
            }
            
            await redis.set(
                f"export_job:{job_id}",
                json.dumps(job_data),
                ex=86400  # 24 hours
            )

    async def get_export_status(self, user: User, job_id: str) -> dict:
        """
        Get the status of a data export job.
        Returns status and download URL when ready.
        """
        from app.core.redis import get_redis
        import json
        
        redis = get_redis()
        job_data_str = await redis.get(f"export_job:{job_id}")
        
        if not job_data_str:
            return {
                "status": "not_found",
                "error": "Export job not found or expired",
            }
        
        job_data = json.loads(job_data_str)
        
        # Verify job belongs to current user
        if job_data["user_id"] != user.id:
            return {
                "status": "forbidden",
                "error": "Access denied",
            }
        
        response = {
            "status": job_data["status"],
        }
        
        # Add fields based on status
        if job_data["status"] == "completed":
            response["download_url"] = job_data.get("download_url")
            response["expires_at"] = job_data.get("expires_at")
            response["file_size_mb"] = job_data.get("file_size_mb")
            response["completed_at"] = job_data.get("completed_at")
        elif job_data["status"] == "failed":
            response["error"] = job_data.get("error")
            response["failed_at"] = job_data.get("failed_at")
        elif job_data["status"] == "processing":
            response["created_at"] = job_data.get("created_at")
        
        return response
