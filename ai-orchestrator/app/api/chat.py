"""Chat API using ReAct Agent architecture.

This module provides the unified chat endpoint using the ReAct Agent:
- Single agent with dynamic tool loading
- Human-in-the-loop for confirmations
- State persistence via Redis
- SSE streaming for real-time responses

Requirements: ReAct Agent v2
"""

import asyncio
import json

import structlog
from fastapi import APIRouter, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.i18n import detect_language, get_message
from app.core.react_agent import ReActAgent
from app.tools.registry import ToolRegistry
# Tool factory imports
from app.tools.langchain_tools import create_langchain_tools
from app.tools.creative_tools import create_creative_tools
from app.tools.campaign_tools import create_campaign_tools
from app.tools.landing_page_tools import create_landing_page_tools
from app.tools.market_tools import create_market_tools
from app.tools.performance_tools import create_performance_tools
from app.tools.mcp_tools import create_mcp_tools
# Gemini Files API service
from app.services.gemini_files import gemini_files_service

logger = structlog.get_logger(__name__)


def _create_agent_with_tools() -> ReActAgent:
    """Create ReActAgent with all tools loaded.

    Tools are organized in 3 categories:
    1. LangChain tools: google_search, calculator, datetime
    2. Agent custom tools (5 capability modules):
       - Creative: generate_image, generate_video, analyze_creative, extract_product_info
       - Campaign: create_campaign, update_campaign, pause_campaign, get_campaigns
       - Landing Page: generate_landing_page, preview_landing_page
       - Market: analyze_competitors, get_market_trends, analyze_audience
       - Performance: get_performance_report, analyze_anomalies, get_recommendations
    3. MCP tools: Tools that interact with backend via MCP protocol
    """
    registry = ToolRegistry()

    # 1. Register LangChain built-in tools
    langchain_tools = create_langchain_tools()
    registry.register_batch(langchain_tools)

    # 2. Register Agent custom tools (5 capability modules)
    creative_tools = create_creative_tools()
    registry.register_batch(creative_tools)

    campaign_tools = create_campaign_tools()
    registry.register_batch(campaign_tools)

    landing_page_tools = create_landing_page_tools()
    registry.register_batch(landing_page_tools)

    market_tools = create_market_tools()
    registry.register_batch(market_tools)

    performance_tools = create_performance_tools()
    registry.register_batch(performance_tools)

    # 3. Register MCP Server tools (backend data interaction)
    mcp_tools = create_mcp_tools()
    registry.register_batch(mcp_tools)

    logger.info(
        "agent_tools_loaded",
        total_tools=len(registry.get_all_tools()),
        stats=registry.get_stats(),
    )

    return ReActAgent(tool_registry=registry)

router = APIRouter()


class MessageAttachment(BaseModel):
    """File attachment with GCS and Gemini info."""
    # New format (preferred)
    gcs_path: str | None = Field(None, description="GCS object path (e.g., user_id/chat-attachments/session_id/file.ext)")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type")
    file_size: int = Field(..., description="File size in bytes")
    download_url: str | None = Field(None, description="Signed download URL (valid for 1 hour)")

    # Legacy format (backward compatibility)
    fileId: str | None = None  # File ID
    contentType: str | None = None  # Use content_type instead
    size: int | None = None  # Use file_size instead
    permanentUrl: str | None = None  # GCS permanent URL (gs://...)
    cdnUrl: str | None = None

    # Gemini File API info (populated after upload)
    geminiFileUri: str | None = None  # Gemini File API URI
    geminiFileName: str | None = None  # Gemini File name
    type: str | None = None  # 'image', 'video', 'document', 'other'


class TempAttachment(BaseModel):
    """Temporary attachment reference (not yet processed)."""
    fileKey: str = Field(..., description="Temporary file key in GCS")
    fileId: str = Field(..., description="Unique file ID")
    filename: str = Field(..., description="Original filename")
    contentType: str = Field(..., description="File content type")
    size: int = Field(..., description="File size in bytes")


class ChatMessage(BaseModel):
    """Single chat message."""
    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")
    attachments: list[MessageAttachment] | None = Field(None, description="File attachments with S3 URLs")
    tempAttachments: list[TempAttachment] | None = Field(None, description="Temporary file attachments (need processing)")


