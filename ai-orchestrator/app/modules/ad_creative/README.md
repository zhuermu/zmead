# Ad Creative Module

AI-powered ad creative generation and management module for the AI Orchestrator.

## Overview

The Ad Creative module provides comprehensive functionality for:
- Product information extraction from Shopify and Amazon
- AI-powered creative generation using Gemini Imagen 3
- Multi-dimensional creative scoring and analysis
- Competitor creative analysis
- Creative library management with filtering and sorting
- Credit-based usage control with bulk discounts
- Platform-specific aspect ratio handling

## Architecture

```
ad_creative/
├── capability.py              # Main entry point (execute interface)
├── models.py                  # Pydantic data models
├── extractors/               # Product info extraction
│   ├── base.py               # Base extractor interface
│   ├── shopify_extractor.py  # Shopify API integration
│   └── amazon_extractor.py   # Amazon web scraping
├── generators/               # Creative generation
│   ├── image_generator.py    # Gemini Imagen 3 integration
│   └── variant_generator.py  # Variant generation
├── analyzers/                # Analysis and scoring
│   ├── scoring_engine.py     # Multi-dimensional scoring
│   └── competitor_analyzer.py # Competitor analysis
├── managers/                 # Resource management
│   ├── creative_manager.py   # Library CRUD operations
│   └── upload_manager.py     # S3 upload flow
└── utils/                    # Utilities
    ├── validators.py         # File validation
    ├── aspect_ratio.py       # Aspect ratio handling
    ├── credit_checker.py     # Credit management
    ├── cache_manager.py      # Redis caching
    └── retry.py              # Retry logic
```

## Usage

### Basic Usage

```python
from app.modules.ad_creative.capability import AdCreative

# Initialize
ad_creative = AdCreative(
    mcp_client=mcp_client,
    gemini_client=gemini_client,
    redis_client=redis_client,
)

# Generate creatives
result = await ad_creative.execute(
    action="generate_creative",
    parameters={
        "product_url": "https://example.myshopify.com/products/item",
        "count": 10,
        "style": "modern",
        "platform": "tiktok",
    },
    context={"user_id": "user_123"},
)

# Get creative library
result = await ad_creative.execute(
    action="get_creatives",
    parameters={
        "filters": {"platform": "tiktok", "score_min": 80},
        "sort_by": "score",
        "limit": 20,
    },
    context={"user_id": "user_123"},
)
```

### Supported Actions

| Action | Description | Parameters |
|--------|-------------|------------|
| `generate_creative` | Generate creatives from product URL | product_url, count, style, platform |
| `analyze_creative` | Analyze creative quality | creative_id or image_url |
| `score_creative` | Score creative (0-100) | creative_id |
| `generate_variants` | Generate variants | creative_id, count, variation_type |
| `analyze_competitor` | Analyze competitor ad | ad_url, save |
| `get_creatives` | List creatives | filters, sort_by, limit, offset |
| `delete_creative` | Delete creative | creative_id |
| `download_creative` | Get download URL | creative_id |
| `batch_download` | Batch download as ZIP | creative_ids |
| `upload_reference` | Upload reference image | file_data, file_name, file_type |

## Components

### Credit Management

```python
from app.modules.ad_creative.utils.credit_checker import CreditChecker

checker = CreditChecker(mcp_client=mcp_client)

# Check balance
result = await checker.check_and_reserve(
    user_id="user_123",
    operation="image_generation",
    count=10,
)

if result.allowed:
    # Deduct credits after successful operation
    await checker.deduct(
        user_id="user_123",
        operation_id="op_456",
        credits=result.required_credits,
    )
else:
    # Handle insufficient credits
    print(f"Need {result.required_credits}, have {result.available_credits}")
```

**Credit Rates:**
- Image generation: 0.5 credits/image
- Bulk generation (10+): 0.4 credits/image (20% discount)
- Creative analysis: 0.2 credits
- Competitor analysis: 1.0 credits

### Creative Library Management

```python
from app.modules.ad_creative.managers.creative_manager import CreativeManager

manager = CreativeManager(mcp_client=mcp_client)

# Get creatives with filters
response = await manager.filter_creatives(
    user_id="user_123",
    platform="tiktok",
    score_min=80.0,
    tags=["product", "ad"],
    limit=20,
)

# Check capacity warning
if response.capacity_warning:
    print("Library has over 100 creatives, consider cleanup")

# Delete creative
await manager.delete_creative(
    user_id="user_123",
    creative_id="creative_456",
)
```

### File Upload

```python
from app.modules.ad_creative.managers.upload_manager import UploadManager
from app.modules.ad_creative.models import GeneratedImage

manager = UploadManager(mcp_client=mcp_client)

# Upload single creative
result = await manager.upload_creative(
    user_id="user_123",
    image=generated_image,
    metadata={"style": "modern", "platform": "tiktok"},
)

print(f"Uploaded: {result.creative_id} at {result.url}")
```

### Caching

