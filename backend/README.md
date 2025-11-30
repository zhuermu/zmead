# AAE Web Platform - Backend

FastAPI backend for the AAE (Automated Ad Engine) Web Platform.

## Requirements

- Python 3.12+
- MySQL 8.4+
- Redis 7.x
- AWS Account (for S3)

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -e ".[dev]"
```

3. Copy environment file and configure:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run database migrations:
```bash
alembic upgrade head
```

5. Start the development server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Development

### Running Tests
```bash
pytest
```

### Running Celery Worker
```bash
celery -A app.core.celery worker --loglevel=info
```

### Running Celery Beat (Scheduler)
```bash
celery -A app.core.celery beat --loglevel=info
```

## Project Structure

```
backend/
├── alembic/              # Database migrations
├── app/
│   ├── api/              # API endpoints
│   ├── core/             # Core configuration
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   ├── mcp/              # MCP server and tools
│   └── tasks/            # Celery tasks
├── tests/                # Test files
├── .env.example          # Environment template
├── alembic.ini           # Alembic configuration
└── pyproject.toml        # Project dependencies
```

## Service-to-Service Authentication

### AI Orchestrator Service Token

The Web Platform communicates with the AI Orchestrator using a service token for authentication.

#### Generating a Service Token

Generate a secure random token for service-to-service authentication:

```bash
# Using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Or using OpenSSL
openssl rand -base64 32
```

#### Configuration

1. Add the generated token to `backend/.env`:
```bash
AI_ORCHESTRATOR_SERVICE_TOKEN=your-generated-token-here
```

2. Add the same token to `ai-orchestrator/.env`:
```bash
WEB_PLATFORM_SERVICE_TOKEN=your-generated-token-here
```

The Web Platform will include this token in the `Authorization` header when calling the AI Orchestrator:
```
Authorization: Bearer <service_token>
```

#### Security Notes

- Use a unique token for each environment (development, staging, production)
- Rotate tokens periodically in production
- Never commit tokens to version control
- Store production tokens in a secrets manager (e.g., AWS Secrets Manager)
