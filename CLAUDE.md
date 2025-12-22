# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AAE (Automated Ad Engine) is an advertising SaaS platform with an embedded AI agent assistant. Users interact through a unified conversational interface to manage ad campaigns across Meta, TikTok, and Google Ads.

**Core Architecture**: 3 services communicating via HTTP/MCP:
- **Frontend** (Next.js, port 3000) - User interface with Vercel AI SDK chat
- **Backend** (FastAPI, port 8000) - REST API, MCP Server, data storage (MySQL + Redis + AWS S3)
- **AI Orchestrator** (FastAPI + Strands Agent, port 8001) - Intent recognition, tool orchestration, multi-model support

## Development Commands

### Quick Start (Local Development)
```bash
# 1. Start infrastructure only (recommended for local dev)
docker-compose up -d mysql redis

# 2. Start backend (in separate terminal)
cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000

# 3. Start AI orchestrator (in separate terminal)
cd ai-orchestrator && source venv/bin/activate && uvicorn app.main:app --reload --port 8001

# 4. Start frontend (in separate terminal)
cd frontend && npm run dev
```

### Infrastructure (Docker)
```bash
# Start all services (MySQL, Redis, backend, ai-orchestrator, frontend)
docker-compose up -d

# Start only MySQL and Redis for local development
docker-compose up -d mysql redis

# Stop services
docker-compose down

# View logs
docker-compose logs -f backend              # Follow backend logs
docker-compose logs -f ai-orchestrator      # Follow AI orchestrator logs
docker-compose logs --tail=100 backend      # Show last 100 lines

# Check service health
docker-compose ps                           # Show all services status
curl http://localhost:8000/health           # Backend health check
curl http://localhost:8001/health           # AI orchestrator health check
```

### Backend (FastAPI) - Port 8000
```bash
cd backend

# Setup virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies (including dev tools)
pip install -e ".[dev]"

# Database migrations
alembic upgrade head                           # Apply all migrations
alembic downgrade -1                           # Rollback one migration
alembic revision --autogenerate -m "message"   # Create new migration
alembic current                                # Show current migration

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest
pytest tests/test_file.py                      # Run single test file
pytest tests/test_file.py::test_function       # Run specific test
pytest --cov=app --cov-report=html             # Generate HTML coverage report

# Linting and type checking
ruff check app/                                # Check for issues
ruff format app/                               # Auto-format code
mypy app/

# Celery worker (background tasks)
celery -A app.core.celery worker --loglevel=info

# Celery beat (scheduler)
celery -A app.core.celery beat --loglevel=info
```

### AI Orchestrator (FastAPI + Strands Agent) - Port 8001
```bash
cd ai-orchestrator

# Setup virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies (including dev tools)
pip install -e ".[dev]"

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# Run tests
pytest
pytest tests/test_file.py                      # Run single test file
pytest --cov=app --cov-report=html             # Generate HTML coverage report

# Linting and type checking
ruff check .                                   # Check for issues
ruff format .                                  # Auto-format code
mypy app/
```

### Frontend (Next.js) - Port 3000
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Run production server
npm start

# Testing
npm run test        # Run tests in watch mode
npm run test:ci     # Run tests once (for CI)

# Lint
npm run lint
```

## Project Structure

```
zmead/
├── backend/                 # Web Platform Backend (FastAPI)
│   ├── app/
│   │   ├── api/             # API endpoints (routers)
│   │   ├── core/            # Config, security, celery setup
│   │   ├── mcp/             # MCP Server implementation
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic layer
│   │   ├── tasks/           # Celery async tasks
│   │   └── main.py          # FastAPI application entry
│   ├── alembic/             # Database migrations
│   └── tests/
├── ai-orchestrator/         # AI Agent Service (Strands Agents)
│   ├── app/
│   │   ├── api/             # Chat streaming endpoint
│   │   ├── core/            # Config, Strands Agent, memory
│   │   ├── tools/           # Unified web_search, creative tools, etc.
│   │   ├── modules/         # Business logic implementations
│   │   ├── prompts/         # LLM prompt templates
│   │   └── services/        # MCP client, model providers (Bedrock, Gemini)
│   └── tests/
├── frontend/                # Web UI (Next.js 14)
│   └── src/
│       ├── app/             # Next.js App Router pages
│       │   ├── admin/       # Admin panel
│       │   ├── billing/     # Subscription & credits
│       │   ├── campaigns/   # Ad campaign management
│       │   └── dashboard/   # Main dashboard
│       ├── components/      # React components
│       ├── hooks/           # Custom React hooks
│       ├── lib/             # Utilities and API client
│       └── types/           # TypeScript types
└── .kiro/specs/             # Requirements and architecture docs
```

## System Architecture

```
User Portal (用户入口)
├── Frontend: Next.js 14 + Vercel AI SDK
├── Backend: FastAPI + MCP Server
└── Data: MySQL 8.4 + Redis 7.x + AWS S3
         │
         │ HTTP Streaming (对话) + MCP Protocol (数据)
         ▼
