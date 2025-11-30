# Campaign Automation Error Handling and Retry Mechanism

## Overview

This document describes the error handling and retry mechanism implemented for the Campaign Automation module.

## Components

### 1. RetryStrategy (`retry_strategy.py`)

Provides exponential backoff retry logic for operations that may fail temporarily.

**Key Features:**
- **Exponential Backoff**: 1s, 2s, 4s delays between retries
- **Timeout**: 30 seconds for all operations
- **Max Retries**: 3 attempts maximum
- **Retryable Errors**: Automatically identifies which errors should trigger retry

**Usage Example:**
```python
from app.modules.campaign_automation.utils.retry_strategy import RetryStrategy

# Retry an async operation
result = await RetryStrategy.retry_with_backoff(
    func=some_async_function,
    max_retries=3,
    timeout=30,
    context="create_campaign"
)
```

**Retryable Error Types:**
- CONNECTION_FAILED
- TIMEOUT
- API_RATE_LIMIT
- SERVICE_UNAVAILABLE
- AI_MODEL_FAILED
- PLATFORM_SERVICE_ERROR
- PLATFORM_TIMEOUT
- MCP_CONNECTION_ERROR
- MCP_TIMEOUT

### 2. Error Handler (`error_handler.py`)

Provides centralized error handling with standardized error responses.

**Key Features:**
- **Platform-Specific Errors**: Handles Meta, TikTok, Google Ads API errors
- **MCP Errors**: Handles MCP client connection and tool errors
- **AI Model Errors**: Handles Gemini API errors
- **Standardized Responses**: All errors return consistent format

**Error Types:**

#### Ad Platform Errors
- `TokenExpiredError`: Token has expired (code: 6001)
- `TokenInvalidError`: Invalid token (code: 6001)
- `PermissionDeniedError`: Access denied (code: 6001)
- `RateLimitError`: Rate limit exceeded (code: 1003)
- `PlatformServiceError`: Platform 5xx error (code: 4002)
- `PlatformTimeoutError`: Request timeout (code: 4002)
- `BudgetInsufficientError`: Insufficient budget (code: 6002)
- `CreativeRejectedError`: Creative rejected (code: 6003)

**Usage Example:**
```python
from app.modules.campaign_automation.utils.error_handler import (
    CampaignAutomationErrorHandler,
    TokenExpiredError,
)

try:
    # Call ad platform API
    result = await platform_api.create_campaign(...)
except Exception as e:
    # Handle error and return standardized response
    error_response = CampaignAutomationErrorHandler.create_error_response(
        error=e,
        context="create_campaign",
        platform="meta",
        retry_count=0
    )
    return error_response
```

### 3. Error Response Format

All errors return a standardized format:

```python
{
    "status": "error",
    "error": {
        "code": "6001",
        "type": "TOKEN_EXPIRED",
        "message": "广告账户授权已过期，请重新授权",
        "context": "create_campaign",
        "platform": "meta",
        "timestamp": "2024-01-01T00:00:00.000000",
        "action": "重新授权",
        "action_url": "/settings/ad-accounts"
    },
    "retry_allowed": false,
    "retry_after": 60  # Optional, in seconds
}
```

## Integration with Campaign Automation

The error handling and retry mechanism is integrated throughout the Campaign Automation module:

1. **Platform Adapters**: Use retry strategy for API calls
2. **Campaign Manager**: Handle errors during campaign creation
3. **Budget Optimizer**: Retry failed optimization operations
4. **A/B Test Manager**: Handle errors during test analysis
5. **Rule Engine**: Retry failed rule executions

## Requirements Satisfied

This implementation satisfies the following requirements:

- **4.4**: API 调用失败时自动重试最多 3 次
- **9.1**: 广告平台 API 调用失败时自动重试最多 3 次
- **9.2**: 网络超时时设置 30 秒超时并重试
- **9.3**: 达到 API 限额时返回限额错误并建议稍后重试
- **9.4**: 达到重试上限时返回明确的错误信息
- **9.5**: 发生错误时记录详细的错误日志

## Logging

All errors are logged with structured logging using `structlog`:

```python
logger.error(
    "operation_error",
    context="create_campaign",
    error_type="TokenExpiredError",
    error_message="Token expired",
    platform="meta",
    retry_count=0
)
```

## Testing

The error handling and retry mechanism has been tested with:
- Unit tests for error response formatting
- Integration tests with existing Campaign Automation tests
- All 126 existing tests pass with the new error handling

## TimeoutConfig

Provides timeout configuration for different operation types:

```python
from app.modules.campaign_automation.utils.retry_strategy import TimeoutConfig

# Get timeout for specific operation
timeout = TimeoutConfig.get_timeout("api_call")  # Returns 30 seconds
```

**Available Timeouts:**
- `api_call`: 30 seconds (Ad platform API calls)
- `mcp_call`: 30 seconds (MCP tool calls)
- `ai_generation`: 30 seconds (AI text generation)
- `default`: 30 seconds (All other operations)
