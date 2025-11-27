# Celery Task Scheduling

This document describes the Celery task scheduling setup for the AAE Web Platform.

## Overview

The Web Platform uses Celery with Redis as the message broker for background task processing and scheduling. Celery Beat is used as the scheduler to run periodic tasks.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Celery Task Scheduling Architecture             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Celery Beat (Scheduler)                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Scheduled Tasks:                                    │   │
│  │  - Token check: Daily at 2:00 AM UTC                │   │
│  │  - Data fetch: Every 6 hours (00:00, 06:00, etc.)   │   │
│  │  - Daily report: Daily at 9:00 AM UTC               │   │
│  │  - Anomaly detection: Every hour                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                   │
│                          ▼                                   │
│  Redis (Message Broker)                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  - Task queue                                        │   │
│  │  - Result backend                                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                   │
│                          ▼                                   │
│  Celery Worker (Executor)                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  1. Receive scheduled task                           │   │
│  │  2. Execute task logic                               │   │
│  │  3. Store result in Redis                            │   │
│  │  4. Retry on failure (max 3 times)                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Scheduled Tasks

### 1. Token Expiry Check
- **Task**: `app.tasks.token_refresh.check_token_expiry`
- **Schedule**: Daily at 2:00 AM UTC
- **Purpose**: Check for ad account tokens expiring within 24 hours and attempt to refresh them
- **Retry**: Up to 3 times with 5-minute delay
- **Requirements**: 2.1.1, 2.1.2, 2.1.3, 2.1.4, 12.2.2, 12.2.5

### 2. Data Fetch
- **Task**: `app.tasks.data_fetch.fetch_ad_data`
- **Schedule**: Every 6 hours (00:00, 06:00, 12:00, 18:00 UTC)
- **Purpose**: Fetch ad performance data from connected platforms (Meta, TikTok, Google)
- **Retry**: Up to 3 times with 5-minute delay
- **Requirements**: 12.2.1
- **Note**: Currently a placeholder for Ad Performance module integration

### 3. Daily Report Generation
- **Task**: `app.tasks.reports.generate_daily_report`
- **Schedule**: Daily at 9:00 AM UTC
- **Purpose**: Generate daily performance reports for all active users
- **Retry**: Up to 3 times with 5-minute delay
- **Requirements**: 12.2.1
- **Note**: Currently a placeholder for Ad Performance module integration

### 4. Anomaly Detection
- **Task**: `app.tasks.anomaly_detection.detect_anomalies`
- **Schedule**: Every hour
- **Purpose**: Detect anomalies in ad performance (CPA spikes, ROAS drops, etc.)
- **Retry**: Up to 3 times with 5-minute delay
- **Requirements**: 12.2.1
- **Note**: Currently a placeholder for Ad Performance module integration

## Running Celery

### Prerequisites

1. Redis must be running:
```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or using local Redis
redis-server
```

2. Environment variables must be set in `.env`:
```env
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

### Starting Celery Worker

```bash
cd backend

# Start Celery worker
celery -A app.core.celery:celery_app worker --loglevel=info

# Or with auto-reload for development
watchmedo auto-restart --directory=./app --pattern=*.py --recursive -- \
  celery -A app.core.celery:celery_app worker --loglevel=info
```

### Starting Celery Beat (Scheduler)

```bash
cd backend

# Start Celery Beat scheduler
celery -A app.core.celery:celery_app beat --loglevel=info

# Or with persistent schedule (recommended for production)
celery -A app.core.celery:celery_app beat --loglevel=info \
  --schedule=/tmp/celerybeat-schedule
```

### Running Both Together

For development, you can run both worker and beat in a single process:

```bash
cd backend

celery -A app.core.celery:celery_app worker --beat --loglevel=info
```

**Note**: In production, run worker and beat as separate processes for better reliability.

## Monitoring

### Flower (Web-based monitoring)

Install Flower:
```bash
pip install flower
```

Start Flower:
```bash
celery -A app.core.celery:celery_app flower --port=5555
```

Access at: http://localhost:5555

### Command-line monitoring

```bash
# List active tasks
celery -A app.core.celery:celery_app inspect active

# List scheduled tasks
celery -A app.core.celery:celery_app inspect scheduled

# List registered tasks
celery -A app.core.celery:celery_app inspect registered

# Check worker stats
celery -A app.core.celery:celery_app inspect stats
```

## Task Configuration

### Retry Configuration

All tasks are configured with:
- **Max retries**: 3
- **Retry delay**: 300 seconds (5 minutes)
- **Retry on failure**: Automatic

### Task Timeouts

- **Hard timeout**: 3600 seconds (1 hour)
- **Soft timeout**: 3300 seconds (55 minutes)

### Worker Configuration

- **Prefetch multiplier**: 1 (one task at a time)
- **Task acknowledgment**: Late (after task completion)
- **Reject on worker lost**: True (requeue tasks if worker crashes)

## Production Deployment

### Using Supervisor

Create `/etc/supervisor/conf.d/celery.conf`:

```ini
[program:celery-worker]
command=/path/to/venv/bin/celery -A app.core.celery:celery_app worker --loglevel=info
directory=/path/to/backend
user=www-data
numprocs=1
stdout_logfile=/var/log/celery/worker.log
stderr_logfile=/var/log/celery/worker.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600

[program:celery-beat]
command=/path/to/venv/bin/celery -A app.core.celery:celery_app beat --loglevel=info --schedule=/var/run/celerybeat-schedule
directory=/path/to/backend
user=www-data
numprocs=1
stdout_logfile=/var/log/celery/beat.log
stderr_logfile=/var/log/celery/beat.log
autostart=true
autorestart=true
startsecs=10
```

### Using systemd

Create `/etc/systemd/system/celery-worker.service`:

```ini
[Unit]
Description=Celery Worker
After=network.target redis.target

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/path/to/backend
ExecStart=/path/to/venv/bin/celery -A app.core.celery:celery_app worker --loglevel=info --pidfile=/var/run/celery/worker.pid
Restart=always

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/celery-beat.service`:

```ini
[Unit]
Description=Celery Beat
After=network.target redis.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/path/to/backend
ExecStart=/path/to/venv/bin/celery -A app.core.celery:celery_app beat --loglevel=info --schedule=/var/run/celery/beat-schedule
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable celery-worker celery-beat
sudo systemctl start celery-worker celery-beat
```

## Troubleshooting

### Task not executing

1. Check if Celery Beat is running:
```bash
ps aux | grep celery
```

2. Check Redis connection:
```bash
redis-cli ping
```

3. Check Celery logs:
```bash
celery -A app.core.celery:celery_app inspect active
```

### Task failing repeatedly

1. Check task logs in Celery worker output
2. Verify database connection
3. Check if required services are running (Redis, MySQL)
4. Review task retry configuration

### Schedule not updating

1. Delete the schedule file:
```bash
rm /tmp/celerybeat-schedule
```

2. Restart Celery Beat

## Testing Tasks Manually

You can trigger tasks manually for testing:

```python
from app.tasks import check_token_expiry, fetch_ad_data

# Trigger immediately
result = check_token_expiry.delay()

# Get result
print(result.get(timeout=60))

# Or apply async with custom options
result = fetch_ad_data.apply_async(countdown=10)  # Run after 10 seconds
```

## References

- [Celery Documentation](https://docs.celeryproject.org/)
- [Celery Beat Documentation](https://docs.celeryproject.org/en/stable/userguide/periodic-tasks.html)
- Requirements: 12.2.1, 12.2.2, 12.2.5, 2.1.1, 2.1.2, 2.1.3, 2.1.4