```python
from app.modules.ad_creative.utils.cache_manager import CacheManager

cache = CacheManager(redis_client=redis_client)

# Cache product info (1 hour TTL)
await cache.cache_product_info(product_url, product_info)

# Get cached product info
cached = await cache.get_product_info(product_url)

# Cache competitor analysis (24 hour TTL)
await cache.cache_competitor_analysis(ad_url, analysis)
```

### Aspect Ratio Handling

```python
from app.modules.ad_creative.utils.aspect_ratio import AspectRatioHandler

handler = AspectRatioHandler()

# Get ratio for platform
ratio = handler.get_ratio_for_platform("tiktok")  # "9:16"

# Get dimensions
width, height = handler.get_dimensions("9:16")  # (1080, 1920)

# Parse custom ratio
width, height = handler.parse_custom_ratio("16:9")  # (1920, 1080)

# Resolve with priority: custom > platform > default
ratio, (w, h) = handler.resolve_aspect_ratio(
    platform="tiktok",
    custom_ratio="1:1",  # Takes priority
)
```

## Configuration

### Environment Variables

```bash
# Gemini API
GEMINI_API_KEY=your_api_key
GEMINI_MODEL_IMAGEN=imagen-3.0-generate-001
GEMINI_MODEL_FLASH=gemini-2.5-flash

# Web Platform MCP
WEB_PLATFORM_URL=http://localhost:8000
WEB_PLATFORM_SERVICE_TOKEN=your_service_token

# Redis (optional, for caching)
REDIS_URL=redis://localhost:6379/0
```

### MCP Tools Required

The module requires these MCP tools from Web Platform:

- `get_upload_url` - Get S3 presigned upload URL
- `create_creative` - Store creative metadata
- `get_creative` - Get single creative
- `get_creatives` - List creatives with filters
- `update_creative` - Update creative metadata
- `delete_creative` - Delete creative
- `get_download_url` - Get download URL
- `batch_download_creatives` - Batch download as ZIP
- `check_credit` - Check credit balance
- `deduct_credit` - Deduct credits
- `refund_credit` - Refund credits
- `get_credit_balance` - Get balance details

## Testing

### Run Tests

```bash
# Run all ad_creative tests
pytest tests/ad_creative/ -v

# Run integration tests only
pytest tests/ad_creative/test_integration.py -v

# Run with coverage
pytest tests/ad_creative/ --cov=app.modules.ad_creative
```

### Test Coverage

- Integration tests: 22 tests covering all major components
- Property-based tests: Optional (marked with `*` in tasks.md)
- Unit tests: Embedded in integration tests

## Error Handling

### Error Codes

| Code | Type | Description | Retryable |
|------|------|-------------|-----------|
| 4001 | AI_MODEL_FAILED | Gemini API failure | Yes |
| 4003 | GENERATION_FAILED | Image generation failed | Yes |
| 5003 | STORAGE_ERROR | S3 upload failed | Yes |
| 6006 | PRODUCT_URL_INVALID | Invalid product URL | No |
| 6007 | PRODUCT_INFO_EXTRACTION_FAILED | Extraction failed | Yes |
| 6011 | INSUFFICIENT_CREDITS | Not enough credits | No |
| 6012 | CREDIT_DEDUCTION_FAILED | Deduction failed | Yes |

### Retry Logic

All operations implement exponential backoff retry:
- Max retries: 3
- Base delay: 1 second
- Backoff factor: 2x (1s, 2s, 4s)
- Jitter: Enabled to prevent thundering herd

## Performance

### Caching Strategy

- **Product info**: 1 hour TTL (reduces API calls to e-commerce platforms)
- **Competitor analysis**: 24 hours TTL (expensive AI analysis)
- **Creative scores**: 24 hours TTL (stable after generation)

### Concurrency Limits

- Image generation: 5 concurrent requests
- Variant generation: 3 concurrent requests
- Upload operations: Sequential (to avoid S3 throttling)

### Bulk Discounts

- 10+ images: 20% discount (0.4 credits/image vs 0.5)
- Automatically applied in `CreditChecker.calculate_cost()`

## Dependencies

- `app.services.mcp_client` - MCP communication
- `app.services.gemini_client` - Gemini AI integration
- `redis.asyncio` - Caching (optional)
- `httpx` - HTTP client for S3 uploads
- `structlog` - Structured logging
- `pydantic` - Data validation

## Development

### Adding New Extractors

1. Create new extractor in `extractors/`
2. Inherit from `BaseExtractor`
3. Implement `extract()` and `supports()` methods
4. Register in capability.py

### Adding New Variation Types

1. Add to `VariantGenerator.VARIATION_TYPES`
2. Define variation prompt instructions
3. Test with different creative types

## Troubleshooting

### Import Errors

Run Python commands from the `ai-orchestrator` directory:

```bash
cd ai-orchestrator
python -c "from app.modules.ad_creative.capability import AdCreative"
```

### MCP Connection Failures

Check Web Platform is running and service token is valid:

```bash
curl -H "Authorization: Bearer $WEB_PLATFORM_SERVICE_TOKEN" \
  http://localhost:8000/api/v1/mcp/v1/execute
```

### Redis Connection Issues

Caching is optional. Module works without Redis, but performance may be reduced.

## License

Internal use only - AAE Platform
