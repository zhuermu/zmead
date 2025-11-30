"""Save creative node for persisting temp creatives to asset library.

This node is triggered when user explicitly requests to save generated creatives.
It retrieves temp creatives from Redis and saves them to the backend via MCP.

Flow:
1. User generates creatives (stored in Redis temp storage + GCS)
2. User previews and says "save" / "保存素材"
3. This node retrieves temp creatives from Redis
4. Calls MCP create_creative to save to backend asset library
5. Deletes temp storage entries

Requirements: Optimized creative generation flow
"""

import structlog
from typing import Any

from app.core.errors import ErrorHandler
from app.core.retry import retry_async
from app.core.state import AgentState
from app.services.mcp_client import MCPClient, MCPError
from app.services.temp_storage import (
    get_temp_creative,
    get_temp_batch,
    delete_temp_creative,
    delete_temp_batch,
    list_user_temp_creatives,
)

logger = structlog.get_logger(__name__)


async def create_creative_record_via_mcp(
    mcp_client: MCPClient,
    gcs_url: str,
    public_url: str,
    file_size: int,
    name: str,
    style: str | None,
    score: int,
    product_url: str | None,
    tags: list[str],
) -> dict[str, Any]:
    """Create creative record in database via MCP.

    Args:
        mcp_client: MCP client instance
        gcs_url: GCS URL of the file
        public_url: Public URL of the file
        file_size: File size in bytes
        name: Creative name
        style: Creative style
        score: Quality score
        product_url: Product URL
        tags: Tags for the creative

    Returns:
        Created creative record
    """
    return await mcp_client.call_tool(
        "create_creative",
        {
            "file_url": gcs_url,
            "cdn_url": public_url,
            "file_type": "image",
            "file_size": file_size,
            "name": name,
            "style": style,
            "score": score,
            "product_url": product_url,
            "tags": tags,
        },
    )


