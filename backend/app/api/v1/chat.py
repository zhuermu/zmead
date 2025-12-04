"""HTTP streaming chat endpoint for Vercel AI SDK compatibility."""

import asyncio
import json
import logging
import uuid
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser
from app.core.config import settings
from app.services.file_processor import process_temp_attachments

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


class TempFileAttachment(BaseModel):
    """Temporary file attachment reference."""

    fileKey: str = Field(..., description="Temporary file key in GCS")
    fileId: str = Field(..., description="Unique file ID")
    filename: str = Field(..., description="Original filename")
    contentType: str = Field(..., description="File content type")
    size: int = Field(..., description="File size in bytes")


class ChatMessage(BaseModel):
    """Chat message model."""

    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")
    tempAttachments: list[TempFileAttachment] | None = Field(
        None, description="Temporary file attachments (not yet confirmed)"
    )


class ChatRequest(BaseModel):
    """Chat request model."""

    messages: list[ChatMessage] = Field(..., description="Conversation messages")


@router.post("")
async def chat_stream(
    request: ChatRequest,
    current_user: CurrentUser,
) -> StreamingResponse:
    """
    HTTP streaming chat endpoint compatible with Vercel AI SDK.

    This endpoint forwards chat requests to the AI Orchestrator and streams
    the response back to the client in a format compatible with Vercel AI SDK.

    Automatically processes temporary file attachments:
    - Moves files from temp to permanent storage
    - Uploads files to Gemini Files API
    - Attaches processed files to messages for AI Agent

    Requirements: 4.1.3, 4.1.4
    """
    logger.info(f"Chat request from user {current_user.id} with {len(request.messages)} messages")

    # DEBUG: Log the raw request to see what we're receiving
    for i, msg in enumerate(request.messages):
        logger.info(f"Message {i}: role={msg.role}, content_length={len(msg.content)}, has_tempAttachments={msg.tempAttachments is not None}")
        if msg.tempAttachments:
            logger.info(f"  tempAttachments count: {len(msg.tempAttachments)}")
            for j, att in enumerate(msg.tempAttachments):
                logger.info(f"    Attachment {j}: fileId={att.fileId}, filename={att.filename}")

    # Process temporary attachments from ALL messages before starting stream
    # This ensures files are ready for AI Agent to use
    processed_messages = []

    for msg in request.messages:
        processed_msg = {"role": msg.role, "content": msg.content}

        # Process temp attachments if present
        if msg.tempAttachments:
            logger.info(
                f"Processing {len(msg.tempAttachments)} temp attachments for message"
            )

            # Convert to dict format for processing
            temp_files = [att.dict() for att in msg.tempAttachments]

            # Process attachments (async)
            processed_attachments = await process_temp_attachments(
                temp_files, str(current_user.id)
            )

            if processed_attachments:
                # Add processed attachments to message
                processed_msg["attachments"] = [
                    att.to_dict() for att in processed_attachments
                ]
                logger.info(
                    f"Successfully processed {len(processed_attachments)} attachments"
                )
            else:
                logger.warning("No attachments were successfully processed")

        processed_messages.append(processed_msg)

    async def generate_stream():
        """Generate streaming response."""
        try:
            async with httpx.AsyncClient(timeout=settings.ai_orchestrator_timeout) as client:
                # Prepare request payload
                # Generate session_id from user_id for conversation continuity
                session_id = f"session-{current_user.id}-{uuid.uuid4().hex[:8]}"

                payload = {
                    "messages": processed_messages,
                    "user_id": str(current_user.id),
                    "session_id": session_id,
                }

                # Stream response from AI Orchestrator
                async with client.stream(
                    "POST",
                    f"{settings.ai_orchestrator_url}/api/v1/chat",
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {settings.ai_orchestrator_service_token}",
                    },
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(
                            f"AI Orchestrator error: {response.status_code} - {error_text}"
                        )
                        # Send error in Vercel AI SDK format
                        error_data = {
                            "error": {
                                "code": "AI_ORCHESTRATOR_ERROR",
                                "message": "Failed to get response from AI",
                            }
                        }
                        yield f"data: {json.dumps(error_data)}\n\n"
                        return

                    # Stream chunks back to client
                    async for chunk in response.aiter_text():
                        if chunk:
                            # Forward chunk as-is (assuming AI Orchestrator returns
                            # Vercel AI SDK compatible format)
                            yield chunk

        except httpx.TimeoutException:
            logger.error(f"AI Orchestrator timeout for user {current_user.id}")
            error_data = {
                "error": {
                    "code": "TIMEOUT",
                    "message": "Response timeout. Please try again.",
                }
            }
            yield f"data: {json.dumps(error_data)}\n\n"

        except httpx.ConnectError:
            logger.error(f"Cannot connect to AI Orchestrator: {settings.ai_orchestrator_url}")
            error_data = {
                "error": {
                    "code": "CONNECTION_FAILED",
                    "message": "Cannot connect to AI service. Please try again later.",
                }
            }
            yield f"data: {json.dumps(error_data)}\n\n"

        except Exception as e:
            logger.error(f"Error in chat stream: {e}", exc_info=True)
            error_data = {
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An error occurred while processing your message",
                }
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
