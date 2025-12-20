# AI Orchestrator

AI Orchestrator is the core intelligent assistant for the AAE (Automated Ad Engine) platform. It provides a unified conversational interface where users interact with the system through natural language using the **Strands Agents** framework.

## Overview

The AI Orchestrator:
- Uses **Strands Agents** framework for autonomous task planning and execution
- Supports **multi-provider AI models** (Gemini, AWS Bedrock Claude/Nova/Qwen3)
- Provides **unified web search** with automatic fallback (Nova → Google Grounding)
- Implements **intelligent tool orchestration** with real-time streaming
- Manages conversation context and memory via Redis
- Communicates with Backend via MCP protocol
- Supports real-time streaming responses via SSE (Server-Sent Events) without buffering

## Architecture

The AI Orchestrator uses **Strands Agents** with intelligent tool orchestration:

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI Orchestrator (ReAct v2)                   │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   FastAPI Application                      │  │
│  │  - POST /api/v1/chat (streaming SSE)                      │  │
│  │  - GET /health, /ready                                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────▼───────────────────────────────┐  │
│  │                   ReAct Agent                              │  │
│  │                                                            │  │
│  │  Step 1: Planner (制定计划)                                │  │
│  │  ├─ 理解用户意图                                            │  │
│  │  ├─ 分解任务步骤                                            │  │
│  │  └─ 选择需要的 Tools                                        │  │
│  │                                                            │  │
│  │  Step 2: Evaluator (判断是否需要人工)                       │  │
│  │  ├─ 检查操作风险（花费、删除等）                             │  │
│  │  ├─ 检查参数模糊度                                          │  │
│  │  └─ 决定是否需要 Human-in-the-Loop                         │  │
│  │                                                            │  │
│  │  Step 3: Human-in-the-Loop (可选)                          │  │
│  │  ├─ 生成确认请求                                            │  │
│  │  ├─ 生成选项（预设 + 其他 + 取消）                          │  │
│  │  └─ 等待用户输入                                            │  │
│  │                                                            │  │
│  │  Step 4: Act (执行 Tools)                                  │  │
│  │  ├─ 调用选定的 Tools                                        │  │
│  │  └─ 处理执行结果                                            │  │
│  │                                                            │  │
│  │  Step 5: Memory (记录结果)                                 │  │
│  │  ├─ 保存执行历史到 Redis                                    │  │
│  │  └─ 更新对话上下文                                          │  │
│  │                                                            │  │
│  │  Step 6: Perceive (评估是否完成)                           │  │
│  │  ├─ 检查任务是否完成                                        │  │
│  │  └─ 决定是否继续循环                                        │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────▼───────────────────────────────┐  │
│  │                   Built-in Tools                           │  │
│  │                                                            │  │
│  │  1. Strands Built-in Tools                                │  │
│  │     - web_search (unified, auto-fallback Nova → Google)   │  │
│  │     - calculator, datetime                                │  │
│  │                                                            │  │
│  │  2. Creative Tools (AI-powered)                           │  │
│  │     - generate_image_tool (Bedrock/SageMaker)             │  │
│  │     - generate_video_tool (AWS SageMaker)                 │  │
│  │     - analyze_creative_tool (Gemini Vision)               │  │
│  │                                                            │  │
│  │  3. MCP Server Tools (Backend API)                        │  │
│  │     - save_creative, fetch_ad_data, create_campaign       │  │
│  │     - save_landing_page, fetch_competitor_data, etc.      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────▼───────────────────────────────┐  │
│  │              业务逻辑实现层 (modules/)                      │  │
│  │                                                            │  │
│  │  - ad_creative/ (被 Creative Tools 调用)                   │  │
│  │  - ad_performance/ (被 Performance Tools 调用)             │  │
│  │  - campaign_automation/ (被 Campaign Tools 调用)           │  │
│  │  - landing_page/ (被 Landing Page Tools 调用)              │  │
│  │  - market_insights/ (被 Market Tools 调用)                 │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────▼───────────────────────────────┐  │
│  │                   Integration Layer                        │  │
│  │  - MCP Client (Backend communication)                     │  │
│  │  - Model Providers (Bedrock, Gemini, SageMaker)           │  │
│  │  - S3 Client (presigned URLs for media)                   │  │
│  │  - Redis Client (conversation memory)                     │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**Key Features:**
- **Strands Agents Framework**: Autonomous tool orchestration with streaming support
- **Multi-Provider Support**: Choose between Gemini and AWS Bedrock (Claude, Nova, Qwen3)
- **Unified Web Search**: Automatic fallback from Amazon Nova Search to Google Grounding
- **Intelligent Tool Orchestration**: Built-in tools for search, calculations, creative generation
- **Real-time Streaming**: SSE streaming without buffering for instant responses
- **Memory Management**: Uses Redis to maintain conversation context and agent state
- **S3 Integration**: Presigned URLs for secure media access (images, videos)
- **User-Friendly Display**: Frontend tool name mapping (e.g., "互联网搜索" instead of technical names)
- **Extensible**: Easy to add new tools and model providers