class ChatRequest(BaseModel):
    """Unified chat request model compatible with Vercel AI SDK."""
    messages: list[ChatMessage] = Field(..., description="Conversation messages")
    user_id: str = Field(..., description="User identifier")
    session_id: str = Field(..., description="Session identifier")


@router.post("/chat")
async def chat_stream(
    request: ChatRequest,
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
) -> StreamingResponse:
    """
    Unified chat endpoint with Server-Sent Events streaming.

    This is the main chat endpoint that:
    - Accepts messages array from frontend/backend
    - Uses ReAct Agent for intelligent task processing
    - Streams responses in real-time via SSE
    - Supports human-in-the-loop interactions
    - Supports i18n via Accept-Language header

    Args:
        request: Chat request with messages array, user_id, and session_id
        accept_language: Accept-Language header for i18n (e.g., "zh-CN", "en-US")

    Returns:
        StreamingResponse with SSE events:
        - type: "thinking" - Agent started processing
        - type: "thought" - Agent's reasoning process (streaming)
        - type: "action" - Agent executing a tool
        - type: "observation" - Tool execution result
        - type: "text" - Final response text
        - type: "user_input_request" - Needs user confirmation/input
        - type: "done" - Response complete
        - type: "error" - Error occurred
    """
    language = detect_language(accept_language)
    log = logger.bind(
        user_id=request.user_id,
        session_id=request.session_id,
        language=language,
    )

    # Extract last user message and attachments
    last_message_obj = request.messages[-1] if request.messages else None
    last_message = last_message_obj.content if last_message_obj else ""

    # Handle processed attachments, temp attachments, and new format attachments
    attachments = []

    # Process new-format attachments (with gcs_path)
    if last_message_obj and last_message_obj.attachments:
        log.info("Processing attachments", count=len(last_message_obj.attachments))
        for att in last_message_obj.attachments:
            # Get content type (prefer new format)
            content_type = att.content_type or att.contentType or "application/octet-stream"
            file_size = att.file_size or att.size or 0

            # Build attachment info dict
            attachment_info = {
                "filename": att.filename,
                "contentType": content_type,
                "size": file_size,
                "type": content_type.split('/')[0] if '/' in content_type else 'other',
            }

            # Check if we need to upload to Gemini (new format without geminiFileUri)
            if att.gcs_path and not att.geminiFileUri:
                # New format: download from GCS and upload to Gemini
                from app.core.config import get_settings
                settings = get_settings()
                gcs_uri = f"gs://{settings.gcs_bucket_uploads}/{att.gcs_path}"

                log.info(
                    "Uploading attachment to Gemini",
                    filename=att.filename,
                    gcs_path=att.gcs_path,
                )

                # Upload to Gemini Files API
                gemini_result = gemini_files_service.upload_from_gcs(
                    gcs_uri=gcs_uri,
                    mime_type=content_type,
                    display_name=att.filename,
                )

                if gemini_result:
                    attachment_info["geminiFileUri"] = gemini_result["uri"]
                    attachment_info["geminiFileName"] = gemini_result["name"]
                    log.info(
                        "Uploaded to Gemini",
                        filename=att.filename,
                        gemini_uri=gemini_result["uri"],
                    )
                else:
                    attachment_info["geminiFileUri"] = None
                    attachment_info["geminiFileName"] = None
                    log.warning(
                        "Failed to upload to Gemini",
                        filename=att.filename,
                        gcs_uri=gcs_uri,
                    )
            elif att.geminiFileUri:
                # Already has Gemini URI (legacy or pre-uploaded)
                attachment_info["geminiFileUri"] = att.geminiFileUri
                attachment_info["geminiFileName"] = att.geminiFileName

            attachments.append(attachment_info)

    # Process temp attachments (legacy format) - kept for backward compatibility
    if last_message_obj and last_message_obj.tempAttachments:
        log.info("Processing temp attachments (legacy)", count=len(last_message_obj.tempAttachments))
        from app.core.config import get_settings
        settings = get_settings()

        for temp_att in last_message_obj.tempAttachments:
            # Construct GCS URI (legacy temp bucket)
            gcs_uri = f"gs://{settings.gcs_bucket_uploads}/{temp_att.fileKey}"

            # Upload to Gemini Files API
            gemini_result = gemini_files_service.upload_from_gcs(
                gcs_uri=gcs_uri,
                mime_type=temp_att.contentType,
                display_name=temp_att.filename,
            )

            # Build attachment info
            attachment_info = {
                "fileId": temp_att.fileId,
                "filename": temp_att.filename,
                "contentType": temp_att.contentType,
                "size": temp_att.size,
                "type": temp_att.contentType.split('/')[0] if '/' in temp_att.contentType else 'other',
            }

            if gemini_result:
                attachment_info["geminiFileUri"] = gemini_result["uri"]
                attachment_info["geminiFileName"] = gemini_result["name"]
                log.info(
                    "Uploaded temp attachment to Gemini",
                    filename=temp_att.filename,
                    gemini_uri=gemini_result["uri"],
                )
            else:
                attachment_info["geminiFileUri"] = None
                attachment_info["geminiFileName"] = None
                log.warning(
                    "Failed to upload temp attachment to Gemini",
                    filename=temp_att.filename,
                    gcs_uri=gcs_uri,
                )

            attachments.append(attachment_info)

    log.info("chat_stream_request",
             message_preview=last_message[:100],
             has_attachments=bool(attachments),
             attachment_count=len(attachments) if attachments else 0)

    async def generate():
        """Generate SSE events."""
        try:
            agent = _create_agent_with_tools()

            # Send initial thinking event
            thinking_msg = get_message("thinking", language)
            yield f"data: {json.dumps({'type': 'thinking', 'message': thinking_msg}, ensure_ascii=False)}\n\n"

            # Process message with ReAct Agent in streaming mode
            async for event in agent.process_message_stream(
                user_message=last_message,
                user_id=request.user_id,
                session_id=request.session_id,
                attachments=attachments,  # Already dict format, no need for model_dump()
            ):
                event_type = event.get("type")

                # Stream events to frontend
                if event_type == "thought":
                    # Agent's reasoning process - keep as thought type
                    # Frontend will display with different styling (collapsible)
                    yield f"data: {json.dumps({'type': 'thought', 'content': event.get('content', '')}, ensure_ascii=False)}\n\n"

                elif event_type == "action":
                    # Tool execution starting
                    tool_name = event.get("tool", "unknown")
                    status_msg = get_message("tool_executing", language).format(tool=tool_name)
                    yield f"data: {json.dumps({'type': 'action', 'tool': tool_name, 'message': status_msg}, ensure_ascii=False)}\n\n"

                elif event_type == "observation":
                    # Tool execution result
                    tool_name = event.get("tool", "unknown")
                    success = event.get("success", False)
                    result = event.get("result", "")

                    observation_data = {
                        'type': 'observation',
                        'tool': tool_name,
                        'success': success,
                        'result': result,
                    }

                    # Include generated media data if present
                    if event.get("images"):
                        observation_data["images"] = event["images"]
                    # Priority: GCS object name > base64 > direct URL
                    if event.get("video_object_name"):
                        # GCS object name - frontend will call signed URL API
                        observation_data["video_object_name"] = event["video_object_name"]
                        observation_data["video_bucket"] = event.get("video_bucket")
                    elif event.get("video_data_b64"):
                        # Fallback to base64 data
                        observation_data["video_data_b64"] = event["video_data_b64"]
                        observation_data["video_format"] = event.get("video_format", "mp4")
                    elif event.get("video_url"):
                        # Legacy fallback to direct URL
                        observation_data["video_url"] = event["video_url"]

                    yield f"data: {json.dumps(observation_data, ensure_ascii=False)}\n\n"

                elif event_type == "text":
                    # Final response text
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                elif event_type == "user_input_request":
                    # Human-in-the-loop request
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                elif event_type == "error":
                    # Error occurred
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    return

            # Send done event
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            log.error("chat_stream_error", error=str(e), exc_info=True)
            error_event = json.dumps({"type": "error", "error": str(e)}, ensure_ascii=False)
            yield f"data: {error_event}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )









