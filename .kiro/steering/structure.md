---
inclusion: always
---

# Project Structure

## Repository Layout

| Directory | Purpose |
|-----------|---------|
| `backend/` | FastAPI backend (Python 3.12+) |
| `frontend/` | Next.js 14 frontend (TypeScript) |
| `ai-orchestrator/` | LangGraph AI agent service |
| `.kiro/` | Kiro AI assistant configuration |

## Backend (`backend/app/`)

| Path | Purpose | When to Modify |
|------|---------|----------------|
| `api/v1/` | REST endpoints | Adding/modifying API routes |
| `api/deps.py` | Dependency injection | Adding shared dependencies |
| `core/` | Config, DB, Redis, security | Infrastructure changes |
| `models/` | SQLAlchemy ORM models | Schema changes (requires migration) |
| `schemas/` | Pydantic request/response | API contract changes |
| `services/` | Business logic layer | Feature implementation |
| `tasks/` | Celery background jobs | Async/scheduled operations |
| `mcp/tools/` | MCP tool implementations | AI agent capabilities |

## Frontend (`frontend/src/`)

| Path | Purpose | When to Modify |
|------|---------|----------------|
| `app/` | Next.js App Router pages | Adding routes/pages |
| `components/` | React components by domain | UI features |
| `components/ui/` | Shadcn/ui primitives | Base UI elements |
| `components/chat/` | AI chat interface | Chat UX changes |
| `hooks/` | Custom React hooks | Shared stateful logic |
| `lib/` | Utilities (api, auth, store) | Core client logic |
| `types/` | TypeScript definitions | Type changes |

## Architecture Rules

**Backend Flow**: `api/v1/*.py` → `services/*.py` → `models/*.py`
- Endpoints call services, services handle business logic and DB access
- Use `Depends()` for auth, DB sessions, rate limiting
- All DB changes require Alembic migrations

**Frontend Flow**: `app/` pages → `components/` → `lib/` utilities
- Pages are Server Components by default
- Add `'use client'` only for interactive components
- Use Zustand for global state, React Query for server state

## Key Conventions

| Area | Convention |
|------|------------|
| API Routes | `/api/v1/{resource}` prefix |
| Auth | JWT in `Authorization: Bearer` header |
| WebSocket | `/ws/chat` for real-time chat |
| File Storage | S3 via `backend/app/core/storage.py` |
| Errors | Consistent JSON: `{"detail": "message"}` |
| Migrations | `alembic revision --autogenerate -m "desc"` |

## File Naming

- Backend: `snake_case.py` for all Python files
- Frontend: `PascalCase.tsx` for components, `camelCase.ts` for utilities
- Models: Singular (`user.py`), tables plural (`users`)
- Schemas: Match model name (`user.py` → `UserCreate`, `UserResponse`)

## Adding New Features

1. **New API endpoint**: Create in `backend/app/api/v1/`, add to `router.py`
2. **New model**: Create in `models/`, add to `__init__.py`, create migration
3. **New service**: Create in `services/`, inject via `Depends()`
4. **New page**: Create folder in `frontend/src/app/` with `page.tsx`
5. **New component**: Create in appropriate `components/` subdirectory
6. **New MCP tool**: Create in `backend/app/mcp/tools/`, register in `registry.py`