## Project Structure

```
ai-orchestrator/
├── app/
│   ├── api/              # FastAPI endpoints
│   │   ├── chat.py       # Chat streaming endpoint (SSE)
│   │   ├── health.py     # Health check endpoints
│   │   └── campaign_automation.py # Campaign automation API
│   ├── core/             # Core infrastructure
│   │   ├── config.py     # Pydantic settings
│   │   ├── logging.py    # Structured logging
│   │   ├── redis_client.py # Redis client
│   │   ├── react_agent.py # ReAct Agent main loop
│   │   ├── planner.py    # Task planning component
│   │   ├── evaluator.py  # Human-in-the-Loop evaluator
│   │   ├── human_in_loop.py # Human interaction handler
│   │   ├── memory.py     # Conversation memory
│   │   ├── context.py    # Context resolution
│   │   ├── errors.py     # Custom exceptions
│   │   ├── retry.py      # Retry with backoff
│   │   └── auth.py       # Service authentication
│   ├── tools/            # 3 类 Tools
│   │   ├── base.py       # Tool base class
│   │   ├── registry.py   # Tool registry
│   │   ├── langchain_tools.py # LangChain 内置 Tools
│   │   ├── creative_tools.py # Creative Agent Custom Tools
│   │   ├── performance_tools.py # Performance Agent Custom Tools
│   │   ├── campaign_tools.py # Campaign Agent Custom Tools
│   │   ├── landing_page_tools.py # Landing Page Agent Custom Tools
│   │   ├── market_tools.py # Market Agent Custom Tools
│   │   └── mcp_tools.py  # MCP Server Tools wrapper
│   ├── modules/          # 业务逻辑实现层
│   │   ├── ad_creative/  # Creative generation (被 Creative Tools 调用)
│   │   ├── ad_performance/ # Performance analytics (被 Performance Tools 调用)
│   │   ├── campaign_automation/ # Campaign automation (被 Campaign Tools 调用)
│   │   ├── landing_page/ # Landing page generation (被 Landing Page Tools 调用)
│   │   └── market_insights/ # Market intelligence (被 Market Tools 调用)
│   ├── prompts/          # LLM prompt templates
│   │   ├── intent_recognition.py
│   │   ├── response_generation.py
│   │   └── performance_analysis.py
│   └── services/         # External service clients
│       ├── mcp_client.py # Backend MCP client
│       └── gemini_client.py # Gemini API client
├── tests/                # Test suite
│   ├── ad_creative/      # Creative module tests
│   ├── ad_performance/   # Performance module tests
│   ├── campaign_automation/ # Campaign module tests
│   ├── landing_page/     # Landing page module tests
│   ├── market_insights/  # Market insights module tests
│   ├── test_react_agent_core.py # ReAct Agent core tests
│   ├── test_human_in_loop.py # Human-in-the-Loop tests
│   └── test_retry_property.py # Retry logic tests
├── docs/                 # Documentation
│   └── ARCHITECTURE.md   # Architecture documentation
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
- **For Gemini provider:**
  - Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
- **For AWS Bedrock provider:**
  - AWS Account with Bedrock access
  - AWS credentials configured
  - Model access approved (Claude, Qwen3, Nova)
- **For SageMaker models:**
  - SageMaker endpoints deployed (Qwen-Image, Wan2.2)

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
   # For AWS setup
   cp .env.aws.example .env
   
   # Or for Gemini-only setup
   cp .env.example .env
   
   # Edit .env with your configuration (see Environment Variables section)
   ```
   
   **Important:** See [AWS Setup Guide](../AWS_SETUP_GUIDE.md) for complete AWS configuration instructions.

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

### POST /api/v1/chat

HTTP streaming endpoint for chat interactions using Server-Sent Events (SSE).

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

data: {"type": "agent_start", "agent": "creative_agent", "action": "generate"}

data: {"type": "agent_complete", "agent": "creative_agent", "success": true}

data: {"type": "token", "content": "已生成10张广告图片"}

