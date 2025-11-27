# WebSocket Chat Backend

This document describes the WebSocket chat backend implementation for real-time communication between the frontend and AI Orchestrator.

## Overview

The Web Platform provides two ways to communicate with the AI Orchestrator:

1. **WebSocket** (`/api/v1/ws/chat`) - Real-time bidirectional communication
2. **HTTP Streaming** (`/api/v1/chat`) - Server-sent events compatible with Vercel AI SDK

## WebSocket Endpoint

### Connection

Connect to the WebSocket endpoint with JWT authentication:

```javascript
const token = localStorage.getItem('access_token');
const ws = new WebSocket(`ws://localhost:8000/api/v1/ws/chat?token=${token}`);
```

### Message Format

#### Client → Server Messages

**User Message:**
```json
{
  "type": "user_message",
  "message_id": "msg_123",
  "content": "Help me create a campaign"
}
```

**Pong (heartbeat response):**
```json
{
  "type": "pong"
}
```

#### Server → Client Messages

**Connection Established:**
```json
{
  "type": "connection_established",
  "session_id": "session_456",
  "user_id": "1",
  "timestamp": "2024-11-27T10:00:00Z"
}
```

**Ping (heartbeat):**
```json
{
  "type": "ping",
  "timestamp": "2024-11-27T10:00:30Z"
}
```

**Message Received:**
```json
{
  "type": "message_received",
  "message_id": "msg_123",
  "timestamp": "2024-11-27T10:00:01Z"
}
```

**Agent Message Chunk (streaming):**
```json
{
  "type": "agent_message_chunk",
  "message_id": "msg_123",
  "content": "I'll help you create a campaign...",
  "timestamp": "2024-11-27T10:00:02Z"
}
```

**Agent Message Complete:**
```json
{
  "type": "agent_message_complete",
  "message_id": "msg_123",
  "full_content": "I'll help you create a campaign. First, let me...",
  "timestamp": "2024-11-27T10:00:05Z"
}
```

**Error:**
```json
{
  "type": "error",
  "error": {
    "code": "TIMEOUT",
    "message": "Response timeout. Please try again."
  },
  "timestamp": "2024-11-27T10:01:00Z"
}
```

## HTTP Streaming Endpoint

### Request

```bash
POST /api/v1/chat
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "messages": [
    {
      "role": "user",
      "content": "Help me create a campaign"
    }
  ]
}
```

### Response

Server-sent events stream compatible with Vercel AI SDK:

```
data: {"type": "chunk", "content": "I'll help you"}

data: {"type": "chunk", "content": " create a campaign"}

data: {"type": "done"}
```

## Features

### 1. Authentication

Both endpoints require JWT authentication:
- WebSocket: Token passed as query parameter (`?token=<jwt>`)
- HTTP: Token passed in Authorization header (`Bearer <jwt>`)

### 2. Heartbeat Mechanism

The WebSocket connection implements a heartbeat mechanism to detect stale connections:

- Server sends `ping` every 30 seconds
- Client must respond with `pong`
- If no `pong` received within 60 seconds, connection is closed

### 3. Connection Management

The `ConnectionManager` class handles:
- Active connection tracking
- User session mapping
- Message broadcasting
- Connection metrics logging

### 4. Error Handling

Both endpoints handle various error scenarios:
- Authentication failures
- AI Orchestrator connection errors
- Timeout errors (60 seconds)
- Invalid message format

### 5. Streaming Response

Messages from the AI Orchestrator are streamed back to the client in real-time, providing a better user experience.

## Configuration

Set these environment variables in `.env`:

```bash
# AI Orchestrator
AI_ORCHESTRATOR_URL=http://localhost:8001
AI_ORCHESTRATOR_TIMEOUT=60

# JWT
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Testing

Run the WebSocket tests:

```bash
pytest tests/test_websocket.py -v
```

## Architecture

```
┌─────────────┐         WebSocket/HTTP         ┌──────────────┐
│   Frontend  │ ────────────────────────────> │ Web Platform │
│             │                                 │   Backend    │
└─────────────┘                                 └──────────────┘
                                                       │
                                                       │ HTTP Stream
                                                       ▼
                                                ┌──────────────┐
                                                │      AI      │
                                                │ Orchestrator │
                                                └──────────────┘
```

## Requirements Validation

This implementation satisfies the following requirements:

- **12.1.1**: WebSocket connection handler with authentication
- **12.1.2**: Heartbeat mechanism (30s ping, 60s timeout)
- **12.1.3**: Auto-reconnect handled by frontend
- **12.1.4**: Message queue handled by frontend
- **4.1.3**: HTTP streaming endpoint for Vercel AI SDK
- **4.1.4**: Message forwarding to AI Orchestrator
- **4.2.2**: Streaming response display

## Next Steps

1. Implement AI Orchestrator integration
2. Add message persistence
3. Add conversation history
4. Implement tool invocation display
5. Add rate limiting
