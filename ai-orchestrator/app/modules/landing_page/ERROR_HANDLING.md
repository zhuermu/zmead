# Error Handling and Retry Logic - Landing Page Module

This document describes the error handling and retry logic implementation for the Landing Page module.

## Overview

The Landing Page module implements comprehensive error handling with:
- **Unified error codes** mapped to specific failure scenarios
- **Automatic retry logic** with exponential backoff for transient failures
- **Circuit breaker pattern** to prevent cascading failures
- **Fallback behaviors** for non-critical operations

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Landing Page Capability                   │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │           Error Handler (LPErrorHandler)            │    │
│  │  - Maps exceptions to error codes                   │    │
│  │  - Determines retry eligibility                     │    │
│  │  - Provides fallback responses                      │    │
│  └────────────────────────────────────────────────────┘    │
│                          │                                   │
│                          ▼                                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │         Retry Strategy (RetryStrategy)              │    │
│  │  - Exponential backoff (2^attempt seconds)          │    │
│  │  - Max 3 retries                                    │    │
│  │  - Configurable per operation                       │    │
│  └────────────────────────────────────────────────────┘    │
│                          │                                   │
│                          ▼                                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │      Circuit Breaker (CircuitBreaker)               │    │
│  │  - Prevents cascading failures                      │    │
│  │  - Opens after 5 consecutive failures               │    │
│  │  - 60s recovery timeout                             │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Error Codes

| Error Code | Error Type | Description | Retryable |
|------------|------------|-------------|-----------|
| 6006 | PRODUCT_URL_INVALID | Invalid or malformed product URL | No |
| 6007 | PRODUCT_INFO_EXTRACTION_FAILED | Failed to extract product information | Yes |
| 6008 | LANDING_PAGE_DOMAIN_NOT_VERIFIED | Custom domain not verified | No |
| 4001 | AI_MODEL_FAILED | AI model generation/analysis failed | Yes |
| 4003 | GENERATION_FAILED | Landing page generation failed | Yes |
| 5003 | STORAGE_ERROR | File upload/storage failed | Yes |
| 5000 | DATA_NOT_FOUND | Resource not found | No |
| 3003 | MCP_EXECUTION_FAILED | MCP tool execution failed | Yes |

## Error Handling Strategies

### 1. Product Information Extraction

**Scenario**: Network failures, API rate limits, invalid responses

**Strategy**:
- Retry up to 3 times with exponential backoff (2s, 4s, 8s)
- After exhausting retries, return error with suggestion to check URL or enter manually

**Implementation**:
```python
from ..utils import with_retry

@with_retry(
    max_retries=3,
    base_delay=2.0,
    retryable_exceptions=(aiohttp.ClientError, TimeoutError)
)
async def _fetch_product_json(self, json_url: str) -> dict:
    # Fetch product data with automatic retry
    pass
```

**Error Response**:
```json
{
  "status": "error",
  "error_code": "6007",
  "message": "产品信息提取失败，请检查链接或手动输入产品信息",
  "suggestion": "请确保链接可访问，或尝试手动输入产品信息"
}
```

### 2. Landing Page Generation

**Scenario**: AI model failures, timeout, temporary service unavailability

**Strategy**:
- Retry up to 3 times with exponential backoff
- Allow user to retry manually after failure

**Implementation**:
```python
async def _generate_landing_page(self, parameters: dict, context: dict) -> dict:
    retry_count = 0
    
    while retry_count <= self.error_handler.MAX_RETRIES:
        try:
            # Generate landing page
            result = await self._do_generation(parameters)
            return {"status": "success", **result}
            
        except Exception as e:
            error_response = await self.error_handler.handle_generation_error(
                error=e,
                retry_count=retry_count,
                context={"action": "generate_landing_page"}
            )
            
            if error_response.get("retry"):
                retry_count += 1
                continue
            else:
                return error_response
```

**Error Response**:
```json
{
  "status": "error",
  "error_code": "4003",
  "message": "落地页生成失败，请稍后重试",
  "retry_allowed": true
}
```

### 3. Copy Optimization (Fallback Behavior)

**Scenario**: AI optimization fails but operation should not block user

**Strategy**:
- Return original text as fallback
- Mark response with `fallback: true` flag
- Log warning but don't fail the operation

