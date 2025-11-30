---
inclusion: always
---

# Project Structure & Architecture

## Repository Layout

```
├── backend/              # FastAPI REST API (Python 3.12+)
├── frontend/             # Next.js 14 App Router (TypeScript)
├── ai-orchestrator/      # LangGraph AI agent service
└── .kiro/                # AI assistant configuration
```

## Backend Structure (`backend/app/`)

### Core Directories

| Path | Responsibility | Modification Triggers |
|------|----------------|----------------------|
| `api/v1/*.py` | REST endpoint definitions | New routes, request/response changes |
| `api/deps.py` | FastAPI dependencies (auth, DB, rate limits) | Shared middleware, dependency injection |
| `core/` | Infrastructure (config, DB, Redis, security, storage) | Environment changes, new integrations |
| `models/*.py` | SQLAlchemy ORM models | Database schema changes |
| `schemas/*.py` | Pydantic validation models | API contract changes |
| `services/*.py` | Business logic implementation | Feature logic, data processing |
| `tasks/*.py` | Celery async/scheduled jobs | Background operations |
| `mcp/tools/*.py` | MCP tool implementations for AI agent | AI capabilities, chat commands |

### Backend Architecture Flow

```
HTTP Request → api/v1/*.py → services/*.py → models/*.py → Database
                    ↓
              Depends(deps)
```

**Rules**:
- Endpoints are thin controllers that call services
- Services contain all business logic and orchestrate DB operations
- Never access models directly from endpoints
- All DB schema changes require Alembic migration: `alembic revision --autogenerate -m "description"`
- Use `Depends()` for auth (`get_current_user`), DB sessions (`get_db`), rate limiting

## Frontend Structure (`frontend/src/`)

### Core Directories

| Path | Responsibility | Modification Triggers |
|------|----------------|----------------------|
| `app/*/page.tsx` | Next.js route pages | New routes, page layouts |
| `components/{domain}/` | Feature-specific components | Domain UI features |
| `components/ui/` | Shadcn/ui base components | Primitive UI elements |
| `components/chat/` | AI chat interface components | Chat UX, embedded rendering |
| `hooks/*.ts` | Custom React hooks | Shared stateful logic |
| `lib/api.ts` | Backend API client | API integration |
| `lib/auth.ts` | Authentication utilities | Auth flow changes |
| `lib/store.ts` | Zustand global state | Cross-component state |
| `types/index.ts` | TypeScript type definitions | Type contracts |

### Frontend Architecture Flow

```
app/*/page.tsx → components/{domain}/ → lib/api.ts → Backend API
       ↓                                      ↓
  Server Component                    hooks/useWebSocket.ts
       ↓
  'use client' (only when needed)
```

**Rules**:
- Pages are Server Components by default (no `'use client'`)
- Add `'use client'` only for components with interactivity (onClick, useState, useEffect)
- Use `lib/api.ts` for REST calls, `hooks/useWebSocket.ts` for real-time chat
- Component organization: group by domain (`chat/`, `dashboard/`, `creatives/`), not by type
- Prefer named exports over default exports

## AI Orchestrator Structure (`ai-orchestrator/app/`)

### Core Directories

| Path | Responsibility |
|------|----------------|
| `modules/{domain}/capability.py` | Domain capability entry points |
| `modules/{domain}/managers/` | Orchestration logic |
| `modules/{domain}/analyzers/` | Data analysis components |
| `modules/{domain}/generators/` | Content generation |
| `modules/{domain}/models.py` | Domain data models |
| `nodes/*.py` | LangGraph workflow nodes |
| `core/graph.py` | LangGraph workflow definition |
| `prompts/*.py` | LLM prompt templates |

**Rules**:
- Each module is self-contained with its own models, managers, and utilities
- Capabilities are invoked via MCP tools from backend
- Use async/await for all I/O operations
- Return structured data for chat rendering (not plain text)

## File Naming Conventions

| Context | Convention | Examples |
|---------|-----------|----------|
| Python files | `snake_case.py` | `user_service.py`, `ad_account.py` |
| Python classes | `PascalCase` | `UserService`, `AdAccount` |
| React components | `PascalCase.tsx` | `ChatWindow.tsx`, `MetricCard.tsx` |
| TypeScript utilities | `camelCase.ts` | `apiClient.ts`, `formatDate.ts` |
| Database models | Singular file, plural table | `user.py` → `users` table |
| Pydantic schemas | Match model + suffix | `User` → `UserCreate`, `UserResponse`, `UserUpdate` |
| Test files | `test_*.py` | `test_user_service.py` |

## Key Architectural Patterns

### API Conventions

```python
# Backend endpoint pattern
@router.post("/campaigns", response_model=CampaignResponse)
async def create_campaign(
    campaign: CampaignCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await campaign_service.create(db, campaign, current_user.id)
```

- Routes: `/api/v1/{resource}` (plural nouns)
- Auth: `Authorization: Bearer <jwt>` header
- Errors: `{"detail": "error message"}` format
- Pagination: `?skip=0&limit=20` query params

### Database Patterns

```python
# Model conventions
class User(Base):
    __tablename__ = "users"  # Plural
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(onupdate=datetime.utcnow)
    deleted_at: Mapped[datetime | None]  # Soft delete
```

- All tables have `id`, `created_at`, `updated_at`
- Use soft deletes (`deleted_at`) for user-facing data
- Foreign keys: `{table}_id` (e.g., `user_id`, `campaign_id`)

### Component Organization

```
components/
├── chat/              # Chat domain
│   ├── ChatWindow.tsx
│   ├── MessageBubble.tsx
│   └── index.ts       # Barrel export
├── dashboard/         # Dashboard domain
└── ui/                # Primitives (button, card, input)
```

- Group by feature domain, not component type
- Each domain folder has `index.ts` for barrel exports
- Shared primitives go in `ui/`

## Adding New Features Checklist

### Backend API Endpoint
1. Create route in `backend/app/api/v1/{resource}.py`
2. Add to `backend/app/api/v1/router.py`
3. Create service in `backend/app/services/{resource}.py`
4. Create schemas in `backend/app/schemas/{resource}.py`
5. If DB changes: create model in `backend/app/models/{resource}.py`, run migration

### Frontend Page
1. Create `frontend/src/app/{route}/page.tsx`
2. Create components in `frontend/src/components/{domain}/`
3. Add API calls to `frontend/src/lib/api.ts` if needed
4. Update types in `frontend/src/types/index.ts`

### MCP Tool (AI Capability)
1. Implement capability in `ai-orchestrator/app/modules/{domain}/`
2. Create MCP tool in `backend/app/mcp/tools/{resource}.py`
3. Register in `backend/app/mcp/registry.py`
4. Add chat rendering in `frontend/src/components/chat/`

### Database Migration
```bash
# After modifying models
cd backend
alembic revision --autogenerate -m "add user preferences table"
alembic upgrade head
```

## Critical Rules

- **Never** bypass the service layer (endpoints → services → models)
- **Never** commit without running migrations if models changed
- **Never** use `'use client'` on pages unless absolutely necessary
- **Always** use `Depends()` for auth and DB sessions in endpoints
- **Always** create Pydantic schemas for request/response validation
- **Always** handle errors with proper HTTP status codes and `{"detail": "message"}` format