Unified AI Agent (Strands Agents Framework)
├── Multi-Model Support (Gemini 2.5 / AWS Bedrock Claude / Nova / Qwen3)
├── Intelligent Tool Orchestration
└── Built-in Tools:
    ├── Unified Web Search (Nova → Google automatic fallback)
    ├── Calculator & DateTime
    ├── Creative Tools (Image/Video generation via Bedrock/SageMaker)
    ├── Performance Analysis Tools
    └── Campaign Management Tools
```

## Key Technical Decisions

- **AI Agent Framework**: Strands Agents with multi-provider support (Gemini / AWS Bedrock)
- **Frontend-to-Agent Communication**: HTTP POST + SSE (Server-Sent Events) for real-time streaming (no buffering)
- **Agent-to-Backend Communication**: MCP Protocol (Model Context Protocol)
- **State Management**: Zustand (frontend), React Query for server state
- **Billing**: Credit-based system (¥199/30K credits, ¥1999/400K credits, overage at ¥0.01/credit)
- **Primary LLM**: AWS Bedrock (Claude 4.5 Sonnet, Qwen3 235B, Nova 2 Lite) with Gemini fallback
- **Image Generation**: Qwen-Image (AWS SageMaker) with Bedrock Stable Diffusion fallback
- **Video Generation**: Wan2.2 (AWS SageMaker)
- **Web Search**: Unified tool with automatic fallback (Amazon Nova Search → Google Grounding)
- **Storage**: AWS S3 with presigned URLs (1-hour expiration) for secure media access
- **Memory Storage**: Redis for conversation context and agent state

## Specification Documents

All requirements are in `.kiro/specs/`:

| Document | Purpose |
|----------|---------|
| `ARCHITECTURE.md` | System architecture and tech stack |
| `INTERFACES.md` | MCP tools, WebSocket protocols, error codes |
| `SUMMARY.md` | Quick architecture overview |
| `web-platform/requirements.md` | Web Platform requirements (auth, billing, Credit system) |
| `ai-orchestrator/requirements.md` | AI Agent with Strands Agents implementation |
| `ad-creative/requirements.md` | Image generation capability |
| `market-insights/requirements.md` | Competitor analysis, trends |
| `ad-performance/requirements.md` | Data fetching, anomaly detection |
| `landing-page/requirements.md` | Landing page generation |
| `campaign-automation/requirements.md` | Campaign creation, budget optimization |

## MCP Tools Reference

High-priority tools defined in `INTERFACES.md`:

| Tool | Category | Purpose |
|------|----------|---------|
| `check_credit` / `deduct_credit` | Billing | Credit balance management |
| `create_creative` | Creative | Store generated assets |
| `create_campaign` | Ad Engine | Create ad campaigns |
| `get_reports` | Reporting | Fetch ad performance data |
| `get_credit_balance` | Billing | Check user credits |

## Error Codes

- `6011`: INSUFFICIENT_CREDITS
- `6012`: CREDIT_DEDUCTION_FAILED
- `6013`: SUBSCRIPTION_EXPIRED
- `4001-4003`: AI service errors
- `3001-3003`: MCP communication errors

## Environment Configuration

Both `backend/` and `ai-orchestrator/` require `.env` files. Copy from `.env.example` in each directory.

**Critical**: `WEB_PLATFORM_SERVICE_TOKEN` must be identical in both services for authentication.

```bash
# Generate a service token
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Required environment variables:
- **Backend**:
  - Core: `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `WEB_PLATFORM_SERVICE_TOKEN`
  - AWS: `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (or use IAM roles)
  - S3 Buckets: `S3_BUCKET_CREATIVES`, `S3_BUCKET_LANDING_PAGES`, `S3_BUCKET_EXPORTS`
  - CloudFront: `CLOUDFRONT_DOMAIN` (required for landing pages)