**Implementation**:
```python
async def _optimize_copy(self, parameters: dict, context: dict) -> dict:
    try:
        # Attempt AI optimization
        optimized = await self.gemini_client.optimize_text(...)
        return {
            "status": "success",
            "optimized_text": optimized,
            "improvements": [...],
            "confidence_score": 0.92
        }
        
    except Exception as e:
        # Fallback to original text
        return await self.error_handler.handle_optimization_error(
            error=e,
            original_text=parameters["current_text"],
            section=parameters["section"]
        )
```

**Fallback Response**:
```json
{
  "status": "success",
  "optimized_text": "Original text unchanged",
  "improvements": [],
  "confidence_score": 0.0,
  "fallback": true,
  "message": "文案优化失败，返回原文案"
}
```

### 4. Translation

**Scenario**: Unsupported language, AI translation service unavailable

**Strategy**:
- Validate language before attempting translation
- Retry transient failures up to 3 times
- Return clear error for unsupported languages

**Implementation**:
```python
async def _translate_landing_page(self, parameters: dict, context: dict) -> dict:
    target_language = parameters.get("target_language")
    
    # Validate language first (non-retryable)
    if target_language not in SUPPORTED_LANGUAGES:
        return {
            "status": "error",
            "error_code": "4001",
            "message": f"不支持的语言: {target_language}",
            "supported_languages": SUPPORTED_LANGUAGES
        }
    
    # Attempt translation with retry
    retry_count = 0
    while retry_count <= self.error_handler.MAX_RETRIES:
        try:
            result = await self._do_translation(parameters)
            return {"status": "success", **result}
            
        except Exception as e:
            error_response = await self.error_handler.handle_translation_error(
                error=e,
                retry_count=retry_count,
                target_language=target_language
            )
            
            if error_response.get("retry"):
                retry_count += 1
                continue
            else:
                return error_response
```

### 5. Storage Operations (S3 Upload)

**Scenario**: Network issues, S3 service unavailability, timeout

**Strategy**:
- Retry up to 3 times with exponential backoff
- Use circuit breaker for repeated failures

**Implementation**:
```python
from ..utils import with_retry, with_circuit_breaker

@with_circuit_breaker(failure_threshold=5, recovery_timeout=60.0)
@with_retry(max_retries=3, base_delay=2.0)
async def _upload_to_s3(self, key: str, content: bytes) -> str:
    # Upload with automatic retry and circuit breaker
    pass
```

### 6. MCP Tool Calls

**Scenario**: Web Platform unavailable, network issues, tool execution timeout

**Strategy**:
- Retry up to 3 times
- Use circuit breaker to prevent overwhelming Web Platform

**Implementation**:
```python
@with_retry(max_retries=3, base_delay=2.0)
async def _call_mcp_tool(self, tool_name: str, parameters: dict) -> dict:
    try:
        return await self.mcp_client.call_tool(tool_name, parameters)
    except MCPError as e:
        logger.error(f"MCP tool {tool_name} failed: {e}")
        raise
```

## Retry Configuration

### Default Configuration

```python
MAX_RETRIES = 3
BASE_DELAY = 2.0  # seconds
MAX_DELAY = 60.0  # seconds
EXPONENTIAL_BASE = 2.0
```

### Delay Calculation

Exponential backoff formula:
```
delay = min(BASE_DELAY * (EXPONENTIAL_BASE ^ attempt), MAX_DELAY)
```

Example delays:
- Attempt 1: 2s
- Attempt 2: 4s
- Attempt 3: 8s

### Retryable vs Non-Retryable Errors

**Retryable Errors**:
- Network errors (ConnectionError, TimeoutError)
- HTTP 5xx errors (503, 502, 504)
- Rate limit errors (429)
- Temporary service unavailability

**Non-Retryable Errors**:
- Validation errors (invalid input format)
- Authentication errors (401, 403)
- Resource not found (404)
- Business logic errors

## Circuit Breaker Pattern

### Configuration

```python
FAILURE_THRESHOLD = 5  # Open circuit after 5 consecutive failures
RECOVERY_TIMEOUT = 60.0  # Wait 60s before attempting recovery
```

### States

1. **CLOSED**: Normal operation, requests pass through
2. **OPEN**: Too many failures, requests fail immediately
3. **HALF_OPEN**: Testing if service recovered

### State Transitions

```
CLOSED --[5 failures]--> OPEN --[60s timeout]--> HALF_OPEN
                                                      │
                                    ┌─────────────────┴─────────────────┐
                                    │                                   │
                              [success]                            [failure]
                                    │                                   │
                                    ▼                                   ▼
                                 CLOSED                               OPEN
```

## Usage Examples

### Example 1: Using Retry Decorator

