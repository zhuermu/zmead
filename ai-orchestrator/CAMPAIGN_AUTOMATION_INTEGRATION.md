# Campaign Automation Integration

This document describes the integration of the Campaign Automation module into the AI Orchestrator.

## Overview

The Campaign Automation module has been successfully integrated into the AI Orchestrator as a real implementation, replacing the previous stub. The module provides comprehensive campaign management capabilities including:

- Automated campaign structure generation (Campaign/Adset/Ad)
- Multi-platform support (Meta, TikTok, Google Ads)
- Budget optimization based on performance
- A/B testing with statistical analysis
- Rule-based automation
- AI-powered ad copy generation

## Architecture

### Components

1. **campaign_automation_node.py** - LangGraph node that handles campaign automation requests
2. **CampaignAutomation capability** - Core business logic module
3. **Platform adapters** - Multi-platform API integration
4. **Budget optimizer** - Performance-based budget optimization
5. **A/B test manager** - Statistical testing framework
6. **Rule engine** - Automated rule execution

### Integration Points

#### 1. Graph Integration (`app/core/graph.py`)

The campaign automation node is registered in the LangGraph workflow:

```python
# Campaign Automation module - use real implementation by default
use_campaign_automation_stub = os.environ.get("USE_CAMPAIGN_AUTOMATION_STUB", "false").lower() == "true"
if use_campaign_automation_stub:
    workflow.add_node("ad_engine", ad_engine_stub_node)
else:
    workflow.add_node("ad_engine", campaign_automation_node)
```

#### 2. Routing Integration (`app/core/routing.py`)

The router maps campaign automation intents to the correct node:

```python
MODULE_NODE_MAP = {
    "creative": NODE_CREATIVE,
    "reporting": NODE_REPORTING,
    "ad_engine": NODE_AD_ENGINE,  # Real implementation
    "market_intel": NODE_MARKET_INTEL,
    "landing_page": NODE_LANDING_PAGE,
}
```

#### 3. Intent Recognition (`app/prompts/intent_recognition.py`)

The intent recognition system already supports campaign automation intents:

- `create_campaign` - Create new campaigns
- Action types: `create_campaign`, `update_budget`, `pause_campaign`, `optimize_budget`, etc.

## Supported Actions

The Campaign Automation module supports the following actions:

### 1. create_campaign
Creates a new advertising campaign with automated structure generation.

**Parameters:**
- `objective`: Campaign objective (sales, traffic, awareness)
- `daily_budget`: Daily budget in USD
- `target_roas`: Target return on ad spend (optional)
- `product_url`: Product URL for ad copy generation
- `creative_ids`: List of creative IDs to use
- `target_countries`: Target countries
- `platform`: Ad platform (meta, tiktok, google)

### 2. optimize_budget
Optimizes campaign budgets based on performance data.

**Parameters:**
- `campaign_id`: Campaign to optimize
- `optimization_strategy`: Optimization strategy (auto)
- `target_metric`: Target metric (roas, cpa)

### 3. manage_campaign
Manages campaign status (pause, start, delete).

**Parameters:**
- `campaign_id`: Campaign to manage
- `action`: Action to perform (pause, start, delete)
- `reason`: Reason for the action (optional)

### 4. create_ab_test
Creates an A/B test for creative comparison.

**Parameters:**
- `test_name`: Name of the test
- `creative_ids`: List of creative IDs to test
- `daily_budget`: Daily budget for the test
- `test_duration_days`: Duration in days
- `platform`: Ad platform

### 5. analyze_ab_test
Analyzes A/B test results using statistical methods.

**Parameters:**
- `test_id`: Test to analyze

### 6. create_rule
Creates an automated rule for campaign management.

**Parameters:**
- `rule_name`: Name of the rule
- `condition`: Rule condition
- `action`: Action to execute
- `applies_to`: Campaigns to apply to
- `check_interval`: Check interval in seconds (default: 21600 = 6 hours)

### 7. get_campaign_status
Retrieves campaign status and performance metrics.

**Parameters:**
- `campaign_id`: Campaign to query

## Credit Management

The campaign automation node implements comprehensive credit management:

1. **Credit Check** - Verifies sufficient credits before execution
2. **Credit Deduction** - Deducts credits after successful execution
3. **Credit Refund** - Refunds credits on failure

### Credit Costs

| Action | Cost (Credits) |
|--------|----------------|
| create_campaign | 2.0 |
| optimize_budget | 1.5 |
| manage_campaign | 0.5 |
| create_ab_test | 2.0 |
| analyze_ab_test | 1.0 |
| create_rule | 0.5 |
| get_campaign_status | 0.5 |

## Error Handling

The integration includes comprehensive error handling:

1. **Insufficient Credits** - Returns error code 6011
2. **MCP Errors** - Handles communication failures with Web Platform
3. **Platform API Errors** - Handles ad platform API failures
4. **Validation Errors** - Validates parameters before execution

## Testing

Integration tests are provided in `tests/test_campaign_automation_integration.py`:

- `test_campaign_automation_node_integration` - Verifies graph integration
- `test_campaign_automation_routing` - Tests routing logic
- `test_campaign_automation_node_execution` - Tests successful execution
- `test_campaign_automation_node_insufficient_credits` - Tests credit handling
- `test_campaign_automation_action_types` - Tests all action types
- `test_campaign_automation_with_stub_fallback` - Tests stub fallback

Run tests:
```bash
cd ai-orchestrator
python -m pytest tests/test_campaign_automation_integration.py -v
```

## Environment Variables

### USE_CAMPAIGN_AUTOMATION_STUB

Set to `"true"` to use the stub implementation instead of the real implementation:

```bash
export USE_CAMPAIGN_AUTOMATION_STUB=true
```

This is useful for:
- Testing without real ad platform credentials
- Development environments
- CI/CD pipelines

## Usage Example

### User Request
```
"Create a campaign with $100 daily budget for my product"
```

### Flow

1. **Router Node** - Recognizes `create_campaign` intent
2. **Route to ad_engine** - Routes to campaign automation node
3. **Credit Check** - Verifies user has 2.0 credits
4. **Execute Action** - Calls CampaignAutomation.execute()
5. **Platform API** - Creates campaign via Meta/TikTok/Google API
6. **MCP Sync** - Syncs data to Web Platform
7. **Credit Deduct** - Deducts 2.0 credits
8. **Response** - Returns campaign details to user

### Response Format

```json
{
  "status": "success",
  "campaign_id": "camp_abc123",
  "adsets": [
    {
      "adset_id": "adset_1",
      "name": "US 18-35",
      "daily_budget": 33.33
    }
  ],
  "ads": [
    {
      "ad_id": "ad_1",
      "creative_id": "creative_1"
    }
  ],
  "message": "Campaign created successfully"
}
```

## Future Enhancements

Potential improvements for future iterations:

1. **Real-time Performance Monitoring** - Stream performance updates
2. **Advanced Optimization Algorithms** - ML-based budget optimization
3. **Cross-platform Campaign Sync** - Sync campaigns across platforms
4. **Automated Reporting** - Scheduled performance reports
5. **Budget Forecasting** - Predict future performance and costs

## Troubleshooting

### Issue: Campaign creation fails

**Solution:** Check that:
1. User has sufficient credits
2. Ad account is properly connected
3. Platform API credentials are valid
4. Creative IDs exist and are approved

### Issue: Budget optimization returns no recommendations

**Solution:** Verify that:
1. Campaign has sufficient performance data
2. Campaign has been running for at least 24 hours
3. Target metrics (ROAS/CPA) are properly configured

### Issue: A/B test analysis shows "insufficient data"

**Solution:** Ensure that:
1. Test has been running for the specified duration
2. Each variant has at least 100 conversions
3. Test is still active and collecting data

## References

- [Campaign Automation Requirements](../.kiro/specs/campaign-automation/requirements.md)
- [Campaign Automation Design](../.kiro/specs/campaign-automation/design.md)
- [Campaign Automation Tasks](../.kiro/specs/campaign-automation/tasks.md)
- [Campaign Automation Capability](./app/modules/campaign_automation/capability.py)
- [Campaign Automation Node](./app/nodes/campaign_automation_node.py)
