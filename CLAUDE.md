# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AAE (Automated Ad Engine) is an advertising SaaS platform with an embedded AI agent assistant. Users interact through a unified conversational interface to manage ad campaigns across Meta, TikTok, and Google Ads.

**Core Architecture**: 3 services communicating via HTTP/MCP:
- **Frontend** (Next.js, port 3000) - User interface with Vercel AI SDK chat
- **Backend** (FastAPI, port 8000) - REST API, MCP Server, data storage
- **AI Orchestrator** (FastAPI + LangGraph, port 8001) - Intent recognition, module coordination

## Development Commands

### Infrastructure (Docker)
```bash
# Start all services (MySQL, Redis, backend, ai-orchestrator, frontend)
docker-compose up -d

# Start only MySQL and Redis for local development
docker-compose up -d mysql redis

# Stop services
docker-compose down
```

### Backend (FastAPI) - Port 8000
```bash
cd backend

# Setup virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies (including dev tools)
pip install -e ".[dev]"

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest

# Run single test file
pytest tests/test_file.py

# Run with coverage
pytest --cov=app

# Linting and type checking
ruff check app/
mypy app/

# Celery worker (background tasks)
celery -A app.core.celery worker --loglevel=info

# Celery beat (scheduler)
celery -A app.core.celery beat --loglevel=info
```

### AI Orchestrator (FastAPI + LangGraph) - Port 8001
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

# Run with coverage
pytest --cov=app tests/

# Linting and type checking
ruff check .
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
├── ai-orchestrator/         # AI Agent Service (FastAPI + LangGraph)
│   ├── app/
│   │   ├── api/             # Chat streaming endpoint
│   │   ├── core/            # Config, state, graph builder
│   │   ├── nodes/           # LangGraph nodes (router, modules, respond)
│   │   ├── modules/         # Capability module implementations
│   │   ├── prompts/         # LLM prompt templates
│   │   └── services/        # MCP client, Gemini client
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
Unified AI Agent (LangGraph)
├── Intent Recognition (Gemini 2.5 Flash)
├── Orchestrator (协调器)
└── 5 Capability Modules:
    ├── Ad Creative (素材生成)
    ├── Market Insights (市场洞察)
    ├── Ad Performance (报表分析)
    ├── Landing Page (落地页)
    └── Campaign Automation (广告投放)
```

## Key Technical Decisions

- **AI Agent Framework**: LangGraph (state machine with checkpointing)
- **Frontend Chat**: Vercel AI SDK (`ai` package) with streaming
- **State Management**: Zustand (frontend), React Query for server state
- **Communication**: HTTP Streaming (frontend ↔ agent) + MCP Protocol (agent ↔ portal)
- **Billing**: Credit-based system (¥199/30K credits, ¥1999/400K credits, overage at ¥0.01/credit)
- **Primary LLM**: Gemini 2.5 Flash (Claude 3.5 Sonnet as fallback)
- **Image Generation**: AWS Bedrock Stable Diffusion XL

## Specification Documents

All requirements are in `.kiro/specs/`:

| Document | Purpose |
|----------|---------|
| `ARCHITECTURE.md` | System architecture and tech stack |
| `INTERFACES.md` | MCP tools, WebSocket protocols, error codes |
| `SUMMARY.md` | Quick architecture overview |
| `web-platform/requirements.md` | Web Platform requirements (auth, billing, Credit system) |
| `ai-orchestrator/requirements.md` | AI Agent with LangGraph implementation |
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
- **Backend**: `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `WEB_PLATFORM_SERVICE_TOKEN`
- **AI Orchestrator**: `GEMINI_API_KEY`, `WEB_PLATFORM_URL`, `WEB_PLATFORM_SERVICE_TOKEN`, `REDIS_URL`

## Development Notes

- All specs are in Chinese with English technical terms
- Requirements follow WHEN/THEN acceptance criteria format
- Credit consumption rules are dynamically configurable
- Capability modules communicate with User Portal exclusively via MCP (no direct DB access)
- Backend uses async SQLAlchemy with aiomysql
- Frontend uses Next.js App Router (not Pages Router)
- Python version: 3.12+ required for both backend services