```python
from ..utils import with_retry

@with_retry(max_retries=3, base_delay=2.0)
async def fetch_external_data(url: str) -> dict:
    """Fetch data with automatic retry on network errors"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

### Example 2: Manual Retry Logic

```python
async def process_with_retry(self, data: dict) -> dict:
    """Process data with manual retry control"""
    retry_count = 0
    
    while retry_count <= self.error_handler.MAX_RETRIES:
        try:
            result = await self._process(data)
            return {"status": "success", "result": result}
            
        except Exception as e:
            error_response = await self.error_handler.handle_generation_error(
                error=e,
                retry_count=retry_count,
                context={"operation": "process"}
            )
            
            if error_response.get("retry"):
                retry_count += 1
                continue
            else:
                return error_response
```

### Example 3: Fallback Behavior

```python
async def optimize_with_fallback(self, text: str) -> dict:
    """Optimize text with fallback to original"""
    try:
        optimized = await self.ai_client.optimize(text)
        return {
            "status": "success",
            "optimized_text": optimized,
            "fallback": False
        }
    except Exception as e:
        logger.warning(f"Optimization failed, using fallback: {e}")
        return {
            "status": "success",
            "optimized_text": text,
            "fallback": True
        }
```

### Example 4: Circuit Breaker

```python
from ..utils import with_circuit_breaker

@with_circuit_breaker(failure_threshold=5, recovery_timeout=60.0)
async def call_external_service(self, request: dict) -> dict:
    """Call external service with circuit breaker protection"""
    # Service call implementation
    pass
```

## Testing

### Unit Tests

Test error handling logic:

```python
import pytest
from ..utils import ErrorHandler, ErrorCode

@pytest.mark.asyncio
async def test_extraction_error_retry():
    """Test extraction error triggers retry"""
    handler = ErrorHandler()
    
    # First attempt should retry
    result = await handler.handle_extraction_error(
        error=ConnectionError("Network error"),
        retry_count=0,
        product_url="https://example.com/product"
    )
    assert result["retry"] is True
    
    # After max retries, should return error
    result = await handler.handle_extraction_error(
        error=ConnectionError("Network error"),
        retry_count=3,
        product_url="https://example.com/product"
    )
    assert result["status"] == "error"
    assert result["error_code"] == ErrorCode.PRODUCT_INFO_EXTRACTION_FAILED
```

### Integration Tests

Test retry behavior with real operations:

```python
@pytest.mark.asyncio
async def test_product_extraction_with_retry(mock_network_failure):
    """Test product extraction retries on network failure"""
    extractor = ShopifyExtractor()
    
    # Mock network to fail twice then succeed
    mock_network_failure.side_effect = [
        aiohttp.ClientError("Connection failed"),
        aiohttp.ClientError("Connection failed"),
        {"product": {"title": "Test Product"}}
    ]
    
    # Should succeed after retries
    result = await extractor.extract("https://shop.com/products/test")
    assert result.title == "Test Product"
```

## Monitoring and Logging

### Log Levels

- **INFO**: Successful operations, retry attempts
- **WARNING**: Fallback behaviors, non-critical errors
- **ERROR**: Failed operations after retries, unexpected errors

### Log Format

```python
logger.error(
    "operation_failed",
    error=str(e),
    error_type=type(e).__name__,
    retry_count=retry_count,
    context={"user_id": user_id, "action": action}
)
```

### Metrics to Track

- Error rate by error code
- Retry success rate
- Circuit breaker state changes
- Fallback usage frequency
- Average retry attempts per operation

## Best Practices

1. **Always use retry for network operations**: External API calls, S3 uploads, MCP calls
2. **Implement fallbacks for non-critical features**: Copy optimization, image generation
3. **Validate input before retrying**: Don't retry validation errors
4. **Use circuit breakers for external services**: Prevent cascading failures
5. **Log all errors with context**: Include user_id, action, parameters
6. **Return user-friendly error messages**: Provide actionable suggestions
7. **Test error scenarios**: Unit test error handlers, integration test retry logic

## Requirements Validation

This implementation satisfies the following requirements:

- **Requirement 1.5**: Error handling for product extraction failures
- **Requirement 4.5**: Fallback behavior for copy optimization failures
- **Task 16.1**: Unified error handler with error code mapping
- **Task 16.2**: Retry strategy with exponential backoff
- **Task 16.3**: Fallback behaviors for optimization and extraction

---

**Document Version**: v1.0
**Last Updated**: 2024-11-30
**Maintainer**: AAE Development Team
