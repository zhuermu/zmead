---
inclusion: always
---

# Testing & Dependency Management

## Python Code Execution Rules

**CRITICAL**: NEVER use `python -c "code"` pattern for executing Python code. This causes PTY host exceptions and terminal disconnections that block execution.

### Correct Patterns

```bash
# ✅ Write to file and execute
echo "print('test')" > temp_script.py
python temp_script.py

# ✅ Use pytest for testing
pytest tests/test_module.py

# ✅ Use Python REPL for interactive exploration
python
>>> import module
>>> module.function()
```

### Incorrect Patterns

```bash
# ❌ NEVER do this - causes terminal disconnection
python -c "import sys; print(sys.version)"
```

## Testing Framework

### Backend & AI Orchestrator (pytest)

- Framework: `pytest` with `pytest-asyncio` for async tests
- Test location: `tests/` directory in each service
- Naming: `test_{module}.py` for test files, `test_{function}` for test functions
- Mark async tests: `@pytest.mark.asyncio`
- Property-based testing: Use `hypothesis` for complex logic validation

```python
# Example test structure
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_campaign(client: AsyncClient, db_session):
    response = await client.post("/api/v1/campaigns", json={
        "name": "Test Campaign",
        "budget": 1000
    })
    assert response.status_code == 201
    assert response.json()["name"] == "Test Campaign"
```

### Running Tests

```bash
# Backend
cd backend
pytest                                    # Run all tests
pytest tests/test_auth.py                # Run specific file
pytest -k "test_user"                    # Run tests matching pattern
pytest --cov=app --cov-report=html       # With coverage

# AI Orchestrator
cd ai-orchestrator
pytest                                    # Run all tests
pytest tests/ad_performance/             # Run directory
```

### Frontend Testing

- Tests are NOT required by default unless explicitly requested
- If requested, use Jest + React Testing Library
- Run with: `npm test` in `frontend/` directory

## Dependency Management

### When Adding Dependencies

**CRITICAL**: When discovering or adding third-party packages during development, immediately update the appropriate dependency file:

#### Python Dependencies

```bash
# Backend
cd backend
# Add to pyproject.toml [project.dependencies]
pip install -e .

# AI Orchestrator
cd ai-orchestrator
# Add to pyproject.toml [project.dependencies]
pip install -e .
```

#### TypeScript Dependencies

```bash
# Frontend
cd frontend
npm install <package-name>
# Automatically updates package.json and package-lock.json
```

### Dependency File Locations

| Service | File | Format |
|---------|------|--------|
| Backend | `backend/pyproject.toml` | Python project config |
| AI Orchestrator | `ai-orchestrator/pyproject.toml` | Python project config |
| Frontend | `frontend/package.json` | npm dependencies |

### Version Pinning Strategy

- **Python**: Pin major versions, allow minor/patch updates (e.g., `fastapi>=0.104.0,<1.0.0`)
- **TypeScript**: Use exact versions for production dependencies (e.g., `"next": "14.0.4"`)
- **Development dependencies**: Can use caret ranges (e.g., `"^1.2.3"`)

## Internationalization (i18n)

### Language Support

The system supports bilingual interfaces (Chinese/English):

| Component | Implementation |
|-----------|----------------|
| UI text | Externalize all user-facing strings to i18n files |
| Error messages | Provide translations for both languages |
| API responses | Support `Accept-Language` header |
| User preference | Language setting stored in user profile |

### Implementation Guidelines

#### Backend (FastAPI)

```python
# Use language-aware error messages
from fastapi import HTTPException, Header

async def endpoint(accept_language: str = Header(default="en")):
    if error:
        message = {
            "en": "Campaign not found",
            "zh": "未找到广告系列"
        }.get(accept_language[:2], "Campaign not found")
        raise HTTPException(status_code=404, detail=message)
```

#### Frontend (Next.js)

```typescript
// Use i18n keys instead of hardcoded strings
// ❌ Bad
<button>Create Campaign</button>

// ✅ Good
<button>{t('campaign.create')}</button>
```

### Language Consistency Rules

1. **Never hardcode user-facing strings** - Always use i18n keys or constants
2. **Maintain terminology consistency** - Use the same translation for the same concept
3. **Document language-specific logic** - Note any business rules that vary by language
4. **Test both languages** - Verify UI and functionality in both Chinese and English
5. **Default to English** - If language detection fails, fall back to English

### Translation File Structure

```
frontend/
  locales/
    en.json          # English translations
    zh.json          # Chinese translations
```

## Code Quality Checks

### Before Committing

```bash
# Backend - Lint and format
cd backend
ruff check .
ruff format .

# AI Orchestrator - Lint and format
cd ai-orchestrator
ruff check .
ruff format .

# Frontend - Lint and type check
cd frontend
npm run lint
npx tsc --noEmit
```

### Database Migrations

**CRITICAL**: After modifying SQLAlchemy models, always create and run migrations:

```bash
cd backend
alembic revision --autogenerate -m "descriptive message"
alembic upgrade head
```

Never commit model changes without corresponding migration files.