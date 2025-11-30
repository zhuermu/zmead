# Platform Adapters

This module provides a unified interface for interacting with different advertising platforms (Meta, TikTok, Google Ads).

## Architecture

The platform adapter infrastructure follows the **Adapter Pattern** to provide a consistent interface across different advertising platforms while handling platform-specific implementation details.

### Components

1. **PlatformAdapter (base.py)** - Abstract base class defining the interface
2. **MetaAdapter (meta_adapter.py)** - Meta (Facebook/Instagram) implementation
3. **TikTokAdapter (tiktok_adapter.py)** - TikTok Ads implementation
4. **GoogleAdapter (google_adapter.py)** - Google Ads implementation
5. **PlatformRouter (router.py)** - Routes requests to appropriate adapter

## Usage

### Basic Usage

```python
from app.modules.campaign_automation.adapters import PlatformRouter

# Initialize router
router = PlatformRouter()

# Create a campaign
result = await router.create_campaign(
    platform="meta",
    params={
        "name": "Summer Sale Campaign",
        "objective": "sales",
        "daily_budget": 100.0,
        "ad_account_id": "123456789"
    }
)
```

### Direct Adapter Usage

```python
from app.modules.campaign_automation.adapters import MetaAdapter

# Initialize adapter
adapter = MetaAdapter()

# Create campaign
campaign = await adapter.create_campaign({
    "name": "Test Campaign",
    "objective": "sales",
    "daily_budget": 100.0,
    "ad_account_id": "123456789"
})
```

## Supported Operations

All adapters implement the following operations:

- `create_campaign(params)` - Create a new campaign
- `create_adset(params)` - Create an ad set/group
- `create_ad(params)` - Create an ad
- `update_budget(adset_id, budget)` - Update ad set budget
- `pause_adset(adset_id)` - Pause an ad set
- `resume_adset(adset_id)` - Resume a paused ad set
- `get_campaign_status(campaign_id)` - Get campaign status and metrics
- `delete_campaign(campaign_id)` - Delete a campaign

## Platform-Specific Details

### Meta (Facebook/Instagram)

- **API Version**: v18.0
- **SDK**: facebook-business (optional, falls back to mock if not installed)
- **Account ID Format**: `act_{account_id}`
- **Budget Format**: Cents (multiply by 100)

**Objectives Mapping**:
- `sales` → `OUTCOME_SALES`
- `traffic` → `OUTCOME_TRAFFIC`
- `awareness` → `OUTCOME_AWARENESS`

### TikTok

- **API Version**: v1.3
- **Account ID**: `advertiser_id`
- **Implementation**: Currently mock (SDK integration pending)

**Objectives Mapping**:
- `sales` → `CONVERSIONS`
- `traffic` → `TRAFFIC`
- `awareness` → `REACH`

### Google Ads

- **API Version**: v14
- **Account ID**: `customer_id`
- **Implementation**: Currently mock (SDK integration pending)

**Objectives Mapping**:
- `sales` → `SALES`
- `traffic` → `WEBSITE_TRAFFIC`
- `awareness` → `BRAND_AWARENESS_AND_REACH`

## Error Handling

All adapters return standardized error responses:

```python
{
    "status": "error",
    "error": {
        "code": "1001",
        "type": "INVALID_REQUEST",
        "message": "Missing required parameter: ad_account_id",
        "details": {},
        "timestamp": "2024-11-29T12:00:00Z"
    }
}
```

### Error Codes

- `1001` - Invalid request (missing parameters)
- `4000` - Platform API error
- `5001` - Dependency error (SDK not installed)

## Testing

Run the adapter tests:

```bash
pytest tests/campaign_automation/test_platform_adapters.py -v
```

The test suite includes:
- Router initialization and routing logic
- Adapter interface consistency
- Error handling for missing parameters
- Platform-specific behavior

## Adding a New Platform

To add support for a new platform:

1. Create a new adapter class inheriting from `PlatformAdapter`
2. Implement all abstract methods
3. Add the adapter to `PlatformRouter.__init__()`
4. Add tests in `test_platform_adapters.py`

Example:

```python
from .base import PlatformAdapter

class NewPlatformAdapter(PlatformAdapter):
    def __init__(self):
        self.api_version = "v1.0"
        self.base_url = "https://api.newplatform.com"
    
    async def create_campaign(self, params):
        # Implementation
        pass
    
    # Implement other methods...
```

## Future Enhancements

- [ ] Complete TikTok SDK integration
- [ ] Complete Google Ads SDK integration
- [ ] Add retry logic with exponential backoff
- [ ] Add rate limiting
- [ ] Add request/response caching
- [ ] Add metrics collection (Prometheus)
- [ ] Add circuit breaker pattern for API failures

## Requirements Validation

This implementation satisfies the following requirements from the design document:

- **Requirement 7.1**: Meta platform support ✅
- **Requirement 7.2**: TikTok platform support ✅ (mock)
- **Requirement 7.3**: Google platform support ✅ (mock)
- **Requirement 7.4**: Cross-platform operation consistency ✅
- **Requirement 7.5**: Platform-specific error handling ✅

## References

- [Meta Marketing API Documentation](https://developers.facebook.com/docs/marketing-apis)
- [TikTok Ads API Documentation](https://ads.tiktok.com/marketing_api/docs)
- [Google Ads API Documentation](https://developers.google.com/google-ads/api/docs/start)
