# Ad Performance Module

## Overview

The Ad Performance module provides comprehensive advertising performance analytics for the AI Orchestrator. It handles data fetching from multiple ad platforms, AI-powered analysis, anomaly detection, and optimization recommendations.

## Architecture

### Main Entry Point

The `AdPerformance` class in `capability.py` serves as the main entry point for all ad performance operations. It implements a unified `execute()` interface that routes actions to appropriate handlers.

### Dependencies

The module depends on:
- **MCPClient**: For communication with Web Platform (data persistence, user management)
- **GeminiClient**: For AI-powered analysis and insights
- **Redis**: For caching metrics data (5-minute TTL)

### Supported Actions

1. **fetch_ad_data**: Fetch advertising data from platforms (Meta, TikTok, Google)
2. **generate_daily_report**: Generate daily performance reports with AI insights
3. **analyze_performance**: Analyze specific entity performance with period comparison
4. **detect_anomalies**: Detect metric anomalies using statistical analysis
5. **generate_recommendations**: Generate optimization recommendations
6. **export_report**: Export reports in CSV or PDF format
7. **get_metrics_summary**: Get aggregated metrics summary

## Implementation Status

### ✅ Completed (Task 2)

- Main entry point (`AdPerformance` class)
- Action routing with comprehensive error handling
- Dependency initialization (MCP, Gemini, Redis clients)
- Structured logging with context binding
- Error handling with user-friendly messages
- Test fixtures and unit tests

### 🚧 Pending Implementation

- Task 3: Platform data fetchers (Meta, TikTok, Google)
- Task 4: MCP integration for data persistence
- Task 6: Performance analyzer with AI insights
- Task 7: Anomaly detection engine
- Task 8: Recommendation engine
- Task 9: Daily report generation
- Task 10: Multi-platform data aggregation
- Task 11: Report exporters (CSV, PDF)
- Task 12: Caching layer
- Task 13: Enhanced error handling

## Usage Example

```python
from app.modules.ad_performance import AdPerformance

# Initialize with dependencies
ad_performance = AdPerformance(
    mcp_client=mcp_client,
    gemini_client=gemini_client,
    redis_client=redis_client,
)

# Execute an action
result = await ad_performance.execute(
    action="fetch_ad_data",
    parameters={
        "platform": "meta",
        "date_range": {
            "start_date": "2024-11-20",
            "end_date": "2024-11-26",
        },
        "levels": ["campaign", "adset", "ad"],
        "metrics": ["spend", "impressions", "clicks", "conversions", "revenue"],
    },
    context={
        "user_id": "user_123",
        "session_id": "session_456",
    },
)

# Handle result
if result["status"] == "success":
    data = result["data"]
    # Process data...
else:
    error = result["error"]
    # Handle error...
```

## Error Handling

The module implements comprehensive error handling:

- **Service Errors**: MCPError, GeminiError are caught and converted to structured responses
- **Unknown Actions**: Returns error with list of supported actions
- **Unexpected Errors**: Caught and logged with full context
- **User-Friendly Messages**: All errors include actionable messages and retry information

Error response format:
```python
{
    "status": "error",
    "error": {
        "code": "1001",
        "type": "INVALID_ACTION",
        "message": "User-friendly error message",
        "details": {...},
        "retryable": True/False,
        "action": "Suggested action",
        "action_url": "/path/to/action"
    }
}
```

## Testing

### Unit Tests

Located in `tests/ad_performance/test_capability.py`:
- Action routing tests for all 7 actions
- Unknown action error handling
- Dependency initialization
- Mock fixtures for isolated testing

### Property-Based Tests

Located in `tests/ad_performance/test_data_models_property.py`:
- Property 1: Data fetch returns complete structure (100 iterations)

### Running Tests

```bash
# Run all ad_performance tests
pytest tests/ad_performance/ -v

# Run specific test file
pytest tests/ad_performance/test_capability.py -v

# Run with coverage
pytest tests/ad_performance/ --cov=app.modules.ad_performance
```

## Logging

The module uses structured logging with `structlog`:

```python
logger.info(
    "ad_performance_execute_start",
    action=action,
    user_id=user_id,
    session_id=session_id,
    parameters=parameters,
)
```

All operations are logged with:
- Action name
- User ID and session ID
- Parameters
- Execution status (start, success, error)
- Error details (if applicable)

## Requirements Coverage

This implementation satisfies the following requirements:

- **1.1**: Data fetching interface (stub)
- **2.1**: Daily report generation interface (stub)
- **3.1**: Performance analysis interface (stub)
- **4.1**: Anomaly detection interface (stub)
- **5.1**: Recommendation generation interface (stub)
- **6.1**: Report export interface (stub)
- **7.1**: Metrics summary interface (stub)

All action handlers are implemented as stubs that will be completed in subsequent tasks.

## Next Steps

1. Implement platform fetchers (Task 3)
2. Integrate MCP for data persistence (Task 4)
3. Implement performance analyzer (Task 6)
4. Implement anomaly detector (Task 7)
5. Implement recommendation engine (Task 8)
6. Wire up daily report generation (Task 9)
7. Implement data aggregation (Task 10)
8. Implement report exporters (Task 11)
