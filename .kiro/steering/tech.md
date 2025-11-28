# Technology Stack

## Frontend

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript 5
- **Styling**: Tailwind CSS 3.4
- **UI Components**: Shadcn/ui + Radix UI
- **State Management**: Zustand
- **Data Fetching**: TanStack Query (React Query)
- **AI Chat**: Vercel AI SDK (`ai` package)
- **Charts**: Recharts
- **HTTP Client**: Axios

## Backend

- **Framework**: FastAPI (Python 3.12+)
- **ORM**: SQLAlchemy 2.0
- **Database Driver**: aiomysql
- **Migrations**: Alembic
- **Task Queue**: Celery 5.4
- **Authentication**: python-jose (JWT)
- **Password Hashing**: bcrypt
- **Validation**: Pydantic 2.9
- **HTTP Client**: httpx
- **Payment**: Stripe SDK

## AI & MCP

- **AI Models**: Google Gemini 2.5 (Flash/Pro), Imagen 3, Veo 3.1
- **Orchestration**: LangChain / LlamaIndex
- **Protocol**: Model Context Protocol (MCP)
- **Ad Platform APIs**: Meta Marketing API, TikTok Ads API

## Data Layer

- **Primary Database**: MySQL 8.4 (via AWS RDS)
- **Time-Series**: TimescaleDB extension (planned)
- **Cache/Sessions**: Redis 7.x
- **File Storage**: AWS S3
- **CDN**: CloudFront

## Infrastructure

- **Containerization**: Docker
- **Orchestration**: docker-compose (dev), AWS ECS (prod)
- **Region**: AWS Singapore
- **Web Server**: Uvicorn (ASGI)

## Development Tools

- **Linting**: Ruff (Python), ESLint (TypeScript)
- **Type Checking**: mypy (Python), TypeScript
- **Testing**: pytest + pytest-asyncio (backend)
- **Code Quality**: Ruff line-length=100, Python 3.12 target

## Common Commands

### Backend

```bash
# Setup
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -e ".[dev]"

# Database
alembic upgrade head           # Run migrations
alembic revision --autogenerate -m "message"  # Create migration

# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Background Tasks
celery -A app.core.celery worker --loglevel=info
celery -A app.core.celery beat --loglevel=info

# Testing
pytest
pytest --cov=app tests/
```

### Frontend

```bash
# Setup
npm install

# Development
npm run dev      # Start dev server (http://localhost:3000)

# Production
npm run build    # Build for production
npm start        # Start production server

# Code Quality
npm run lint     # Run ESLint
```

### Docker

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f [service_name]

# Rebuild
docker-compose up -d --build
```

## Environment Variables

- Backend: `backend/.env` (see `.env.example`)
- Frontend: `frontend/.env.local` (see `.env.example`)
- Required: Database credentials, Redis URL, AWS credentials, API keys
