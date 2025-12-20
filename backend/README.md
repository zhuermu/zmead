# AAE Web Platform - Backend

FastAPI backend for the AAE (Automated Ad Engine) Web Platform with AWS integration.

## Requirements

- Python 3.12+
- MySQL 8.4+
- Redis 7.x
- AWS Account with:
  - S3 buckets configured
  - IAM user/role with appropriate permissions
  - (Optional) CloudFront distribution for CDN

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

## AWS Configuration

### S3 Storage Setup

The backend uses Amazon S3 for file storage. See [AWS Setup Guide](../AWS_SETUP_GUIDE.md) for detailed instructions.

Quick setup:

```bash
# Create S3 buckets
aws s3 mb s3://aae-creatives --region us-west-2
aws s3 mb s3://aae-landing-pages --region us-west-2
aws s3 mb s3://aae-exports --region us-west-2
aws s3 mb s3://aae-user-uploads --region us-west-2

# Configure CORS (see AWS_SETUP_GUIDE.md for cors-config.json)
aws s3api put-bucket-cors --bucket aae-creatives --cors-configuration file://cors-config.json
```

### AWS Credentials

For development, use AWS CLI credentials:

```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Enter region: us-west-2
```

For production, use IAM roles (recommended):

```bash
# Attach IAM role to EC2/ECS instance
# No credentials needed in .env file
```

### Configuration Validation

Validate your AWS configuration:

```bash
python -m app.core.aws_config_validator
```

Expected output:
```
✓ AWS credentials configured
✓ S3 buckets accessible
✓ Configuration valid
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
WEB_PLATFORM_SERVICE_TOKEN=your-generated-token-here
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
- Store production tokens in AWS Secrets Manager

## Additional Documentation

- [AWS Setup Guide](../AWS_SETUP_GUIDE.md) - Complete AWS setup instructions
- [AWS Troubleshooting Guide](../AWS_TROUBLESHOOTING_GUIDE.md) - Common issues and solutions
- [AWS Deployment Guide](../AWS_DEPLOYMENT_GUIDE.md) - Production deployment
- [S3 Storage Guide](./S3_STORAGE_GUIDE.md) - S3 storage implementation details
- [AWS Configuration Guide](./AWS_CONFIGURATION_GUIDE.md) - Backend AWS configuration
