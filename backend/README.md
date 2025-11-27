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
│   └── tasks/            # Celery tasks
├── tests/                # Test files
├── .env.example          # Environment template
├── alembic.ini           # Alembic configuration
└── pyproject.toml        # Project dependencies
```
