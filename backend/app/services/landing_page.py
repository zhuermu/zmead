"""Landing page service for managing landing pages."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import landing_pages_storage
from app.models.landing_page import LandingPage
from app.schemas.landing_page import (
    LandingPageCreate,
    LandingPageFilter,
    LandingPageStatus,
    LandingPageUpdate,
)


class LandingPageNotFoundError(Exception):
    """Raised when landing page is not found."""

    def __init__(self, landing_page_id: int):
        self.landing_page_id = landing_page_id
        super().__init__(f"Landing page {landing_page_id} not found")


class LandingPageService:
    """Service for landing page operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        user_id: int,
        data: LandingPageCreate,
    ) -> LandingPage:
        """Create a new landing page.

        Args:
            user_id: Owner user ID
            data: Landing page creation data

        Returns:
            Created LandingPage instance
        """
        # Generate unique S3 key for draft (in drafts subfolder)
        unique_id = uuid.uuid4().hex
        draft_s3_key = f"users/{user_id}/landing-pages/drafts/{unique_id}/index.html"

        # Upload draft HTML to S3 immediately
        if data.html_content:
            landing_pages_storage.upload_file(
                key=draft_s3_key,
                data=data.html_content.encode("utf-8"),
                content_type="text/html; charset=utf-8",
            )

        landing_page = LandingPage(
            user_id=user_id,
            name=data.name,
            url="",  # Draft pages have no public URL until published
            s3_key=draft_s3_key,  # Store draft S3 key
            product_url=data.product_url,
            template=data.template,
            language=data.language,
            # 创建时内容保存到 draft_content，html_content 在发布时才会被填充
            draft_content=data.html_content,
            html_content=None,
            status=LandingPageStatus.DRAFT.value,
        )

        self.db.add(landing_page)
        await self.db.flush()
        await self.db.refresh(landing_page)

        return landing_page


    async def get_by_id(
        self,
        landing_page_id: int,
        user_id: int | None = None,
    ) -> LandingPage | None:
        """Get landing page by ID.

        Args:
            landing_page_id: Landing page ID
            user_id: Optional user ID to filter by owner

        Returns:
            LandingPage instance or None if not found
        """
        query = select(LandingPage).where(LandingPage.id == landing_page_id)

        if user_id is not None:
            query = query.where(LandingPage.user_id == user_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_list(
        self,
        user_id: int,
        filters: LandingPageFilter | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Get paginated list of landing pages.

        Args:
            user_id: Owner user ID
            filters: Optional filter criteria
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Dictionary with landing_pages, total, page, page_size, has_more
        """
        # Base query - exclude archived by default
        query = select(LandingPage).where(LandingPage.user_id == user_id)

        # Apply filters
        if filters:
            if filters.status:
                query = query.where(LandingPage.status == filters.status.value)
            else:
                # Default: exclude archived
                query = query.where(LandingPage.status != LandingPageStatus.ARCHIVED.value)
            if filters.template:
                query = query.where(LandingPage.template == filters.template)
            if filters.language:
                query = query.where(LandingPage.language == filters.language)
        else:
            # Default: exclude archived
            query = query.where(LandingPage.status != LandingPageStatus.ARCHIVED.value)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Apply pagination and ordering
        offset = (page - 1) * page_size
        query = query.order_by(LandingPage.created_at.desc()).offset(offset).limit(page_size)

        result = await self.db.execute(query)
        landing_pages = list(result.scalars().all())

        return {
            "landing_pages": landing_pages,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": offset + len(landing_pages) < total,
        }

    async def update(
        self,
        landing_page_id: int,
        user_id: int,
        data: LandingPageUpdate,
    ) -> LandingPage:
        """Update a landing page.

        Args:
            landing_page_id: Landing page ID
            user_id: Owner user ID
            data: Update data

        Returns:
            Updated LandingPage instance

        Raises:
            LandingPageNotFoundError: If landing page not found or not owned by user
        """
        landing_page = await self.get_by_id(landing_page_id, user_id)

        if not landing_page:
            raise LandingPageNotFoundError(landing_page_id)

        # Update fields if provided
        update_data = data.model_dump(exclude_unset=True)

        # 编辑器保存时，将 html_content 映射到 draft_content
        # 前端发送 html_content，后端存储到 draft_content
        if "html_content" in update_data:
            draft_content_changed = update_data["html_content"] != landing_page.draft_content
            landing_page.draft_content = update_data["html_content"]
            del update_data["html_content"]

            # 同步更新 S3 文件（覆盖同一个文件，不产生新副本）
            if draft_content_changed and landing_page.s3_key:
                landing_pages_storage.upload_file(
                    key=landing_page.s3_key,
                    data=landing_page.draft_content.encode("utf-8"),
                    content_type="text/html; charset=utf-8",
                )

            # 如果草稿内容变化，标记为有未发布的更改
            if draft_content_changed and landing_page.status == LandingPageStatus.PUBLISHED.value:
                # 保持 published 状态，但标记有未发布的更改（通过比较 draft 和 published content）
                pass  # 状态不变，通过 has_unpublished_changes 属性判断

        for field, value in update_data.items():
            setattr(landing_page, field, value)

        landing_page.updated_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(landing_page)

        return landing_page

    async def delete(
        self,
        landing_page_id: int,
        user_id: int,
        hard_delete: bool = False,
    ) -> bool:
        """Delete a landing page.

        Args:
            landing_page_id: Landing page ID
            user_id: Owner user ID
            hard_delete: If True, permanently delete; otherwise archive

        Returns:
            True if deleted successfully

        Raises:
            LandingPageNotFoundError: If landing page not found or not owned by user
        """
        landing_page = await self.get_by_id(landing_page_id, user_id)

        if not landing_page:
            raise LandingPageNotFoundError(landing_page_id)

        if hard_delete:
            # Delete S3 file
            try:
                if landing_page.s3_key:
                    landing_pages_storage.delete_file(landing_page.s3_key)
            except Exception:
                # Log but don't fail if S3 deletion fails
                pass

            await self.db.delete(landing_page)
        else:
            # Soft delete (archive)
            landing_page.status = LandingPageStatus.ARCHIVED.value
            landing_page.updated_at = datetime.utcnow()

        await self.db.flush()
        return True

    async def publish(
        self,
        landing_page_id: int,
        user_id: int,
    ) -> LandingPage:
        """Publish a landing page to S3 and CloudFront CDN.

        Args:
            landing_page_id: Landing page ID
            user_id: Owner user ID

        Returns:
            Updated LandingPage instance with published status

        Raises:
            LandingPageNotFoundError: If landing page not found or not owned by user
            ValueError: If landing page has no HTML content
        """
        landing_page = await self.get_by_id(landing_page_id, user_id)

        if not landing_page:
            raise LandingPageNotFoundError(landing_page_id)

        if not landing_page.draft_content:
            raise ValueError("Landing page has no draft content to publish")

        # 准备发布内容
        html_to_publish = landing_page.draft_content

        # 如果配置了 GA4 Measurement ID，注入追踪代码
        if landing_page.ga_measurement_id:
            ga_script = f'''
<!-- Google Analytics 4 -->
<script async src="https://www.googletagmanager.com/gtag/js?id={landing_page.ga_measurement_id}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{landing_page.ga_measurement_id}');
</script>
'''
            # 在 </head> 前注入 GA4 代码
            if "</head>" in html_to_publish:
                html_to_publish = html_to_publish.replace("</head>", f"{ga_script}</head>")
            elif "<body" in html_to_publish:
                # 如果没有 </head>，在 <body 前注入
                html_to_publish = html_to_publish.replace("<body", f"{ga_script}<body")

        # 发布时：从 drafts/ 路径移动到正式路径
        # Extract unique_id from draft s3_key
        # Format: users/{user_id}/landing-pages/drafts/{unique_id}/index.html
        import re
        match = re.search(r'/drafts/([a-f0-9]+)/', landing_page.s3_key)
        if not match:
            # Fallback: 如果不是 drafts 路径，使用原 key（可能已发布过）
            unique_id = landing_page.s3_key.split('/')[-2] if '/' in landing_page.s3_key else uuid.uuid4().hex
        else:
            unique_id = match.group(1)

        # 生成正式发布路径（去掉 drafts/）
        published_s3_key = f"users/{user_id}/landing-pages/{unique_id}/index.html"

        # Upload HTML to published path (with GA4 tracking if configured)
        landing_pages_storage.upload_file(
            key=published_s3_key,
            data=html_to_publish.encode("utf-8"),
            content_type="text/html; charset=utf-8",
        )

        # 删除 drafts/ 下的旧文件（节省存储空间）
        if landing_page.s3_key != published_s3_key:
            try:
                landing_pages_storage.delete_file(landing_page.s3_key)
            except Exception:
                # Log but don't fail if deletion fails
                pass

        # Update status and metadata
        landing_page.html_content = landing_page.draft_content  # 复制草稿到已发布版本
        landing_page.status = LandingPageStatus.PUBLISHED.value
        landing_page.s3_key = published_s3_key  # 更新到正式路径
        landing_page.url = landing_pages_storage.get_cdn_url(published_s3_key)  # 使用 CloudFront URL
        landing_page.published_at = datetime.utcnow()
        landing_page.updated_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(landing_page)

        return landing_page

    async def get_by_ids(
        self,
        landing_page_ids: list[int],
        user_id: int,
    ) -> list[LandingPage]:
        """Get multiple landing pages by IDs.

        Args:
            landing_page_ids: List of landing page IDs
            user_id: Owner user ID

        Returns:
            List of LandingPage instances
        """
        if not landing_page_ids:
            return []

        result = await self.db.execute(
            select(LandingPage)
            .where(LandingPage.id.in_(landing_page_ids))
            .where(LandingPage.user_id == user_id)
            .where(LandingPage.status != LandingPageStatus.ARCHIVED.value)
        )
        return list(result.scalars().all())
