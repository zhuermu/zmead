# Error Handling in Ad Performance Module

This document describes the error handling implementation for the Ad Performance module.

## Overview

The `AdPerformanceErrorHandler` class provides centralized error handling for:
- **Ad Platform API errors** (Meta, TikTok, Google)
- **MCP client errors** (connection, timeout, tool execution)
- **AI model errors** (Gemini timeouts, quota exceeded)
- **Data validation errors**

All errors are converted to standardized error responses following the format defined in `INTERFACES.md`.

## Error Response Format

All error responses follow this standard format:

```python
{
    "status": "error",
    "error_code": "6001",  # From INTERFACES.md error codes
    "message": "User-friendly error message",
    "retry_allowed": True,  # Whether retry is allowed
    "retry_after": 60,  # Optional: seconds to wait before retry
    "action": "重新授权",  # Optional: suggested action
    "action_url": "/settings/ad-accounts",  # Optional: action URL
    "platform": "meta",  # Optional: platform name for API errors
    "details": {}  # Optional: additional error details
}
```

## Error Types

### 1. Ad Platform API Errors

#### Token Expired/Invalid (401/403)
```python
from app.modules.ad_performance.utils import TokenExpiredError

try:
    # Call ad platform API
    result = await meta_api.get_insights()
except Exception as e:
    # Convert to TokenExpiredError
    error = TokenExpiredError(platform="meta")
    response = AdPerformanceErrorHandler.handle_api_error(
        error=error,
        platform="meta",
        retry_count=0,
    )
    # Returns: error_code="6001", retry_allowed=False
```

#### Rate Limit Exceeded (429)
```python
from app.modules.ad_performance.utils import RateLimitError

error = RateLimitError(platform="tiktok", retry_after=120)
response = AdPerformanceErrorHandler.handle_api_error(
    error=error,
    platform="tiktok",
    retry_count=0,
)
# Returns: error_code="1003", retry_allowed=True, retry_after=120
```

#### Platform Service Error (500)
```python
from app.modules.ad_performance.utils import PlatformServiceError

error = PlatformServiceError(platform="google", status_code=503)
response = AdPerformanceErrorHandler.handle_api_error(
    error=error,
    platform="google",
    retry_count=0,
)
# Returns: error_code="4002", retry_allowed=True (if retry_count < 3)
```

#### Timeout Error
```python
from app.modules.ad_performance.utils import PlatformTimeoutError

error = PlatformTimeoutError(platform="meta")
response = AdPerformanceErrorHandler.handle_api_error(
    error=error,
    platform="meta",
    retry_count=1,
)
# Returns: error_code="4002", retry_allowed=True, retry_after=2 (exponential backoff)
```

### 2. MCP Client Errors

#### Connection Error
```python
from app.services.mcp_client import MCPConnectionError

try:
    result = await mcp_client.call_tool("save_metrics", params)
except MCPConnectionError as e:
    response = AdPerformanceErrorHandler.handle_mcp_error(e)
    # Returns: error_code="3000", retry_allowed=True
```

#### Timeout Error
```python
from app.services.mcp_client import MCPTimeoutError

try:
    result = await mcp_client.call_tool("get_metrics", params)
except MCPTimeoutError as e:
    response = AdPerformanceErrorHandler.handle_mcp_error(e)
    # Returns: error_code="3004", retry_allowed=True
```

#### Tool Execution Error
```python
from app.services.mcp_client import MCPToolError

try:
    result = await mcp_client.call_tool("save_metrics", params)
except MCPToolError as e:
    response = AdPerformanceErrorHandler.handle_mcp_error(e)
    # Returns: error_code="3003", retry_allowed=True
```

#### Insufficient Credits
```python
from app.services.mcp_client import InsufficientCreditsError

try:
    result = await mcp_client.call_tool("generate_report", params)
except InsufficientCreditsError as e:
    response = AdPerformanceErrorHandler.handle_mcp_error(e)
    # Returns: error_code="6011", retry_allowed=False, action="前往充值"
```

### 3. AI Model Errors

#### Timeout Error
```python
from app.core.errors import AIModelTimeoutError

try:
    result = await gemini_client.generate_content(prompt)
except AIModelTimeoutError as e:
    response = AdPerformanceErrorHandler.handle_ai_model_error(e)
    # Returns: error_code="4002", retry_allowed=True
```

#### Quota Exceeded
```python
from app.core.errors import AIModelQuotaError

try:
    result = await gemini_client.generate_content(prompt)
except AIModelQuotaError as e:
    response = AdPerformanceErrorHandler.handle_ai_model_error(e)
    # Returns: error_code="4003", retry_allowed=True, retry_after=60
```

