"""
Creative library manager for managing user's creative assets.

Requirements: 6.2, 6.3, 8.1, 8.2, 8.3, 8.4
- Get creatives list with filtering and sorting
- Delete creatives
- Download single creative
- Batch download multiple creatives
- Capacity warning when library exceeds 100 items
"""

from typing import Any, Literal
from datetime import datetime

import structlog

from app.services.mcp_client import MCPClient, MCPError, MCPConnectionError

from ..models import Creative, GetCreativesRequest, GetCreativesResponse

logger = structlog.get_logger(__name__)


class CreativeManagerError(Exception):
    """Exception raised when creative management operations fail."""

    def __init__(
        self,
        message: str,
        error_code: str = "CREATIVE_MANAGER_ERROR",
        retryable: bool = False,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.retryable = retryable


class CreativeManager:
    """Manages creative library operations.

    Handles:
    - Listing creatives with filtering and sorting
    - Deleting creatives
    - Downloading single or multiple creatives
    - Capacity warnings

    Example:
        async with MCPClient() as mcp:
            manager = CreativeManager(mcp)
            response = await manager.get_creatives(
                user_id="user123",
                request=GetCreativesRequest(
                    filters={"platform": "tiktok"},
                    sort_by="score",
                    sort_order="desc"
                )
            )
    """

    CAPACITY_WARNING_THRESHOLD: int = 100

    def __init__(self, mcp_client: MCPClient | None = None):
        """Initialize creative manager.

        Args:
            mcp_client: MCP client for Web Platform communication
        """
        self.mcp = mcp_client

    def _ensure_mcp_client(self) -> None:
        """Ensure MCP client is initialized."""
        if self.mcp is None:
            raise CreativeManagerError(
                message="MCP client not initialized",
                error_code="MCP_NOT_INITIALIZED",
                retryable=False,
            )

    async def get_creatives(
        self,
        user_id: str,
        request: GetCreativesRequest | None = None,
    ) -> GetCreativesResponse:
        """Get user's creatives list with filtering and sorting.

        Calls MCP tool 'get_creatives' to retrieve creatives from Web Platform.
        Supports filtering by tags, date range, score range, and platform.
        Results are sorted by score (descending) by default.

        Args:
            user_id: User ID
            request: Request parameters for filtering and sorting

        Returns:
            GetCreativesResponse with creatives list and metadata

        Raises:
            CreativeManagerError: If MCP call fails
        """
        self._ensure_mcp_client()

        if request is None:
            request = GetCreativesRequest()

        log = logger.bind(
            user_id=user_id,
            filters=request.filters,
            sort_by=request.sort_by,
            sort_order=request.sort_order,
            limit=request.limit,
            offset=request.offset,
        )
        log.info("get_creatives_start")

        try:
            result = await self.mcp.call_tool(
                "get_creatives",
                {
                    "user_id": user_id,
                    "filters": request.filters,
                    "sort_by": request.sort_by,
                    "sort_order": request.sort_order,
                    "limit": request.limit,
                    "offset": request.offset,
                },
            )

            # Parse creatives from result
            creatives_data = result.get("creatives", [])
            creatives = [
                self._parse_creative(c) for c in creatives_data
            ]

            # Sort by score descending (Requirements 7.5)
            creatives = self._sort_creatives(
                creatives,
                sort_by=request.sort_by,
                sort_order=request.sort_order,
            )

            total = result.get("total", len(creatives))

            # Check capacity warning (Requirements 8.5)
            capacity_warning = total >= self.CAPACITY_WARNING_THRESHOLD

            log.info(
                "get_creatives_success",
                count=len(creatives),
                total=total,
                capacity_warning=capacity_warning,
            )

            return GetCreativesResponse(
                status="success",
                creatives=creatives,
                total=total,
                message="素材列表获取成功",
                capacity_warning=capacity_warning,
            )

        except MCPError as e:
            log.error("get_creatives_failed", error=str(e))
            raise CreativeManagerError(
                message=f"获取素材列表失败: {e.message}",
                error_code=e.code or "MCP_ERROR",
                retryable=isinstance(e, MCPConnectionError),
            ) from e

    def _parse_creative(self, data: dict[str, Any]) -> Creative:
        """Parse creative data from MCP response.

        Args:
            data: Raw creative data from MCP

        Returns:
            Creative model instance
        """
        return Creative(
            creative_id=data.get("creative_id", data.get("id", "")),
            user_id=data.get("user_id", ""),
            url=data.get("url", data.get("file_url", "")),
            thumbnail_url=data.get("thumbnail_url"),
            product_url=data.get("product_url"),
            style=data.get("style"),
            aspect_ratio=data.get("aspect_ratio", "1:1"),
            platform=data.get("platform"),
            score=data.get("score"),
            score_dimensions=data.get("score_dimensions"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at"),
            tags=data.get("tags", []),
        )

    def _sort_creatives(
        self,
        creatives: list[Creative],
        sort_by: str = "score",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> list[Creative]:
        """Sort creatives by specified field.

        Args:
            creatives: List of creatives to sort
            sort_by: Field to sort by (score, created_at, updated_at)
            sort_order: Sort order (asc or desc)

        Returns:
            Sorted list of creatives
        """
        reverse = sort_order == "desc"

        def get_sort_key(c: Creative) -> Any:
            if sort_by == "score":
                # None scores go to the end
                return c.score if c.score is not None else -1
            elif sort_by == "created_at":
                return c.created_at or ""
            elif sort_by == "updated_at":
                return c.updated_at or ""
            else:
                return c.score if c.score is not None else -1

        return sorted(creatives, key=get_sort_key, reverse=reverse)

    async def delete_creative(
        self,
        user_id: str,
        creative_id: str,
    ) -> dict[str, Any]:
        """Delete a creative from user's library.

        Calls MCP tool 'delete_creative' to remove the creative.
        The file is also deleted from S3 storage.

        Args:
            user_id: User ID
            creative_id: ID of the creative to delete

        Returns:
            Dict with success status and message

        Raises:
            CreativeManagerError: If deletion fails
        """
        self._ensure_mcp_client()

        log = logger.bind(
            user_id=user_id,
            creative_id=creative_id,
        )
        log.info("delete_creative_start")

        try:
            result = await self.mcp.call_tool(
                "delete_creative",
                {
                    "user_id": user_id,
                    "creative_id": creative_id,
                },
            )

            log.info(
                "delete_creative_success",
                deleted=result.get("deleted", True),
            )

            return {
                "status": "success",
                "creative_id": creative_id,
                "message": "素材删除成功",
            }

        except MCPError as e:
            log.error("delete_creative_failed", error=str(e))

            # Check if it's a not found error
            if e.code == "RESOURCE_NOT_FOUND":
                raise CreativeManagerError(
                    message="素材不存在或已被删除",
                    error_code="CREATIVE_NOT_FOUND",
                    retryable=False,
                ) from e

            raise CreativeManagerError(
                message=f"删除素材失败: {e.message}",
                error_code=e.code or "MCP_ERROR",
                retryable=isinstance(e, MCPConnectionError),
            ) from e

    async def download_creative(
        self,
        user_id: str,
        creative_id: str,
    ) -> dict[str, Any]:
        """Get download URL for a single creative.

        Generates a presigned download URL for the creative file.
        The URL is valid for a limited time (typically 1 hour).

        Args:
            user_id: User ID
            creative_id: ID of the creative to download

        Returns:
            Dict with download_url and metadata

        Raises:
            CreativeManagerError: If download URL generation fails
        """
        self._ensure_mcp_client()

        log = logger.bind(
            user_id=user_id,
            creative_id=creative_id,
        )
        log.info("download_creative_start")

        try:
            # First get the creative details
            creative_result = await self.mcp.call_tool(
                "get_creative",
                {
                    "user_id": user_id,
                    "creative_id": creative_id,
                },
            )

            # Get download URL
            download_result = await self.mcp.call_tool(
                "get_download_url",
                {
                    "user_id": user_id,
                    "creative_id": creative_id,
                },
            )

            log.info(
                "download_creative_success",
                has_url=bool(download_result.get("download_url")),
            )

            return {
                "status": "success",
                "creative_id": creative_id,
                "download_url": download_result.get("download_url"),
                "file_name": creative_result.get("file_name", f"{creative_id}.png"),
                "file_type": creative_result.get("file_type", "image/png"),
                "expires_at": download_result.get("expires_at"),
                "message": "下载链接生成成功",
            }

        except MCPError as e:
            log.error("download_creative_failed", error=str(e))

            if e.code == "RESOURCE_NOT_FOUND":
                raise CreativeManagerError(
                    message="素材不存在",
                    error_code="CREATIVE_NOT_FOUND",
                    retryable=False,
                ) from e

            raise CreativeManagerError(
                message=f"获取下载链接失败: {e.message}",
                error_code=e.code or "MCP_ERROR",
                retryable=isinstance(e, MCPConnectionError),
            ) from e

    async def batch_download(
        self,
        user_id: str,
        creative_ids: list[str],
    ) -> dict[str, Any]:
        """Get download URL for multiple creatives as a ZIP archive.

        Generates a presigned download URL for a ZIP file containing
        all requested creatives. The ZIP is created on-demand.

        Args:
            user_id: User ID
            creative_ids: List of creative IDs to download

        Returns:
            Dict with download_url for the ZIP archive

        Raises:
            CreativeManagerError: If batch download fails
        """
        self._ensure_mcp_client()

        if not creative_ids:
            raise CreativeManagerError(
                message="请选择至少一个素材进行下载",
                error_code="INVALID_REQUEST",
                retryable=False,
            )

        log = logger.bind(
            user_id=user_id,
            creative_count=len(creative_ids),
        )
        log.info("batch_download_start")

        try:
            result = await self.mcp.call_tool(
                "batch_download_creatives",
                {
                    "user_id": user_id,
                    "creative_ids": creative_ids,
                },
            )

            log.info(
                "batch_download_success",
                has_url=bool(result.get("download_url")),
                file_count=result.get("file_count", len(creative_ids)),
            )

            return {
                "status": "success",
                "download_url": result.get("download_url"),
                "file_name": result.get("file_name", "creatives.zip"),
                "file_count": result.get("file_count", len(creative_ids)),
                "expires_at": result.get("expires_at"),
                "message": f"批量下载链接生成成功，共 {len(creative_ids)} 个素材",
            }

        except MCPError as e:
            log.error("batch_download_failed", error=str(e))

            raise CreativeManagerError(
                message=f"批量下载失败: {e.message}",
                error_code=e.code or "MCP_ERROR",
                retryable=isinstance(e, MCPConnectionError),
            ) from e

    async def get_creative_count(self, user_id: str) -> int:
        """Get total count of user's creatives.

        Args:
            user_id: User ID

        Returns:
            Total number of creatives
        """
        self._ensure_mcp_client()

        try:
            result = await self.mcp.call_tool(
                "get_creatives",
                {
                    "user_id": user_id,
                    "limit": 1,
                    "offset": 0,
                },
            )
            return result.get("total", 0)

        except MCPError:
            return 0

    async def check_capacity_warning(self, user_id: str) -> bool:
        """Check if user's creative library exceeds capacity threshold.

        Args:
            user_id: User ID

        Returns:
            True if capacity warning should be shown
        """
        count = await self.get_creative_count(user_id)
        return count >= self.CAPACITY_WARNING_THRESHOLD

    async def filter_creatives(
        self,
        user_id: str,
        tags: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        score_min: float | None = None,
        score_max: float | None = None,
        platform: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> GetCreativesResponse:
        """Filter creatives with specific criteria.

        Convenience method that builds filter dict and calls get_creatives.

        Args:
            user_id: User ID
            tags: Filter by tags (any match)
            date_from: Filter by creation date (ISO format)
            date_to: Filter by creation date (ISO format)
            score_min: Minimum score filter
            score_max: Maximum score filter
            platform: Filter by target platform
            limit: Maximum results to return
            offset: Pagination offset

        Returns:
            GetCreativesResponse with filtered results
        """
        filters: dict[str, Any] = {}

        if tags:
            filters["tags"] = tags
        if date_from:
            filters["date_from"] = date_from
        if date_to:
            filters["date_to"] = date_to
        if score_min is not None:
            filters["score_min"] = score_min
        if score_max is not None:
            filters["score_max"] = score_max
        if platform:
            filters["platform"] = platform

        request = GetCreativesRequest(
            filters=filters,
            sort_by="score",
            sort_order="desc",
            limit=limit,
            offset=offset,
        )

        return await self.get_creatives(user_id, request)
