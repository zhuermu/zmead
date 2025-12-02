"""Temporary metadata storage service for generated creatives.

Stores creative metadata in Redis for tracking which creatives are pending save.
The actual images are PERMANENTLY stored in GCS for chat history display.

IMPORTANT: Images are NEVER stored in Redis. Only metadata is stored here.
- GCS stores the actual images permanently (they never expire)
- Redis only stores metadata (GCS URLs, analysis, etc.) for tracking saves
- When Redis metadata expires, images are still accessible via their GCS URLs
- Chat history can always display images using the permanent GCS URLs

This service only stores metadata to track:
- Which creatives are available for saving to asset library
- GCS URLs and analysis data
- User/session associations

Flow:
1. generate_creative -> uploads images to GCS (PERMANENT), stores metadata in Redis
2. User previews images in chat (GCS URLs always accessible, never expire)
3. User says "save" -> save_creative creates record in backend via MCP
4. Metadata expires from Redis after TTL (images REMAIN in GCS permanently)

Requirements: Optimized creative generation flow
"""

import json
import uuid
from dataclasses import dataclass
from typing import Any

import structlog

from app.core.redis_client import get_redis

logger = structlog.get_logger(__name__)

# TTL for temporary metadata (30 minutes)
# NOTE: This only affects the Redis metadata, NOT the GCS images which are permanent
TEMP_METADATA_TTL = 1800

# Redis key prefixes
PREFIX_TEMP_METADATA = "temp_creative:metadata"
PREFIX_TEMP_BATCH = "temp_creative:batch"


@dataclass
class TempCreative:
    """Represents metadata for a temporarily tracked creative.

    NOTE: This does NOT contain image data. Images are stored permanently in GCS.
    This only contains metadata for tracking which creatives can be saved to asset library.
    """

    temp_id: str
    gcs_url: str  # Permanent GCS URL (gs://bucket/path)
    public_url: str  # Public URL for display (https://storage.googleapis.com/...)
    filename: str
    style: str
    score: int
    analysis: dict[str, Any]
    created_at: str
    user_id: str
    session_id: str


async def store_temp_creative(
    user_id: str,
    session_id: str,
    gcs_url: str,
    public_url: str,
    filename: str,
    style: str,
    score: int,
    analysis: dict[str, Any],
) -> str:
    """Store creative metadata temporarily in Redis.

    NOTE: This only stores metadata, NOT image data. Images are permanently
    stored in GCS and accessible via the provided URLs.

    Args:
        user_id: User ID
        session_id: Session ID
        gcs_url: Permanent GCS URL (gs://bucket/path)
        public_url: Public URL for display (https://storage.googleapis.com/...)
        filename: Suggested filename
        style: Creative style
        score: Quality score (0-100)
        analysis: Analysis results from Gemini (should include GCS info)

    Returns:
        Temporary ID for this creative
    """
    from datetime import datetime, timezone

    redis = await get_redis()

    # Generate unique temp ID
    temp_id = f"temp_{uuid.uuid4().hex[:12]}"

    # Create metadata structure (NO image data - images are in GCS permanently)
    data = {
        "temp_id": temp_id,
        "gcs_url": gcs_url,
        "public_url": public_url,
        "filename": filename,
        "style": style,
        "score": score,
        "analysis": analysis,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "session_id": session_id,
    }

    # Store metadata in Redis with TTL
    # NOTE: When this expires, the image is STILL accessible via gcs_url/public_url
    cache_key = f"{PREFIX_TEMP_METADATA}:{user_id}:{temp_id}"
    await redis.setex(
        cache_key,
        TEMP_METADATA_TTL,
        json.dumps(data, ensure_ascii=False),
    )

    logger.info(
        "temp_creative_metadata_stored",
        temp_id=temp_id,
        user_id=user_id,
        filename=filename,
        gcs_url=gcs_url,
        ttl=TEMP_METADATA_TTL,
    )

    return temp_id


async def store_temp_batch(
    user_id: str,
    session_id: str,
    temp_ids: list[str],
) -> str:
    """Store a batch reference for multiple temp creatives.

    Args:
        user_id: User ID
        session_id: Session ID
        temp_ids: List of temporary creative IDs

    Returns:
        Batch ID
    """
    redis = await get_redis()

    batch_id = f"batch_{uuid.uuid4().hex[:12]}"

    data = {
        "batch_id": batch_id,
        "temp_ids": temp_ids,
        "user_id": user_id,
        "session_id": session_id,
    }

    cache_key = f"{PREFIX_TEMP_BATCH}:{user_id}:{batch_id}"
    await redis.setex(
        cache_key,
        TEMP_METADATA_TTL,
        json.dumps(data, ensure_ascii=False),
    )

    logger.info(
        "temp_batch_stored",
        batch_id=batch_id,
        user_id=user_id,
        count=len(temp_ids),
    )

    return batch_id


async def get_temp_creative(user_id: str, temp_id: str) -> TempCreative | None:
    """Retrieve metadata for a temporarily tracked creative.

    NOTE: This returns metadata only. The actual image is permanently stored in GCS
    and accessible via the gcs_url/public_url fields.

    Args:
        user_id: User ID
        temp_id: Temporary creative ID

    Returns:
        TempCreative metadata if found, None otherwise
    """
    redis = await get_redis()

    cache_key = f"{PREFIX_TEMP_METADATA}:{user_id}:{temp_id}"
    data_str = await redis.get(cache_key)

    if not data_str:
        logger.debug("temp_creative_metadata_not_found", temp_id=temp_id, user_id=user_id)
        return None

    try:
        data = json.loads(data_str)
        return TempCreative(**data)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error("temp_creative_metadata_parse_error", temp_id=temp_id, error=str(e))
        return None


