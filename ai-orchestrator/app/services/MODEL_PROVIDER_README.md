# Multi-Provider AI Model Architecture

This directory contains the multi-provider AI model architecture that enables the AAE platform to support multiple AI providers (Gemini, AWS Bedrock, AWS SageMaker) with a unified interface.

## Architecture Overview

The architecture consists of:

1. **ModelProvider** - Abstract base class defining the interface
2. **Provider Implementations** - Concrete implementations for each provider
3. **ModelProviderFactory** - Factory for creating providers based on configuration
4. **Configuration Models** - Pydantic models for provider configuration

## Components

### Base Classes

- **`model_provider.py`** - Abstract base class and error types
  - `ModelProvider` - Base class with retry logic and error handling
  - `ModelProviderError` - Base exception for provider errors

### Provider Implementations

- **`gemini_provider.py`** - Google Gemini provider
  - Wraps existing `GeminiClient`
  - Supports Gemini 2.5 Flash, Gemini 2.5 Pro, Gemini 3 Pro
  - Includes image generation capabilities

- **`bedrock_provider.py`** - AWS Bedrock provider
  - Supports Claude 4.5 Sonnet, Qwen3, Nova 2 Lite
  - Uses boto3 for AWS API calls
  - Implements streaming and structured output

- **`sagemaker_provider.py`** - AWS SageMaker provider
  - For custom model deployments
  - Supports Qwen-Image and Wan2.2 video models
  - Direct endpoint invocation

### Factory and Configuration

- **`model_factory.py`** - Provider factory and configuration
  - `ModelProviderFactory` - Creates providers from configuration
  - `ModelConfig` - Provider configuration model
  - `ConversationalModelConfig` - Available conversational models
  - `GenerationModelConfig` - Creative generation model configuration

## Usage Examples

### Basic Usage

```python
from app.services.model_factory import ModelConfig, ModelProviderFactory

# Create Gemini provider
config = ModelConfig(provider="gemini")
provider = ModelProviderFactory.create_provider(config)

# Chat completion
messages = [{"role": "user", "content": "Hello!"}]
response = await provider.chat_completion(messages)
```

### User Model Selection

```python
# User selects their preferred model
user_provider = "bedrock"
user_model = "claude-4.5-sonnet"

# Create provider from user preference
provider = ModelProviderFactory.create_from_user_preference(
    provider=user_provider,
    model=user_model,
)

response = await provider.chat_completion(messages)
```

### Streaming Responses

```python
# Stream chat completion
async for chunk in provider.chat_completion_stream(messages):
    print(chunk, end="", flush=True)
```

### Structured Output

```python
from pydantic import BaseModel

class CityInfo(BaseModel):
    name: str
    country: str
    population: int

messages = [{"role": "user", "content": "Tell me about Paris"}]
result = await provider.structured_output(messages, CityInfo)
```

### AWS Bedrock with Custom Credentials

```python
config = ModelConfig(
    provider="bedrock",
    bedrock_model_name="claude-4.5-sonnet",
    bedrock_region="us-west-2",
    aws_access_key_id="...",
    aws_secret_access_key="...",
)
provider = ModelProviderFactory.create_provider(config)
```

### SageMaker Custom Model

```python
config = ModelConfig(
    provider="sagemaker",
    sagemaker_endpoint_name="qwen-image-endpoint",
    sagemaker_region="us-west-2",
)
provider = ModelProviderFactory.create_provider(config)

# Generate image
image_bytes = await provider.generate_image(
    prompt="A beautiful sunset",
    aspect_ratio="16:9",
)
```

## Available Models

### Gemini Models

- `gemini-2.5-flash` - Fast responses, good for chat
- `gemini-2.5-pro` - Balanced performance and quality
- `gemini-3-pro` - Best quality, complex reasoning

### Bedrock Models

- `claude-4.5-sonnet` - Anthropic Claude 4.5 Sonnet
- `qwen3` - Alibaba Qwen3 235B
- `nova-2-lite` - Amazon Nova 2 Lite

### SageMaker Models

- Custom endpoints for specialized models
- Qwen-Image for image generation
- Wan2.2 for video generation

## Configuration

### Environment Variables

```bash
# Gemini
GEMINI_API_KEY=your_api_key

# AWS (optional, uses default credentials if not set)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-west-2
```

### Settings Integration

The providers integrate with `app.core.config.Settings`:

```python
from app.core.config import get_settings

settings = get_settings()

# Gemini provider uses settings automatically
provider = GeminiProvider()  # Uses settings.gemini_api_key
```

## Error Handling

All providers raise `ModelProviderError` with:

- `message` - Error description
- `code` - Error code (RATE_LIMIT, TIMEOUT, etc.)
- `retryable` - Whether the error is retryable
- `provider` - Provider name

```python
from app.services.model_provider import ModelProviderError

try:
    response = await provider.chat_completion(messages)
except ModelProviderError as e:
    if e.retryable:
        # Retry logic
        pass
    else:
        # Handle non-retryable error
        pass
```

## Retry Logic

All providers include automatic retry with exponential backoff:

- Default: 3 retries
- Backoff: 1s, 2s, 4s
- Configurable via `max_retries`, `backoff_base`, `backoff_factor`

## Integration with Existing Code

The architecture maintains backward compatibility:

```python
# Old way (still works)
from app.services.gemini_client import GeminiClient
client = GeminiClient()

# New way (recommended)
from app.services.model_factory import ModelProviderFactory
provider = ModelProviderFactory.get_default_provider()
```

## Testing

See `model_provider_example.py` for comprehensive examples.

Run examples:
```bash
cd ai-orchestrator
python -m app.services.model_provider_example
```

## Future Enhancements

- [ ] Add support for more Bedrock models
- [ ] Implement model performance monitoring
- [ ] Add cost tracking per provider
- [ ] Support for model fallback chains
- [ ] Caching layer for repeated requests
- [ ] A/B testing between providers

## Requirements

### Dependencies

- `boto3>=1.35.0` - AWS SDK
- `botocore>=1.35.0` - AWS SDK core
- `google-genai>=0.8.0` - Gemini SDK
- `pydantic>=2.9.0` - Configuration and validation

### AWS Permissions

For Bedrock:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "*"
    }
  ]
}
```

For SageMaker:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sagemaker:InvokeEndpoint"
      ],
      "Resource": "*"
    }
  ]
}
```

## Support

For issues or questions:
1. Check the examples in `model_provider_example.py`
2. Review error messages and codes
3. Verify AWS credentials and permissions
4. Check provider-specific documentation
