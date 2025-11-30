# AI Orchestrator

AI Orchestrator is the core intelligent assistant for the AAE (Automated Ad Engine) platform. It provides a unified conversational interface where users interact with the system through natural language.

## Overview

The AI Orchestrator:
- Understands user intent through Gemini 2.5 Pro
- Coordinates 5 functional modules (Creative, Reporting, Market Intel, Landing Page, Campaign)
- Manages conversation context and history
- Communicates with Web Platform via MCP protocol
- Supports streaming responses for real-time interaction

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   AI Orchestrator                       │
│                                                         │
│  ┌───────────────────────────────────────────────┐    │
│  │         FastAPI Application Layer             │    │
│  │  - HTTP Streaming Handler (/chat)             │    │
│  │  - Health Check Endpoints (/health, /ready)   │    │
│  └───────────────────────────────────────────────┘    │
│                        │                               │
│  ┌───────────────────────────────────────────────┐    │
│  │         LangGraph Agent Layer                 │    │
│  │  - State Machine (StateGraph)                 │    │
│  │  - Router Node (Intent Recognition)           │    │
│  │  - Functional Module Nodes (5 modules)        │    │
│  │  - Confirmation Node (Human-in-the-loop)      │    │
│  │  - Response Generator Node                    │    │
│  └───────────────────────────────────────────────┘    │
│                        │                               │
│  ┌───────────────────────────────────────────────┐    │
│  │         Integration Layer                     │    │
│  │  - MCP Client (Web Platform communication)    │    │
│  │  - LLM Client (Gemini 2.5 Pro/Flash)          │    │
│  │  - Redis Client (State Persistence)           │    │
│  └───────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## Project Structure

```
ai-orchestrator/
├── app/
│   ├── api/              # FastAPI endpoints
│   │   ├── chat.py       # Chat streaming endpoint
│   │   └── health.py     # Health check endpoints
│   ├── core/             # Core infrastructure
│   │   ├── config.py     # Pydantic settings
│   │   ├── logging.py    # Structured logging
│   │   ├── redis_client.py
│   │   ├── state.py      # LangGraph state definition
│   │   ├── graph.py      # LangGraph builder
│   │   ├── routing.py    # Conditional routing logic
│   │   ├── context.py    # Context resolution
│   │   ├── errors.py     # Custom exceptions
│   │   ├── retry.py      # Retry with backoff
│   │   └── auth.py       # Service authentication
│   ├── nodes/            # LangGraph nodes
│   │   ├── router.py     # Intent recognition
│   │   ├── creative_stub.py
│   │   ├── reporting_stub.py
│   │   ├── market_intel_stub.py
│   │   ├── landing_page_stub.py
│   │   ├── ad_engine_stub.py
│   │   ├── respond.py    # Response generation
│   │   ├── persist.py    # Conversation persistence
│   │   └── confirmation.py
│   ├── prompts/          # LLM prompt templates
│   │   ├── intent_recognition.py
│   │   └── response_generation.py
│   └── services/         # External service clients
│       ├── mcp_client.py # Web Platform MCP client
│       └── gemini_client.py
├── tests/                # Test suite
│   ├── test_intent_recognition_property.py
│   ├── test_execution_order_property.py
│   ├── test_context_resolution_property.py
│   └── test_retry_property.py
├── Dockerfile            # Docker configuration
├── .dockerignore         # Docker build exclusions
├── pyproject.toml        # Project configuration
├── requirements.txt      # Dependencies
├── .env.example          # Environment template
└── README.md             # This file
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- Redis 7.x running locally or via Docker
- Web Platform backend running on port 8000
- Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

### Local Development Setup

1. **Create virtual environment**
   ```bash
   cd ai-orchestrator
   python -m venv venv
   source venv/bin/activate  # macOS/Linux
   # or: venv\Scripts\activate  # Windows
   ```

2. **Install dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration (see Environment Variables section)
   ```

4. **Start Redis** (if not using Docker)
   ```bash
   redis-server
   ```

5. **Start the server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
   ```

6. **Verify it's running**
   ```bash
   curl http://localhost:8001/health
   ```

---

## API Endpoints

### POST /chat

HTTP streaming endpoint for chat interactions. Compatible with Vercel AI SDK.

**Headers:**
```
Authorization: Bearer <WEB_PLATFORM_SERVICE_TOKEN>
Content-Type: application/json
```

**Request Body:**
```json
{
  "messages": [
    {"role": "user", "content": "帮我生成10张广告图片"}
  ],
  "user_id": "user_123",
  "session_id": "session_456"
}
```

**Response:** Server-Sent Events (SSE) stream
```
data: {"type": "token", "content": "好的"}

data: {"type": "token", "content": "，"}

data: {"type": "tool_start", "tool": "check_credit"}

data: {"type": "tool_complete", "tool": "check_credit", "result": {"allowed": true}}

data: {"type": "token", "content": "正在生成素材..."}

data: {"type": "done"}