data: {"type": "done"}
```

### POST /api/v1/chat/sync

Synchronous (non-streaming) chat endpoint for simple request-response interactions.

**Headers:**
```
Authorization: Bearer <WEB_PLATFORM_SERVICE_TOKEN>
Content-Type: application/json
```

**Request Body:**
```json
{
  "messages": [
    {"role": "user", "content": "查看我的广告表现"}
  ],
  "user_id": "user_123",
  "session_id": "session_456"
}
```

**Response:**
```json
{
  "response": "您的广告表现如下...",
  "success": true,
  "session_id": "session_456",
  "tool_results": [
    {
      "agent": "performance_agent",
      "action": "analyze",
      "data": {...}
    }
  ]
}
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

## ReAct Agent Workflow

The ReAct Agent follows a **Reasoning + Acting** loop:

```
用户消息
    │
    ▼
┌─────────────────────────────────────┐
│ Step 1: Planner                     │
│  - 使用 Gemini 理解用户意图          │
│  - 分解任务为具体步骤                │
│  - 选择需要的 Tools                  │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ Step 2: Evaluator                   │
│  - 检查操作风险                      │
│  - 检查参数模糊度                    │
│  - 决定是否需要 Human-in-the-Loop   │
└─────────────────────────────────────┘
    │
    ├─ 需要人工 ──────────┐
    │                      │
    ▼                      ▼
┌──────────────┐  ┌──────────────┐
│ Human-in-    │  │ 跳过，继续   │
│ the-Loop     │  │ 执行         │
└──────────────┘  └──────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ Step 4: Act                         │
│  - 调用选定的 Tools                  │
│  - 处理执行结果                      │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ Step 5: Memory                      │
│  - 保存执行历史到 Redis              │
│  - 更新对话上下文                    │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ Step 6: Perceive                    │
│  - 检查任务是否完成                  │
│  - 决定是否继续循环                  │
└─────────────────────────────────────┘
    │
    ├─ 未完成 ──► 返回 Step 1
    │
    ▼
  返回用户
```

### Human-in-the-Loop Mechanism

**Triggers:**
1. **Spending operations**: Creating campaigns, increasing budgets
2. **Important operations**: Deleting campaigns, pausing ads
3. **Ambiguous parameters**: User didn't specify style, target audience, etc.

**Interaction Types:**
1. **Confirmation**: Show operation details, user confirms or cancels
2. **Options**: Provide preset options + "Other" + "Cancel"
3. **Input**: User provides free-form input

**Example:**
```python
# User: "帮我生成素材"
# Agent (Evaluator): Style parameter is ambiguous

return UserInputRequest(
    question="请选择素材风格：",
    options=[
        "1️⃣ 现代简约",
        "2️⃣ 活力多彩",
        "3️⃣ 高端奢华",
        "➕ 其他",
        "❌ 取消"
    ]
)
```

## Architecture Details

### 3 Types of Tools

**1. LangChain Built-in Tools**
- General-purpose tools from LangChain ecosystem
- Examples: `google_search`, `calculator`
- Used for: Web search, calculations, date/time operations

**2. Agent Custom Tools (可调用大模型)**
- Custom tools that can call LLMs (Gemini)
- Encapsulate AI capabilities
- Examples:
  - `generate_image_tool`: Generate images using Gemini Imagen
  - `analyze_performance_tool`: Analyze ad performance using Gemini
  - `optimize_budget_tool`: Generate budget optimization recommendations using Gemini

**3. MCP Server Tools (Backend API)**
- Data interaction tools provided by Backend via MCP protocol
- No AI logic, only data CRUD operations
- Examples:
  - `save_creative`: Save creative to database
  - `fetch_ad_data`: Fetch ad data from database
  - `create_campaign`: Create campaign via Backend API

### Tool Registry

Tools are registered at startup:

```python
from app.tools.registry import get_tool_registry

registry = get_tool_registry()

# Register LangChain tools
registry.register_langchain_tools()

# Register Agent Custom Tools
registry.register_agent_tools()

# Register MCP Server Tools
await registry.register_mcp_tools()
```

### modules/ as Implementation Layer

The `modules/` directory contains business logic implementations that are called by Agent Custom Tools:

```python
# Agent Custom Tool
@tool
async def generate_image_tool(product_info: dict, style: str) -> str:
    """Generate ad image using Gemini Imagen."""
    service = get_ad_creative_service()
    image_url = await service.generate_image(product_info, style)
    return image_url

# modules/ad_creative/service.py
class AdCreativeService:
    async def generate_image(self, product_info: dict, style: str) -> str:
        # Business logic implementation
        prompt = self._build_prompt(product_info, style)
        image_url = await self.gemini_client.generate_image(prompt)
        return image_url
```

