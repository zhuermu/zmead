"""
Upload manager for creative files.

Requirements: 2.3, 4.1.1, 4.1.2, 4.1.3
- Get presigned URLs from Web Platform via MCP
- Upload files to S3 using presigned URLs
- Store metadata via MCP after successful upload
- Retry failed uploads up to 3 times
"""

import asyncio
from typing import Any

import httpx
import structlog

from app.services.mcp_client import MCPClient, MCPError, MCPConnectionError

from ..models import GeneratedImage, UploadResult
from ..utils.validators import FileValidator, FileValidationError

logger = structlog.get_logger(__name__)


class UploadError(Exception):
    """Exception raised when upload fails."""

    def __init__(
        self,
        message: str,
        error_code: str = "UPLOAD_ERROR",
        retryable: bool = True,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.retryable = retryable


class UploadManager:
    """Manages file uploads to S3 via MCP.

    Handles:
    - Getting presigned URLs from Web Platform
    - Uploading files to S3
    - Storing metadata via MCP
    - Retry logic with exponential backoff

    Example:
        async with MCPClient() as mcp:
            manager = UploadManager(mcp)
            result = await manager.upload_creative(
                user_id="user123",
                image=generated_image,
                metadata={"style": "modern"}
            )
    """

    UPLOAD_TIMEOUT: int = 60  # seconds
    MAX_RETRIES: int = 3
    BACKOFF_BASE: float = 1.0
    BACKOFF_FACTOR: float = 2.0

    def __init__(self, mcp_client: MCPClient | None = None):
        """Initialize upload manager.

        Args:
            mcp_client: MCP client for Web Platform communication
        """
        self.mcp = mcp_client
        self.validator = FileValidator()
        self._http_client: httpx.AsyncClient | None = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for S3 uploads."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.UPLOAD_TIMEOUT),
                limits=httpx.Limits(
                    max_keepalive_connections=10,
                    max_connections=50,
                ),
            )
        return self._http_client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

    async def get_presigned_url(
        self,
        user_id: str,
        file_name: str,
        file_type: str,
        file_size: int,
    ) -> dict[str, Any]:
        """Get S3 presigned upload URL from Web Platform.

        Calls MCP tool 'get_upload_url' to get a presigned URL
        for uploading files directly to S3.

        Args:
            user_id: User ID
            file_name: Name of the file
            file_type: MIME type (image/jpeg or image/png)
            file_size: Size in bytes

        Returns:
            Dict with:
                - upload_url: Presigned URL for PUT request
                - file_url: CDN URL where file will be accessible

        Raises:
            UploadError: If MCP call fails
        """
        if self.mcp is None:
            raise UploadError(
                message="MCP client not initialized",
                error_code="MCP_NOT_INITIALIZED",
                retryable=False,
            )

        log = logger.bind(
            user_id=user_id,
            file_name=file_name,
            file_type=file_type,
            file_size=file_size,
        )
        log.info("get_presigned_url_start")

        try:
            result = await self.mcp.call_tool(
                "get_upload_url",
                {
                    "user_id": user_id,
                    "file_name": file_name,
                    "file_type": file_type,
                    "file_size": file_size,
                    "purpose": "creative",
                },
            )

            log.info(
                "get_presigned_url_success",
                file_url=result.get("file_url"),
            )

            return {
                "upload_url": result["upload_url"],
                "file_url": result["file_url"],
            }

        except MCPError as e:
            log.error("get_presigned_url_failed", error=str(e))
            raise UploadError(
                message=f"获取上传 URL 失败: {e.message}",
                error_code=e.code or "MCP_ERROR",
                retryable=isinstance(e, MCPConnectionError),
            ) from e

    async def upload_to_s3(
        self,
        upload_url: str,
        file_data: bytes,
        content_type: str,
    ) -> None:
        """Upload file to S3 using presigned URL.

        Uses HTTP PUT request to upload file directly to S3.
        The presigned URL already contains authentication.

        Args:
            upload_url: Presigned upload URL
            file_data: File bytes
            content_type: MIME type

        Raises:
            UploadError: If upload fails
        """
        log = logger.bind(
            content_type=content_type,
            file_size=len(file_data),
        )
        log.info("s3_upload_start")

        client = await self._get_http_client()

        try:
            response = await client.put(
                upload_url,
                content=file_data,
                headers={
                    "Content-Type": content_type,
                    "Content-Length": str(len(file_data)),
                },
            )

            if response.status_code not in (200, 201, 204):
                log.error(
                    "s3_upload_failed",
                    status_code=response.status_code,
                    response_text=response.text[:200] if response.text else None,
                )
                raise UploadError(
                    message=f"S3 上传失败: HTTP {response.status_code}",
                    error_code="S3_UPLOAD_FAILED",
                    retryable=response.status_code >= 500,
                )

            log.info("s3_upload_success")

        except httpx.TimeoutException as e:
            log.error("s3_upload_timeout", error=str(e))
            raise UploadError(
                message="S3 上传超时",
                error_code="S3_UPLOAD_TIMEOUT",
                retryable=True,
            ) from e

        except httpx.HTTPError as e:
            log.error("s3_upload_http_error", error=str(e))
            raise UploadError(
                message=f"S3 上传网络错误: {e}",
                error_code="S3_UPLOAD_HTTP_ERROR",
                retryable=True,
            ) from e

    async def _create_creative_metadata(
        self,
        user_id: str,
        file_url: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Store creative metadata via MCP.

        Args:
            user_id: User ID
            file_url: CDN URL of uploaded file
            metadata: Additional metadata

        Returns:
            Created creative data with creative_id

        Raises:
            UploadError: If MCP call fails
        """
        if self.mcp is None:
            raise UploadError(
                message="MCP client not initialized",
                error_code="MCP_NOT_INITIALIZED",
                retryable=False,
            )

        log = logger.bind(user_id=user_id, file_url=file_url)
        log.info("create_creative_metadata_start")

        try:
            result = await self.mcp.call_tool(
                "create_creative",
                {
                    "user_id": user_id,
                    "file_url": file_url,
                    "metadata": metadata,
                },
            )

            log.info(
                "create_creative_metadata_success",
                creative_id=result.get("creative_id"),
            )

            return result

        except MCPError as e:
            log.error("create_creative_metadata_failed", error=str(e))
            raise UploadError(
                message=f"保存素材元数据失败: {e.message}",
                error_code=e.code or "MCP_ERROR",
                retryable=isinstance(e, MCPConnectionError),
            ) from e

    async def upload_creative(
        self,
        user_id: str,
        image: GeneratedImage,
        metadata: dict[str, Any],
    ) -> UploadResult:
        """Upload a creative to S3 with full flow.

        Complete upload flow:
        1. Validate file format and size
        2. Get presigned URL from Web Platform (MCP)
        3. Upload file to S3 using presigned URL
        4. Store metadata via MCP

        Implements retry logic with exponential backoff for
        transient failures (up to 3 retries).

        Args:
            user_id: User ID
            image: Generated image to upload
            metadata: Additional metadata (style, platform, etc.)

        Returns:
            UploadResult with creative_id and CDN URL

        Raises:
            FileValidationError: If file validation fails
            UploadError: If upload fails after retries
        """
        log = logger.bind(
            user_id=user_id,
            file_name=image.file_name,
            file_type=image.file_type,
            file_size=len(image.image_data),
        )
        log.info("upload_creative_start")

        # Step 1: Validate file
        self.validator.validate_or_raise(
            file_data=image.image_data,
            file_type=image.file_type,
            file_size=len(image.image_data),
        )

        last_error: Exception | None = None

        for attempt in range(self.MAX_RETRIES):
            try:
                # Step 2: Get presigned URL
                url_info = await self.get_presigned_url(
                    user_id=user_id,
                    file_name=image.file_name,
                    file_type=image.file_type,
                    file_size=len(image.image_data),
                )

                # Step 3: Upload to S3
                await self.upload_to_s3(
                    upload_url=url_info["upload_url"],
                    file_data=image.image_data,
                    content_type=image.file_type,
                )

                # Step 4: Store metadata
                creative_metadata = {
                    **metadata,
                    "width": image.width,
                    "height": image.height,
                    "aspect_ratio": image.aspect_ratio,
                    "file_type": image.file_type,
                    "file_size": len(image.image_data),
                }

                result = await self._create_creative_metadata(
                    user_id=user_id,
                    file_url=url_info["file_url"],
                    metadata=creative_metadata,
                )

                log.info(
                    "upload_creative_success",
                    creative_id=result.get("creative_id"),
                    attempt=attempt + 1,
                )

                return UploadResult(
                    creative_id=result["creative_id"],
                    url=result.get("url", url_info["file_url"]),
                    created_at=result.get("created_at", ""),
                )

            except FileValidationError:
                # Don't retry validation errors
                raise

            except UploadError as e:
                last_error = e

                if not e.retryable:
                    log.error(
                        "upload_creative_failed_not_retryable",
                        error=str(e),
                        error_code=e.error_code,
                    )
                    raise

                if attempt < self.MAX_RETRIES - 1:
                    wait_time = self.BACKOFF_BASE * (self.BACKOFF_FACTOR ** attempt)
                    log.warning(
                        "upload_creative_retry",
                        attempt=attempt + 1,
                        max_retries=self.MAX_RETRIES,
                        wait_seconds=wait_time,
                        error=str(e),
                    )
                    await asyncio.sleep(wait_time)
                else:
                    log.error(
                        "upload_creative_failed_max_retries",
                        attempt=attempt + 1,
                        error=str(e),
                    )
                    raise UploadError(
                        message="素材上传失败，已达到最大重试次数",
                        error_code="5003",  # STORAGE_ERROR
                        retryable=False,
                    ) from e

        # Should not reach here
        if last_error:
            raise last_error
        raise UploadError(
            message="素材上传失败",
            error_code="5003",
            retryable=False,
        )

    async def upload_multiple(
        self,
        user_id: str,
        images: list[GeneratedImage],
        metadata: dict[str, Any],
    ) -> list[UploadResult]:
        """Upload multiple creatives.

        Uploads images sequentially to avoid overwhelming S3.
        Continues on individual failures, collecting results.

        Args:
            user_id: User ID
            images: List of generated images
            metadata: Base metadata for all images

        Returns:
            List of UploadResult for successful uploads
        """
        results: list[UploadResult] = []
        errors: list[tuple[int, Exception]] = []

        for i, image in enumerate(images):
            try:
                result = await self.upload_creative(
                    user_id=user_id,
                    image=image,
                    metadata={**metadata, "index": i},
                )
                results.append(result)
            except Exception as e:
                logger.error(
                    "upload_multiple_item_failed",
                    index=i,
                    error=str(e),
                )
                errors.append((i, e))

        if errors and not results:
            # All uploads failed
            raise UploadError(
                message=f"所有素材上传失败: {len(errors)} 个错误",
                error_code="5003",
                retryable=False,
            )

        return results