- **AI Orchestrator**: `GEMINI_API_KEY`, `WEB_PLATFORM_URL`, `WEB_PLATFORM_SERVICE_TOKEN`, `REDIS_URL`, `AWS_REGION`, `S3_BUCKET_CREATIVES`

### Storage Architecture

**S3 Bucket Structure** (需要手动创建):

1. **`aae-creatives`** - All creative assets (统一存储所有创意素材)
   ```
   users/{user_id}/uploaded/        # 用户手动上传的素材
   ├── {uuid}.png
   └── {uuid}.mp4

   users/{user_id}/generated/       # AI 生成的素材
   └── {session_id}/
       ├── {filename}.png
       └── {filename}.mp4
   ```
   - 包含用户上传和 AI 生成的所有素材
   - 所有素材记录同步到 `creatives` 数据表
   - 通过 S3 presigned URLs 提供访问（1小时有效期）

2. **`aae-landing-pages`** - Landing page HTML files (通过 CloudFront CDN 公开访问)
   ```
   {user_id}/{landing_page_id}/
   └── index.html
   ```
   - 独立存储，避免与 creative 素材混淆
   - **必须配置 CloudFront CDN** 提供公开访问
   - 发布后生成 CloudFront URL: `https://landing.zmead.com/{user_id}/{landing_page_id}/index.html`

3. **`aae-exports`** - Data export files (临时文件)
   ```
   users/{user_id}/exports/{date}/
   └── export.csv
   ```

**CloudFront CDN Setup** (Landing Pages):
1. Create CloudFront distribution pointing to `aae-landing-pages` bucket
2. Set `CLOUDFRONT_DOMAIN` environment variable (default: `landing.zmead.com`)
3. Landing pages will be accessible via: `https://landing.zmead.com/{user_id}/{landing_page_id}/index.html`

## Development Notes

- All specs are in Chinese with English technical terms
- Requirements follow WHEN/THEN acceptance criteria format
- Credit consumption rules are dynamically configurable
- AI Orchestrator communicates with Backend exclusively via MCP (no direct DB access)
- Backend uses async SQLAlchemy with aiomysql
- Frontend uses Next.js App Router (not Pages Router)
- Python version: 3.12+ required for both backend services
- Chat uses HTTP streaming (SSE) with real-time forwarding (no text buffering)
- Agent framework: Strands Agents with streaming via `stream_async()`
- Web Search: Unified `web_search` tool with automatic Nova → Google fallback
- Storage: S3 presigned URLs (1-hour expiration) for secure media access
- Frontend: Tool name mapping to user-friendly Chinese names (e.g., "互联网搜索")
- Model Selection: User can choose between Gemini and Bedrock providers in settings

## Important File Locations

```
Key configuration files:
├── backend/.env                     # Backend environment variables
├── backend/alembic.ini              # Database migration config
├── ai-orchestrator/.env             # AI orchestrator environment variables
├── frontend/.env.local              # Frontend environment variables
├── docker-compose.yml               # Docker services configuration
└── .kiro/specs/                     # All requirements and specs
    ├── ARCHITECTURE.md              # System architecture overview
    ├── INTERFACES.md                # API and protocol specifications
    └── */requirements.md            # Module-specific requirements
```

## Common Troubleshooting

### Backend won't start
```bash
# Check if MySQL is running
docker-compose ps mysql
# Check database connection
mysql -h 127.0.0.1 -u aae_user -paae_password aae_platform
```

### AI Orchestrator connection errors
```bash
# Verify WEB_PLATFORM_SERVICE_TOKEN matches in both .env files
grep WEB_PLATFORM_SERVICE_TOKEN backend/.env
grep WEB_PLATFORM_SERVICE_TOKEN ai-orchestrator/.env
```

### Frontend can't connect to backend
```bash
# Check NEXT_PUBLIC_API_URL in frontend/.env.local
# Should be http://localhost:8000 for local development
```