**Key Points:**
- `modules/` are NOT independent agents
- They are called by Agent Custom Tools
- They contain reusable business logic
- They can be called by both Agent Custom Tools and Celery tasks

### Memory Management

The ReAct Agent uses Redis to store:
- **Conversation history**: User messages and agent responses
- **Agent state**: Current plan, executed steps, tool results
- **Session context**: User preferences, active campaigns, etc.

```python
# Save to memory
await memory.save(
    session_id=session_id,
    state={
        "current_plan": plan,
        "steps_completed": steps,
        "tool_results": results
    }
)

# Load from memory
state = await memory.load(session_id=session_id)
```

---

## Development Guide

### Adding a New Tool

#### 1. Agent Custom Tool (可调用大模型)

```python
# app/tools/creative_tools.py

from langchain.tools import tool
from app.modules.ad_creative.service import get_ad_creative_service

@tool
async def generate_video_tool(
    product_info: dict,
    style: str,
    duration: int = 15
) -> str:
    """Generate ad video using Gemini Veo.
    
    Args:
        product_info: Product information
        style: Video style (modern, vibrant, luxury)
        duration: Video duration in seconds
    
    Returns:
        Video URL
    """
    service = get_ad_creative_service()
    video_url = await service.generate_video(product_info, style, duration)
    return video_url
```

#### 2. Register the Tool

```python
# app/tools/registry.py

def register_agent_tools(self):
    """Register all Agent Custom Tools."""
    from app.tools.creative_tools import (
        generate_image_tool,
        generate_video_tool,  # Add new tool
        analyze_creative_tool
    )
    
    self.tools.extend([
        generate_image_tool,
        generate_video_tool,  # Register new tool
        analyze_creative_tool
    ])
```

#### 3. Implement Business Logic

```python
# app/modules/ad_creative/service.py

class AdCreativeService:
    async def generate_video(
        self,
        product_info: dict,
        style: str,
        duration: int
    ) -> str:
        """Generate video using Gemini Veo."""
        prompt = self._build_video_prompt(product_info, style, duration)
        video_url = await self.gemini_client.generate_video(prompt)
        
        # Save to backend via MCP
        await self.mcp_client.call_tool(
            "save_creative",
            {
                "type": "video",
                "url": video_url,
                "metadata": {...}
            }
        )
        
        return video_url
```

### Adding a New Module

1. Create module directory: `app/modules/new_module/`
2. Implement service: `app/modules/new_module/service.py`
3. Create Agent Custom Tools: `app/tools/new_module_tools.py`
4. Register tools in `app/tools/registry.py`

### Testing

```bash
# Run all tests
pytest

# Run specific module tests
pytest tests/ad_creative/ -v

# Run ReAct Agent tests
pytest tests/test_react_agent_core.py -v

# Run Human-in-the-Loop tests
pytest tests/test_human_in_loop.py -v

# Run with coverage
pytest --cov=app tests/
```

### Debugging

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with auto-reload
uvicorn app.main:app --reload --port 8001

# View Redis data
redis-cli
> SELECT 3
> KEYS *
> GET session:123
```

---

## Future Optimizations

### Skills Dynamic Loading

When the number of tools exceeds 50, implement Skills dynamic loading:

1. **Group tools into Skills** (Creative, Performance, Campaign, Landing Page, Market)
2. **Identify required Skills** based on user message
3. **Load only relevant tools** (15-20 instead of 50)
4. **Reduce LLM context** by 60%+
5. **Improve response speed** by 30%+

See `.kiro/specs/react-agent-v2/design.md` for detailed design.

---

## License

MIT


---

## AWS Integration

### Model Providers

The AI Orchestrator supports multiple model providers:

1. **Google Gemini** (default for new installations)
   - Gemini 2.5 Flash
   - Gemini 2.5 Pro
   - Multimodal support (images, videos, documents)

2. **AWS Bedrock** (recommended for production)
   - Claude 4.5 Sonnet
   - Qwen3 235B
   - Amazon Nova 2 Lite

3. **AWS SageMaker** (for custom models)
   - Qwen-Image (image generation)
   - Wan2.2 (video generation)

### AWS Setup

See [AWS Setup Guide](../AWS_SETUP_GUIDE.md) for complete instructions:

1. Configure AWS credentials
2. Request Bedrock model access
3. Deploy SageMaker endpoints
4. Update environment configuration
5. Validate setup

### Configuration Validation

```bash
python -m app.core.aws_config_validator
```

Expected output:
```
✓ AWS credentials configured
✓ Bedrock models available
✓ SageMaker endpoints ready
✓ Configuration valid
```

## Key Features Implemented

### Unified Web Search

The `web_search` tool provides automatic fallback for reliable search results:

**Primary**: Amazon Nova Search (AWS Bedrock Converse API)
- Fast, AWS-native integration
- Uses `nova_grounding` system tool
- Model: `us.amazon.nova-lite-v1:0`
- Response time: ~5-6 seconds

**Fallback**: Google Search (Gemini Grounding)
- Structured citations support
- Response time: ~3-4 seconds

**User Experience**:
- Single tool name: `web_search`
- Frontend displays: "互联网搜索"
- Automatic provider selection (transparent to user)

See [WEB_SEARCH_UNIFIED.md](./WEB_SEARCH_UNIFIED.md) and [NOVA_SEARCH_IMPLEMENTATION.md](./NOVA_SEARCH_IMPLEMENTATION.md) for technical details.

### S3 Presigned URLs

Generated images and videos return presigned URLs for secure browser access:

```python
# Generate presigned URL (1-hour expiration)
presigned_url = s3_client.generate_presigned_url(
    object_name=upload_result["object_name"],
    expiration=3600
)