async def get_temp_batch(user_id: str, batch_id: str) -> list[str] | None:
    """Retrieve temp IDs from a batch.

    Args:
        user_id: User ID
        batch_id: Batch ID

    Returns:
        List of temp IDs if found, None otherwise
    """
    redis = await get_redis()

    cache_key = f"{PREFIX_TEMP_BATCH}:{user_id}:{batch_id}"
    data_str = await redis.get(cache_key)

    if not data_str:
        logger.debug("temp_batch_not_found", batch_id=batch_id, user_id=user_id)
        return None

    try:
        data = json.loads(data_str)
        return data.get("temp_ids", [])
    except json.JSONDecodeError as e:
        logger.error("temp_batch_parse_error", batch_id=batch_id, error=str(e))
        return None


def get_public_url_from_creative(creative: TempCreative) -> str:
    """Get the public URL for a creative's image.

    NOTE: The image is permanently stored in GCS, so this URL never expires.

    Args:
        creative: TempCreative metadata

    Returns:
        Public URL for the image
    """
    return creative.public_url


async def delete_temp_creative(user_id: str, temp_id: str) -> bool:
    """Delete metadata for a temporary creative.

    NOTE: This only deletes the Redis metadata, NOT the GCS image.
    The image remains permanently stored in GCS.

    Args:
        user_id: User ID
        temp_id: Temporary creative ID

    Returns:
        True if metadata was deleted, False otherwise
    """
    redis = await get_redis()

    cache_key = f"{PREFIX_TEMP_METADATA}:{user_id}:{temp_id}"
    result = await redis.delete(cache_key)

    logger.info("temp_creative_metadata_deleted", temp_id=temp_id, deleted=result > 0)
    return result > 0


async def delete_temp_batch(user_id: str, batch_id: str) -> int:
    """Delete a batch and all its temp creative metadata.

    NOTE: This only deletes Redis metadata, NOT GCS images.
    Images remain permanently stored in GCS.

    Args:
        user_id: User ID
        batch_id: Batch ID

    Returns:
        Number of metadata items deleted
    """
    redis = await get_redis()

    # Get batch temp IDs
    temp_ids = await get_temp_batch(user_id, batch_id)
    if not temp_ids:
        return 0

    deleted = 0

    # Delete all temp creative metadata
    for temp_id in temp_ids:
        if await delete_temp_creative(user_id, temp_id):
            deleted += 1

    # Delete batch reference
    batch_key = f"{PREFIX_TEMP_BATCH}:{user_id}:{batch_id}"
    await redis.delete(batch_key)

    logger.info(
        "temp_batch_metadata_deleted",
        batch_id=batch_id,
        deleted_count=deleted,
    )

    return deleted


async def list_user_temp_creatives(user_id: str) -> list[dict[str, Any]]:
    """List all temp creative metadata for a user.

    NOTE: Returns metadata only. Images are permanently stored in GCS
    and accessible via the public_url field.

    Args:
        user_id: User ID

    Returns:
        List of temp creative metadata with GCS URLs
    """
    redis = await get_redis()

    pattern = f"{PREFIX_TEMP_METADATA}:{user_id}:*"
    keys = []

    async for key in redis.scan_iter(match=pattern):
        keys.append(key)

    results = []
    for key in keys:
        data_str = await redis.get(key)
        if data_str:
            try:
                data = json.loads(data_str)
                # Return metadata with GCS URLs
                results.append({
                    "temp_id": data["temp_id"],
                    "filename": data["filename"],
                    "style": data["style"],
                    "score": data["score"],
                    "created_at": data["created_at"],
                    "gcs_url": data.get("gcs_url"),
                    "public_url": data.get("public_url"),
                })
            except json.JSONDecodeError:
                continue

    return results


async def get_temp_creatives(user_id: str, session_id: str) -> dict[str, dict[str, Any]]:
    """Get all temp creative metadata for a user session.

    NOTE: Returns metadata only. Images are permanently stored in GCS
    and accessible via the public_url field.

    Args:
        user_id: User ID
        session_id: Session ID

    Returns:
        Dict mapping temp_id to creative metadata
    """
    redis = await get_redis()

    pattern = f"{PREFIX_TEMP_METADATA}:{user_id}:*"
    keys = []

    async for key in redis.scan_iter(match=pattern):
        keys.append(key)

    results = {}
    for key in keys:
        data_str = await redis.get(key)
        if data_str:
            try:
                data = json.loads(data_str)
                # Filter by session_id if provided
                if data.get("session_id") == session_id:
                    results[data["temp_id"]] = {
                        "temp_id": data["temp_id"],
                        "filename": data["filename"],
                        "style": data["style"],
                        "score": data["score"],
                        "created_at": data["created_at"],
                        "gcs_url": data.get("gcs_url"),
                        "public_url": data.get("public_url"),
                        "analysis": data.get("analysis", {}),
                    }
            except json.JSONDecodeError:
                continue

    return results