```

### GET /health

Health check endpoint for monitoring and load balancers.

**Response:**
```json
{
  "status": "healthy",
  "checks": {
    "redis": true,
    "mcp": true,
    "llm": true
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

**Status Codes:**
- `200 OK` - All checks passed
- `503 Service Unavailable` - One or more checks failed

### GET /ready

Kubernetes readiness probe endpoint.

**Response:**
```json
{
  "ready": true
}
```

---

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | `AIza...` |
| `WEB_PLATFORM_SERVICE_TOKEN` | Service-to-service auth token | `abc123...` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `WEB_PLATFORM_URL` | Web Platform backend URL | `http://localhost:8000` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/3` |
| `ENVIRONMENT` | Environment name | `development` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `GEMINI_MODEL_CHAT` | Model for intent recognition | `gemini-2.5-pro` |
| `GEMINI_MODEL_FAST` | Model for fast responses | `gemini-2.5-flash` |
| `MAX_CONCURRENT_REQUESTS` | Max concurrent requests | `100` |
| `REQUEST_TIMEOUT` | Request timeout (seconds) | `60` |
| `REDIS_MAX_CONNECTIONS` | Redis connection pool size | `10` |

### Generating Service Token

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Use the same token in both:
- `ai-orchestrator/.env` as `WEB_PLATFORM_SERVICE_TOKEN`
- `backend/.env` as `WEB_PLATFORM_SERVICE_TOKEN`

---

## Docker Deployment

### Build Image

```bash
cd ai-orchestrator
docker build -t ai-orchestrator:latest .
```

### Run Container

```bash
docker run -d \
  --name ai-orchestrator \
  -p 8001:8001 \
  -e GEMINI_API_KEY=your_api_key \
  -e WEB_PLATFORM_URL=http://host.docker.internal:8000 \
  -e WEB_PLATFORM_SERVICE_TOKEN=your_token \
  -e REDIS_URL=redis://host.docker.internal:6379/3 \
  ai-orchestrator:latest
```

### Docker Compose (Recommended)

From the repository root:

```bash
# Start all services
docker-compose up -d

# Start only AI Orchestrator and dependencies
docker-compose up -d redis backend ai-orchestrator

# View logs
docker-compose logs -f ai-orchestrator

# Stop services
docker-compose down
```

**Required environment variables in project root `.env`:**
```bash
GEMINI_API_KEY=your_gemini_api_key
WEB_PLATFORM_SERVICE_TOKEN=your_service_token
```

---

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_intent_recognition_property.py -v

# Run property-based tests with more examples
pytest tests/ -v --hypothesis-seed=0
```

### Code Quality

```bash
# Lint code
ruff check .

# Auto-fix lint issues
ruff check . --fix

# Format code
ruff format .

# Type checking
mypy app/
```

### Development Server with Auto-reload

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### Testing Chat Endpoint

```bash
curl -X POST http://localhost:8001/chat \
  -H "Authorization: Bearer your_service_token" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "帮我生成广告素材"}],
    "user_id": "test_user",
    "session_id": "test_session"
  }'
```

---

## Troubleshooting

### Common Issues

#### 1. Redis Connection Failed

**Symptoms:**
```
ConnectionError: Error connecting to redis://localhost:6379/3
```

**Solutions:**
- Ensure Redis is running: `redis-cli ping`
- Check REDIS_URL in .env matches your Redis instance
- For Docker: use `redis://redis:6379/3` (service name)

#### 2. MCP Connection Failed

**Symptoms:**
```
MCPConnectionError: Failed to connect to Web Platform
```

**Solutions:**
- Ensure Web Platform backend is running on the configured URL
- Verify WEB_PLATFORM_SERVICE_TOKEN matches backend configuration
- Check network connectivity between services

#### 3. Gemini API Errors

**Symptoms:**
```
AIModelError: Gemini API request failed
```

**Solutions:**
- Verify GEMINI_API_KEY is valid
- Check API quota at https://aistudio.google.com/
- Ensure you have access to the specified models

#### 4. Authentication Errors

**Symptoms:**
```
401 Unauthorized: Invalid service token
```

**Solutions:**
- Ensure WEB_PLATFORM_SERVICE_TOKEN is set correctly
- Token must match between AI Orchestrator and Web Platform
- Check Authorization header format: `Bearer <token>`

#### 5. Health Check Failing

**Symptoms:**
```
503 Service Unavailable
```

**Solutions:**
- Check individual service health: Redis, MCP, LLM
- Review logs: `docker-compose logs ai-orchestrator`
- Verify all environment variables are set

### Viewing Logs

**Local development:**
```bash
# Logs are printed to stdout with human-readable format
uvicorn app.main:app --reload --port 8001
```

**Docker:**
```bash
# View logs
docker-compose logs -f ai-orchestrator

# View last 100 lines
docker-compose logs --tail=100 ai-orchestrator
```

**Production logs are JSON formatted for log aggregation systems.**

---

## Architecture Details

### LangGraph State Machine

The AI Orchestrator uses LangGraph to manage conversation flow:

```
[START] → [router] → [module_node] → [should_confirm?]
                                          │
                    ┌─────────────────────┴─────────────────────┐
                    ▼                                           ▼
            [human_confirmation]                           [respond]
                    │                                           │
                    └───────────────────────────────────────────┘
                                          │
                                          ▼
                                      [persist]
                                          │
                                          ▼
                                        [END]
```

### Intent Recognition

The router node uses Gemini 2.5 Pro with structured output to identify:
- Primary intent (creative, reporting, market, landing_page, campaign)
- Extracted parameters
- Estimated credit cost
- Whether confirmation is required

### Credit Flow

1. Module estimates credit cost
2. Check credit via MCP `check_credit` tool
3. If sufficient, execute operation
4. Deduct credit via MCP `deduct_credit` tool
5. On failure, refund via MCP `refund_credit` tool

---

## License

MIT