# Response includes both formats
{
    "s3_url": "s3://bucket/path/to/image.png",  # For internal use
    "url": "https://bucket.s3.amazonaws.com/...?X-Amz..."  # For browser display
}
```

### Real-time Streaming

Streaming implementation forwards model delta directly without buffering:

```python
# Direct forwarding from model
if "delta" in chunk and isinstance(chunk["delta"], dict):
    text = chunk["delta"].get("text", "")
    if text:
        yield {"type": "text", "content": text}  # No buffering
```

**Benefits**:
- True real-time streaming experience
- Lower latency (no accumulation delay)
- Preserves model's original chunking

### Frontend Tool Name Mapping

User-friendly Chinese names for tools displayed in UI:

```typescript
const toolNameMap = {
  'web_search': '互联网搜索',
  'google_search': '互联网搜索',
  'nova_search': '互联网搜索',
  'calculator': '计算器',
  'datetime': '日期时间',
  'generate_image_tool': '图片生成',
  'generate_video_tool': '视频生成'
}
```

See `frontend/src/components/chat/AgentProcessingCard.tsx` for implementation.

---

## Attachment Handling & Media Generation

The AI Orchestrator supports generating and displaying media in the chat interface:

- **Image Generation**: Bedrock Stable Diffusion / SageMaker Qwen-Image
- **Video Generation**: AWS SageMaker Wan2.2 / Bedrock Nova Reel
- **Storage**: AWS S3 with presigned URLs (1-hour expiration)
- **Display**: Real-time streaming with unified attachment format

### Unified Attachment Format

All tools return attachments in the same structure:

```python
{
    "success": True,
    "message": "Successfully generated 1 images",
    "attachments": [
        {
            "id": "image_0_generated_image_modern_1",
            "filename": "generated_image_modern_1.png",
            "contentType": "image/png",
            "size": 1152573,
            "s3Url": "chat-images/2/session-123/image.png",
            "type": "image"  # or "video", "document"
        }
    ]
}
```

### Complete Flow

```
Tool Execution → Upload to S3 → Yield observation + attachments
    → SSE forwards to frontend → Fetch presigned URLs → Display in chat
```

**See [Attachment Handling Guide](./ATTACHMENT_HANDLING_GUIDE.md) for complete documentation.**

## Additional Documentation

- **[Attachment Handling Guide](./ATTACHMENT_HANDLING_GUIDE.md)** - Complete guide for media generation and display
- [AWS Setup Guide](../AWS_SETUP_GUIDE.md) - Complete AWS setup instructions
- [AWS Troubleshooting Guide](../AWS_TROUBLESHOOTING_GUIDE.md) - Common issues and solutions
- [Model Provider Capabilities](../MODEL_PROVIDER_CAPABILITIES.md) - Model comparison and selection guide
- [API Model Selection](../API_MODEL_SELECTION.md) - Model selection API documentation
- [SageMaker Deployment Guide](./SAGEMAKER_DEPLOYMENT_GUIDE.md) - Deploy custom models
- [Strands Agents Migration](./STRANDS_AGENTS_MIGRATION.md) - Framework migration details
- [Multi-Provider Implementation](./MULTI_PROVIDER_IMPLEMENTATION.md) - Technical implementation details
- [Web Search Unified](./WEB_SEARCH_UNIFIED.md) - Unified web search implementation
- [Nova Search Implementation](./NOVA_SEARCH_IMPLEMENTATION.md) - Amazon Nova Search details

---

**For AWS-related issues, see [AWS Troubleshooting Guide](../AWS_TROUBLESHOOTING_GUIDE.md)**