### 4. Validation Errors

```python
try:
    # Validate date format
    date = datetime.fromisoformat(date_str)
except ValueError as e:
    response = AdPerformanceErrorHandler.handle_validation_error(
        error=e,
        field="date",
    )
    # Returns: error_code="1001", retry_allowed=False
```

## Usage in Capability Module

### Method 1: Using create_error_response (Recommended)

This is the main entry point that automatically routes to the appropriate handler:

```python
async def _fetch_ad_data(self, parameters: dict, context: dict) -> dict:
    """Fetch ad data with error handling."""
    try:
        # Fetch data from platform
        result = await self.meta_fetcher.fetch_insights(...)
        return {
            "status": "success",
            "data": result,
        }
    except Exception as e:
        # Unified error handling
        error_response = AdPerformanceErrorHandler.create_error_response(
            error=e,
            context="fetch_ad_data",
            platform="meta",
            retry_count=0,
        )
        return error_response
```

### Method 2: Using Specific Handlers

For more control, use specific handlers:

```python
async def _save_metrics(self, metrics: dict) -> dict:
    """Save metrics with MCP error handling."""
    try:
        result = await self.mcp_client.call_tool("save_metrics", metrics)
        return {"status": "success", "data": result}
    except (MCPConnectionError, MCPTimeoutError, MCPToolError) as e:
        error_response = AdPerformanceErrorHandler.handle_mcp_error(e)
        return error_response
```

### Method 3: Using Retry with Backoff

For operations that should be retried automatically:

```python
async def _fetch_with_retry(self, platform: str) -> dict:
    """Fetch data with automatic retry."""
    
    async def fetch():
        return await self.platform_fetcher.fetch_insights(...)
    
    try:
        result = await AdPerformanceErrorHandler.retry_with_backoff(
            func=fetch,
            max_retries=3,
            backoff_factor=2,
        )
        return {"status": "success", "data": result}
    except Exception as e:
        error_response = AdPerformanceErrorHandler.create_error_response(
            error=e,
            context="fetch_with_retry",
            platform=platform,
            retry_count=3,  # Max retries exhausted
        )
        return error_response
```

## Error Code Reference

| Code | Description | Retry | Action |
|------|-------------|-------|--------|
| 1000 | Unknown error | No | Contact support |
| 1001 | Invalid parameters | No | - |
| 1003 | Rate limit exceeded | Yes | Wait and retry |
| 3000 | MCP connection failed | Yes | Retry |
| 3003 | MCP tool execution failed | Yes | Retry |
| 3004 | MCP timeout | Yes | Retry |
| 4001 | AI model error | Yes | Retry |
| 4002 | AI/API timeout | Yes | Retry |
| 4003 | AI quota exceeded | Yes | Wait and retry |
| 6001 | Token expired/invalid | No | Re-authorize |
| 6011 | Insufficient credits | No | Recharge |

## Best Practices

1. **Always use standardized error responses**: Return error dicts with the standard format
2. **Log errors appropriately**: The error handler logs automatically, but add context-specific logs
3. **Preserve error details**: Include relevant details in the error response
4. **Handle retries intelligently**: Use exponential backoff for transient errors
5. **Don't retry non-retryable errors**: Check `retry_allowed` before retrying
6. **Provide user-friendly messages**: Error messages should be clear and actionable
7. **Include suggested actions**: When possible, tell users what to do next

## Testing

The error handler is fully tested in `tests/ad_performance/test_error_handler.py`:

```bash
# Run error handler tests
pytest tests/ad_performance/test_error_handler.py -v

# Run with coverage
pytest tests/ad_performance/test_error_handler.py --cov=app.modules.ad_performance.utils.error_handler
```

## Integration with AI Orchestrator

The Ad Performance module's error responses are compatible with the AI Orchestrator's error handling:

```python
# In AI Orchestrator node
result = await ad_performance.execute(
    action="fetch_ad_data",
    parameters={...},
    context={...},
)

if result["status"] == "error":
    # Error response follows standard format
    error_code = result["error_code"]
    message = result["message"]
    retry_allowed = result["retry_allowed"]
    
    # Can be passed directly to state
    return {
        "error": result,
        "messages": [{"role": "assistant", "content": message}],
    }
```

## Requirements

This implementation satisfies:
- **Requirement 8.5**: Error handling for API errors (401, 403, 429, 500, timeout), MCP errors, and AI model errors
- **INTERFACES.md**: Standardized error response format with error codes
- **Design Document**: Error handling strategy with retry mechanism

## See Also

- `app/core/errors.py` - Core error handling utilities
- `INTERFACES.md` - Error code definitions
- `.kiro/specs/ad-performance/design.md` - Error handling design
