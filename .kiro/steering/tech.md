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

## Python Code Style (Backend & AI Orchestrator)

### Formatting & Structure
- Line length: 100 characters (Ruff enforced)
- Import order: stdlib → third-party → local (Ruff auto-sorts)
- Use `async/await` for ALL I/O operations (database, HTTP, file operations)
- Type hints REQUIRED on all function signatures (parameters and return types)

### Type Annotations
```python
# Required pattern
async def get_user(db: Session, user_id: str) -> User | None:
    return await db.get(User, user_id)

# SQLAlchemy models use Mapped[]
class User(Base):
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
```

### Validation & Models
- Use Pydantic v2 models for ALL request/response validation
- Define separate schemas for Create/Update/Response operations
- Use `ConfigDict` for Pydantic configuration (not `Config` class)

```python
from pydantic import BaseModel, ConfigDict

class UserCreate(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    email: str
    created_at: datetime
```

### Error Handling
- Raise `HTTPException` for API errors with appropriate status codes
- Use `{"detail": "message"}` format for error responses
- Include actionable error messages for users

```python
from fastapi import HTTPException, status

if not user:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )
```

## TypeScript Code Style (Frontend)

### Configuration
- Strict mode enabled in `tsconfig.json`
- Use ESLint rules from `.eslintrc.json`
- Prefer named exports over default exports

### Type Definitions
```typescript
// Use interface for object shapes
interface User {
  id: string;
  email: string;
  createdAt: string;
}

// Use type for unions/intersections
type Status = 'active' | 'paused' | 'completed';
type UserWithStatus = User & { status: Status };
```

### React Components
- Server Components by default (no `'use client'`)
- Add `'use client'` ONLY when using: `useState`, `useEffect`, `onClick`, event handlers
- Use Tailwind utility classes; avoid inline styles
- Prefer composition over prop drilling

```typescript
// Server Component (default)
export default async function Page() {
  const data = await fetchData();
  return <div>{data}</div>;
}

// Client Component (only when needed)
'use client';
export function InteractiveButton() {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(count + 1)}>{count}</button>;
}
```

### Styling
- Use Tailwind classes exclusively
- Use `cn()` utility from `lib/utils.ts` for conditional classes
- Avoid inline styles unless absolutely necessary

## API Conventions

### REST Endpoints
- Base path: `/api/v1/{resource}` (plural nouns)
- Authentication: `Authorization: Bearer <jwt>` header
- Error format: `{"detail": "error message"}`
- Pagination: `?skip=0&limit=20` query parameters
- HTTP methods: GET (read), POST (create), PUT (full update), PATCH (partial), DELETE

### Response Patterns
```python
# Success response
return {"data": result, "message": "Operation successful"}

# List response with pagination
return {
    "items": results,
    "total": count,
    "skip": skip,
    "limit": limit
}

# Error response
raise HTTPException(status_code=400, detail="Invalid input")
```

### WebSocket
- Chat endpoint: `/ws/chat`
- Message format: `{"type": "user"|"assistant", "content": str, "metadata": dict}`
- Handle reconnection gracefully on client side

## Database Patterns

### Model Conventions
```python
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

class BaseModel(Base):
    __abstract__ = True
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    deleted_at: Mapped[datetime | None]  # Soft delete
```

- Table names: plural (`users`, `campaigns`, `ad_accounts`)
- Primary key: `id` (String UUID, not auto-increment)
- Timestamps: `created_at`, `updated_at` on ALL tables
- Soft delete: `deleted_at` for user-facing data
- Foreign keys: `{table}_id` (e.g., `user_id`, `campaign_id`)

### Migrations
```bash
# After modifying models in backend/app/models/
cd backend
alembic revision --autogenerate -m "descriptive message"
alembic upgrade head
```

**CRITICAL**: Always run migrations after model changes before committing.

### Query Patterns
```python
# Use async session methods
async def get_user(db: AsyncSession, user_id: str) -> User | None:
    result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()

# Use soft delete
async def delete_user(db: AsyncSession, user_id: str) -> None:
    user = await get_user(db, user_id)
    user.deleted_at = datetime.utcnow()
    await db.commit()
```

## Testing Requirements

### Backend (pytest)
- Framework: pytest + pytest-asyncio
- Mark async tests: `@pytest.mark.asyncio`
- Fixtures in `conftest.py` for shared setup
- Property-based tests with Hypothesis for complex logic
- Test file naming: `test_{module}.py`

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_user(client: AsyncClient, db_session):
    response = await client.post("/api/v1/users", json={
        "email": "test@example.com",
        "password": "secure123"
    })
    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"
```

### Frontend
- No tests required unless explicitly requested by user
- If tests are requested, use Jest + React Testing Library

## Development Commands

### Backend
```bash
cd backend

# Development server (auto-reload)
uvicorn app.main:app --reload --port 8000

# Run tests
pytest

# Run tests with coverage
pytest --cov=app --cov-report=html

# Lint and format
ruff check .
ruff format .

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1  # Rollback one migration
```

### Frontend
```bash
cd frontend

# Development server
npm run dev  # Runs on port 3000

# Build for production
npm run build

# Lint
npm run lint

# Type check
npx tsc --noEmit
```

### AI Orchestrator
```bash
cd ai-orchestrator

# Development server
uvicorn app.main:app --reload --port 8001

# Run tests
pytest

# Lint
ruff check .
```

### Docker
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f [service_name]

# Rebuild after dependency changes
docker-compose up -d --build

# Stop all services
docker-compose down
```

## Environment Configuration

### Required Files
- `backend/.env` (copy from `.env.example`)
- `frontend/.env.local` (copy from `.env.example`)
- `ai-orchestrator/.env` (copy from `.env.example`)

### Key Environment Variables
```bash
# Backend
DATABASE_URL=mysql+aiomysql://user:pass@localhost:3306/aae
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=your-secret-key
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# AI Orchestrator
GEMINI_API_KEY=...
MCP_SERVER_URL=http://localhost:8000
```

## Dependency Management

### Python (Backend & AI Orchestrator)
- Use `pyproject.toml` for dependency specification
- Pin major versions, allow minor/patch updates
- After adding dependencies: `pip install -e .` or rebuild Docker

### TypeScript (Frontend)
- Use `package.json` for dependencies
- After adding dependencies: `npm install`
- Prefer exact versions for production dependencies

## Critical Rules

1. **Async/Await**: ALL I/O operations MUST use `async/await` (no blocking calls)
2. **Type Safety**: Type hints required in Python, strict mode in TypeScript
3. **Validation**: Use Pydantic for ALL API request/response validation
4. **Migrations**: Run Alembic migrations after ANY model changes
5. **Error Handling**: Use proper HTTP status codes and structured error responses
6. **Server Components**: Use `'use client'` only when absolutely necessary
7. **Soft Deletes**: Use `deleted_at` for user-facing data, not hard deletes
8. **Authentication**: Always use `Depends(get_current_user)` for protected endpoints