async def save_creative_node(state: AgentState) -> dict[str, Any]:
    """Save creative node for persisting temp creatives to asset library.

    This node:
    1. Retrieves temp creatives from Redis
    2. Creates permanent records via MCP
    3. Cleans up temp storage

    Args:
        state: Current agent state

    Returns:
        State updates with saved creative IDs
    """
    log = logger.bind(
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
        module="save_creative",
    )
    log.info("save_creative_node_start")

    user_id = state.get("user_id", "")
    session_id = state.get("session_id", "")

    # Get pending actions for save_creative
    pending_actions = state.get("pending_actions", [])
    save_actions = [a for a in pending_actions if a.get("module") == "save_creative"]

    if not save_actions:
        log.warning("save_creative_node_no_actions")
        return {"completed_results": []}

    action = save_actions[0]
    params = action.get("params", {})

    # Get temp IDs from params or from state
    temp_ids = params.get("temp_ids", [])
    batch_id = params.get("batch_id")

    # If batch_id provided, get temp_ids from batch
    if batch_id and not temp_ids:
        temp_ids = await get_temp_batch(user_id, batch_id)
        if not temp_ids:
            log.warning("save_creative_batch_not_found", batch_id=batch_id)

    # If still no temp_ids, try to get from previous state or list all
    if not temp_ids:
        temp_creatives_state = state.get("temp_creatives", {})
        temp_ids = temp_creatives_state.get("temp_ids", [])
        batch_id = temp_creatives_state.get("batch_id")

    # If still no temp_ids, list all user's temp creatives
    if not temp_ids:
        temp_list = await list_user_temp_creatives(user_id)
        temp_ids = [t["temp_id"] for t in temp_list]

    if not temp_ids:
        log.warning("save_creative_no_temp_creatives")
        return {
            "completed_results": [
                {
                    "action_type": "save_creative",
                    "module": "save_creative",
                    "status": "error",
                    "data": {},
                    "error": {
                        "code": "NO_TEMP_CREATIVES",
                        "type": "NO_TEMP_CREATIVES",
                        "message": "没有找到待保存的素材。素材预览可能已过期，请重新生成。",
                    },
                    "cost": 0,
                    "mock": False,
                }
            ]
        }

    saved_creatives: list[dict[str, Any]] = []
    failed_ids: list[str] = []

    try:
        async with MCPClient() as mcp:
            for temp_id in temp_ids:
                try:
                    # Get temp creative metadata from Redis
                    temp_creative = await get_temp_creative(user_id, temp_id)
                    if not temp_creative:
                        log.warning("save_creative_temp_not_found", temp_id=temp_id)
                        failed_ids.append(temp_id)
                        continue

                    # GCS URLs are now stored directly on TempCreative (not in analysis)
                    gcs_url = temp_creative.gcs_url
                    public_url = temp_creative.public_url

                    if not gcs_url or not public_url:
                        log.warning("save_creative_no_urls", temp_id=temp_id)
                        failed_ids.append(temp_id)
                        continue

                    # Get file size from analysis if available
                    analysis = temp_creative.analysis
                    file_size = analysis.get("file_size", 0)

                    # Create permanent record via MCP
                    creative_record = await retry_async(
                        lambda: create_creative_record_via_mcp(
                            mcp_client=mcp,
                            gcs_url=gcs_url,
                            public_url=public_url,
                            file_size=file_size,
                            name=temp_creative.filename,
                            style=temp_creative.style,
                            score=temp_creative.score,
                            product_url=None,  # Could be stored in analysis if needed
                            tags=["ai-generated", temp_creative.style],
                        ),
                        max_retries=3,
                        context=f"save_creative_{temp_id}",
                    )

                    saved_creatives.append({
                        "id": creative_record.get("id"),
                        "temp_id": temp_id,
                        "name": temp_creative.filename,
                        "url": public_url,
                        "style": temp_creative.style,
                        "score": temp_creative.score,
                        "status": "saved",
                    })

                    # Delete temp storage entry
                    await delete_temp_creative(user_id, temp_id)

                    log.info(
                        "save_creative_saved",
                        temp_id=temp_id,
                        creative_id=creative_record.get("id"),
                    )

                except MCPError as e:
                    log.error(
                        "save_creative_mcp_error",
                        temp_id=temp_id,
                        error=str(e),
                    )
                    failed_ids.append(temp_id)
                    continue

                except Exception as e:
                    log.error(
                        "save_creative_error",
                        temp_id=temp_id,
                        error=str(e),
                    )
                    failed_ids.append(temp_id)
                    continue

            # Clean up batch reference if all saved
            if batch_id and not failed_ids:
                await delete_temp_batch(user_id, batch_id)

    except Exception as e:
        log.error("save_creative_unexpected_error", error=str(e), exc_info=True)
        error_state = ErrorHandler.create_node_error_state(
            error=e,
            node_name="save_creative",
            user_id=user_id,
            session_id=session_id,
        )
        error_state["completed_results"] = [
            {
                "action_type": "save_creative",
                "module": "save_creative",
                "status": "error",
                "data": {"partial_results": saved_creatives},
                "error": error_state.get("error"),
                "cost": 0,
                "mock": False,
            }
        ]
        return error_state

    # Build result
    if not saved_creatives:
        return {
            "completed_results": [
                {
                    "action_type": "save_creative",
                    "module": "save_creative",
                    "status": "error",
                    "data": {},
                    "error": {
                        "code": "SAVE_FAILED",
                        "type": "SAVE_FAILED",
                        "message": "保存素材失败，请稍后重试。",
                    },
                    "cost": 0,
                    "mock": False,
                }
            ]
        }

    result = {
        "action_type": "save_creative",
        "module": "save_creative",
        "status": "success",
        "data": {
            "saved_creatives": saved_creatives,
            "saved_ids": [c["id"] for c in saved_creatives],
            "count": len(saved_creatives),
            "failed_count": len(failed_ids),
            "message": f"已保存 {len(saved_creatives)} 张素材到素材库",
        },
        "error": None,
        "cost": 0,
        "mock": False,
    }

    log.info(
        "save_creative_node_complete",
        saved_count=len(saved_creatives),
        failed_count=len(failed_ids),
    )

    return {
        "completed_results": [result],
        # Clear temp_creatives from state after save
        "temp_creatives": None,
    }
