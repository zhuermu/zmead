"""HTTP streaming chat endpoint for Vercel AI SDK compatibility."""

import json
import logging
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    """Chat message model."""

    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")


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
    
    Requirements: 4.1.3, 4.1.4
    """
    logger.info(f"Chat request from user {current_user.id} with {len(request.messages)} messages")

    async def generate_stream():
        """Generate streaming response."""
        try:
            async with httpx.AsyncClient(timeout=settings.ai_orchestrator_timeout) as client:
                # Prepare request payload
                payload = {
                    "messages": [
                        {"role": msg.role, "content": msg.content}
                        for msg in request.messages
                    ],
                    "user_id": str(current_user.id),
                }

                # Stream response from AI Orchestrator
                async with client.stream(
                    "POST",
                    f"{settings.ai_orchestrator_url}/chat",
                    json=payload,
                    headers={"Content-Type": "application/json"},
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
