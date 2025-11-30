---
inclusion: always
---

# Technology Stack & Conventions

## Stack Overview

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14 (App Router), TypeScript 5, Tailwind CSS 3.4, Shadcn/ui |
| Backend | FastAPI, Python 3.12+, SQLAlchemy 2.0, Pydantic 2.9 |
| AI Orchestrator | LangGraph, Google Gemini 2.5, MCP Protocol |
| Database | MySQL 8.4, Redis 7.x |
| Infrastructure | Docker, AWS (S3, RDS, ECS) |

## Code Style Rules

### Python (Backend & AI Orchestrator)
- Line length: 100 characters (Ruff enforced)
- Use `async/await` for all I/O operations
- Type hints required on all function signatures
- Imports: stdlib → third-party → local (Ruff auto-sorts)
- Use Pydantic models for request/response validation
- SQLAlchemy models use `Mapped[]` type annotations

### TypeScript (Frontend)
- Strict mode enabled
- Use `interface` for object shapes, `type` for unions/intersections
- Prefer named exports over default exports
- Components: `'use client'` only when interactivity required
- Use Tailwind classes; avoid inline styles

## API Conventions

### REST Endpoints
- Prefix: `/api/v1/{resource}`
- Auth: `Authorization: Bearer <jwt>` header
- Errors: `{"detail": "message"}` format
- Pagination: `?skip=0&limit=20`

### WebSocket
- Chat endpoint: `/ws/chat`
- Message format: JSON with `type`, `content`, `metadata` fields

## Database Patterns

### Migrations
```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Model Conventions
- Table names: plural (`users`, `campaigns`)
- Primary key: `id` (UUID)
- Timestamps: `created_at`, `updated_at` on all tables
- Soft delete: `deleted_at` where applicable

## Testing Requirements

### Backend
- Framework: pytest + pytest-asyncio
- Use `@pytest.mark.asyncio` for async tests
- Fixtures in `conftest.py`
- Property-based tests with Hypothesis where applicable

### Frontend
- No tests required unless explicitly requested

## Common Commands

| Task | Command |
|------|---------|
| Backend dev server | `uvicorn app.main:app --reload --port 8000` |
| Frontend dev server | `npm run dev` (port 3000) |
| Run migrations | `alembic upgrade head` |
| Backend tests | `pytest` |
| Lint Python | `ruff check .` |
| Lint TypeScript | `npm run lint` |
| Docker up | `docker-compose up -d` |

## Environment Files

- Backend: `backend/.env` (copy from `.env.example`)
- Frontend: `frontend/.env.local` (copy from `.env.example`)
- AI Orchestrator: `ai-orchestrator/.env` (copy from `.env.example`)
