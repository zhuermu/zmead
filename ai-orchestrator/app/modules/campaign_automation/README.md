# Campaign Automation Module

## Overview

Campaign Automation is a functional module within the AI Orchestrator that provides automated campaign creation, management, and optimization capabilities for advertising platforms (Meta, TikTok, Google Ads).

## Features

- **Automated Campaign Structure Generation**: Automatically creates Campaign/Adset/Ad hierarchy
- **Multi-Platform Support**: Unified interface for Meta, TikTok, and Google Ads
- **Budget Optimization**: AI-powered budget allocation based on performance
- **A/B Testing**: Statistical analysis with chi-square testing
- **Rule-Based Automation**: Automated actions based on performance thresholds
- **AI Copy Generation**: Gemini-powered ad copy generation with fallback

## Architecture

```
campaign_automation/
├── capability.py          # Main entry point (Module API)
├── models.py             # Pydantic data models
├── adapters/             # Platform-specific adapters
│   ├── base.py          # Abstract base adapter
│   ├── meta_adapter.py  # Meta Marketing API
│   ├── tiktok_adapter.py # TikTok Ads API
│   └── google_adapter.py # Google Ads API
├── managers/             # Campaign management
│   └── campaign_manager.py
├── optimizers/           # Optimization components
│   ├── budget_optimizer.py
│   ├── ab_test_manager.py
│   └── rule_engine.py
└── utils/               # Shared utilities
    ├── cache_manager.py
    ├── retry_strategy.py
    └── error_handler.py
```

## Module API

The module exposes a single `execute()` method that routes to different handlers:

```python
async def execute(action: str, parameters: dict, context: dict) -> dict
```

### Supported Actions

1. **create_campaign**: Create a new advertising campaign
2. **optimize_budget**: Optimize budget allocation across adsets
3. **manage_campaign**: Pause/start/delete campaigns
4. **create_ab_test**: Create A/B test for creative optimization
5. **analyze_ab_test**: Analyze A/B test results with statistical testing
6. **create_rule**: Create automation rule
7. **get_campaign_status**: Get real-time campaign status

## Usage Example

```python
from app.modules.campaign_automation import CampaignAutomation

# Initialize module
campaign_automation = CampaignAutomation(
    mcp_client=mcp_client,
    gemini_client=gemini_client,
    redis_client=redis_client,
)

# Create campaign
result = await campaign_automation.execute(
    action="create_campaign",
    parameters={
        "objective": "sales",
        "daily_budget": 100,
        "creative_ids": ["creative_1", "creative_2"],
        "target_countries": ["US", "CA"],
        "platform": "meta",
    },
    context={
        "user_id": "user_123",
        "session_id": "session_456",
    },
)
```

## Dependencies

- **MCP Client**: Communication with Web Platform for data persistence
- **Gemini Client**: AI-powered copy generation and analysis
- **Redis**: Caching for performance optimization
- **Platform SDKs**: facebook-business, tiktok-business-api, google-ads

## Testing

The module uses property-based testing with Hypothesis to verify correctness properties:

```bash
# Run all tests
pytest tests/campaign_automation/

# Run specific property test
pytest tests/campaign_automation/test_campaign_creation_property.py
```

## Requirements

See `.kiro/specs/campaign-automation/requirements.md` for detailed requirements.

## Design

See `.kiro/specs/campaign-automation/design.md` for detailed design documentation.

## Implementation Status

- [x] Task 1: Project structure and core interfaces
- [ ] Task 2: Platform adapters
- [ ] Task 3: Campaign Manager
- [ ] Task 4: AI copy generation
- [ ] Task 5: MCP client integration
- [ ] Task 6: Budget Optimizer
- [ ] Task 7: A/B Test Manager
- [ ] Task 8: Rule Engine
- [ ] Task 9: Error handling and retry
- [ ] Task 10: Cache mechanism
- [ ] Task 11: Module API integration
- [ ] Task 12: AI Orchestrator integration

## Error Handling

The module uses structured error responses following the AAE error format:

```python
{
    "status": "error",
    "error": {
        "code": "1001",
        "type": "INVALID_REQUEST",
        "message": "Error description",
        "details": {...}
    }
}
```

## Performance

- Campaign creation: < 10 seconds
- Budget optimization: < 5 seconds
- Status query: < 3 seconds (with caching)
- Concurrent operations: Up to 10

## Monitoring

Key metrics exposed via Prometheus:
- `campaign_automation_requests_total`: Request counter by action and status
- `campaign_automation_request_duration_seconds`: Request duration histogram
- `platform_api_calls_total`: Platform API call counter
- `campaign_automation_active_rules`: Active automation rules gauge
