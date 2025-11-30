"""Creative service for managing advertising assets."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import creatives_storage
from app.models.creative import Creative
from app.schemas.creative import (
    CreativeCreate,
    CreativeFilter,
    CreativeStatus,
    CreativeUpdate,
)


class CreativeNotFoundError(Exception):
    """Raised when creative is not found."""

    def __init__(self, creative_id: int):
        self.creative_id = creative_id
        super().__init__(f"Creative {creative_id} not found")


class CreativeService:
    """Service for creative operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        user_id: int,
        data: CreativeCreate,
    ) -> Creative:
        """Create a new creative.

        Args:
            user_id: Owner user ID
            data: Creative creation data

        Returns:
            Created Creative instance
        """
        creative = Creative(
            user_id=user_id,
            file_url=data.file_url,
            cdn_url=data.cdn_url,
            file_type=data.file_type.value,
            file_size=data.file_size,
            name=data.name,
            product_url=data.product_url,
            style=data.style,
            score=data.score,
            tags=data.tags or [],
            status=CreativeStatus.ACTIVE.value,
        )

        self.db.add(creative)
        await self.db.flush()
        await self.db.refresh(creative)

        return creative

    async def get_by_id(
        self,
        creative_id: int,
        user_id: int | None = None,
    ) -> Creative | None:
        """Get creative by ID.

        Args:
            creative_id: Creative ID
            user_id: Optional user ID to filter by owner

        Returns:
            Creative instance or None if not found
        """
        query = select(Creative).where(Creative.id == creative_id)

        if user_id is not None:
            query = query.where(Creative.user_id == user_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_list(
        self,
        user_id: int,
        filters: CreativeFilter | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Get paginated list of creatives.

        Args:
            user_id: Owner user ID
            filters: Optional filter criteria
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Dictionary with creatives, total, page, page_size, has_more
        """
        # Base query
        query = select(Creative).where(Creative.user_id == user_id)

        # Apply filters
        if filters:
            if filters.status:
                query = query.where(Creative.status == filters.status.value)
            if filters.file_type:
                query = query.where(Creative.file_type == filters.file_type.value)
            if filters.style:
                query = query.where(Creative.style == filters.style)
            # Tag filtering - check if any of the filter tags are in creative tags
            if filters.tags:
                # MySQL JSON contains check
                for tag in filters.tags:
                    query = query.where(
                        Creative.tags.contains([tag])
                    )
        else:
            # Default to active creatives only
            query = query.where(Creative.status == CreativeStatus.ACTIVE.value)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Apply pagination and ordering
        offset = (page - 1) * page_size
        query = query.order_by(Creative.created_at.desc()).offset(offset).limit(page_size)

        result = await self.db.execute(query)
        creatives = list(result.scalars().all())

        return {
            "creatives": creatives,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": offset + len(creatives) < total,
        }

    async def update(
        self,
        creative_id: int,
        user_id: int,
        data: CreativeUpdate,
    ) -> Creative:
        """Update a creative.

        Args:
            creative_id: Creative ID
            user_id: Owner user ID
            data: Update data

        Returns:
            Updated Creative instance

        Raises:
            CreativeNotFoundError: If creative not found or not owned by user
        """
        creative = await self.get_by_id(creative_id, user_id)

        if not creative:
            raise CreativeNotFoundError(creative_id)

        # Update fields if provided
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(creative, field, value)

        creative.updated_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(creative)

        return creative

    async def delete(
        self,
        creative_id: int,
        user_id: int,
        hard_delete: bool = False,
    ) -> bool:
        """Delete a creative.

        Args:
            creative_id: Creative ID
            user_id: Owner user ID
            hard_delete: If True, permanently delete; otherwise soft delete

        Returns:
            True if deleted successfully

        Raises:
            CreativeNotFoundError: If creative not found or not owned by user
        """
        creative = await self.get_by_id(creative_id, user_id)

        if not creative:
            raise CreativeNotFoundError(creative_id)

        if hard_delete:
            # Delete GCS file
            try:
                file_key = self._extract_gcs_key(creative.file_url)
                if file_key:
                    creatives_storage.delete_file(file_key)
            except Exception:
                # Log but don't fail if GCS deletion fails
                pass

            await self.db.delete(creative)
        else:
            # Soft delete
            creative.status = CreativeStatus.DELETED.value
            creative.updated_at = datetime.utcnow()

        await self.db.flush()
        return True

    def _extract_gcs_key(self, gcs_url: str) -> str | None:
        """Extract GCS key from GCS URL.

        Args:
            gcs_url: GCS URL (gs://bucket/key or https://storage.googleapis.com/...)

        Returns:
            GCS key or None
        """
        if gcs_url.startswith("gs://"):
            # gs://bucket/key format
            parts = gcs_url.replace("gs://", "").split("/", 1)
            return parts[1] if len(parts) > 1 else None
        elif "storage.googleapis.com/" in gcs_url:
            # https://storage.googleapis.com/bucket/key format
            parts = gcs_url.split("storage.googleapis.com/", 1)
            if len(parts) > 1:
                # Remove bucket name from path
                path_parts = parts[1].split("/", 1)
                return path_parts[1] if len(path_parts) > 1 else None
        return None

    def generate_presigned_upload_url(
        self,
        user_id: int,
        filename: str,
        content_type: str,
        expires_in: int = 3600,
    ) -> dict[str, Any]:
        """Generate presigned URL for file upload.

        Args:
            user_id: User ID for organizing files
            filename: Original filename
            content_type: MIME type of the file
            expires_in: URL expiration time in seconds

        Returns:
            Dictionary with upload_url, upload_fields, file_key, s3_url, cdn_url
        """
        # Generate unique file key
        file_ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
        unique_id = uuid.uuid4().hex
        file_key = f"users/{user_id}/creatives/{unique_id}.{file_ext}"

        # Generate presigned POST URL
        presigned = creatives_storage.generate_presigned_upload_url(
            key=file_key,
            content_type=content_type,
            expires_in=expires_in,
        )

        # Get URLs
        gcs_url = f"gs://{creatives_storage.bucket_name}/{file_key}"
        cdn_url = creatives_storage.get_cdn_url(file_key)

        return {
            "upload_url": presigned["url"],
            "upload_fields": presigned["fields"],
            "file_key": file_key,
            "gcs_url": gcs_url,
            "cdn_url": cdn_url,
            "expires_in": expires_in,
        }

    async def get_by_ids(
        self,
        creative_ids: list[int],
        user_id: int,
    ) -> list[Creative]:
        """Get multiple creatives by IDs.

        Args:
            creative_ids: List of creative IDs
            user_id: Owner user ID

        Returns:
            List of Creative instances
        """
        if not creative_ids:
            return []

        result = await self.db.execute(
            select(Creative)
            .where(Creative.id.in_(creative_ids))
            .where(Creative.user_id == user_id)
            .where(Creative.status == CreativeStatus.ACTIVE.value)
        )
        return list(result.scalars().all())
