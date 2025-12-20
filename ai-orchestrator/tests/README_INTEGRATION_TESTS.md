# AI Orchestrator AWS Integration Tests

This directory contains integration and end-to-end tests for AWS Bedrock and SageMaker integrations.

## Test Categories

### 1. Bedrock Integration Tests (`test_bedrock_integration.py`)
Tests AWS Bedrock model inference including:
- Chat completion with Claude, Qwen, and Nova models
- Streaming responses
- Structured output generation
- Multi-turn conversations
- Error handling and retry logic
- Temperature and token control

**Requirements Validated:** 2.1, 2.2, 2.3, 2.4

### 2. SageMaker Integration Tests (`test_sagemaker_integration.py`)
Tests AWS SageMaker custom model invocation including:
- Qwen-Image model for image generation
- Wan2.2 model for video generation
- Endpoint invocation with various parameters
- Timeout and error handling
- Retry logic
- Concurrent requests

**Requirements Validated:** 3.1, 3.2, 3.4, 3.5

### 3. End-to-End AWS Integration Tests (`test_e2e_aws_integration.py`)
Tests complete workflows spanning multiple services:
- Creative generation workflow (text + image)
- Multi-model conversation workflows
- Model failover and error recovery
- Concurrent multi-provider requests
- Streaming with multiple models
- Model selection based on task type
- Performance comparison across models

**Requirements Validated:** 8.4, 8.5

## Prerequisites

### AWS Configuration

1. **AWS Credentials**: Set up AWS credentials:
   ```bash
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_REGION=us-west-2
   ```

2. **Bedrock Model Access**: Enable model access in AWS Bedrock console:
   - Claude 4.5 Sonnet: `anthropic.claude-sonnet-4-20250514-v1:0`
   - Qwen3: `qwen.qwen3-235b-a22b-2507-v1:0`
   - Nova 2 Lite: `us.amazon.nova-lite-v1:0`

3. **SageMaker Endpoints**: Deploy custom model endpoints:
   ```bash
   # Deploy Qwen-Image endpoint
   cd ai-orchestrator/scripts/sagemaker
   python deploy_qwen_image.py
   
   # Deploy Wan2.2 video endpoint
   python deploy_wan_video.py
   ```

4. **IAM Permissions**: Ensure permissions for:
   - Bedrock: `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`
   - SageMaker: `sagemaker:InvokeEndpoint`

### Environment Variables

Set these in `ai-orchestrator/.env`:
```bash
# AWS Configuration
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# Bedrock Configuration
BEDROCK_REGION=us-west-2
BEDROCK_DEFAULT_MODEL=anthropic.claude-sonnet-4-20250514-v1:0

# SageMaker Endpoints
SAGEMAKER_QWEN_IMAGE_ENDPOINT=qwen-image-endpoint
SAGEMAKER_WAN_VIDEO_ENDPOINT=wan-video-endpoint
```

## Running Tests

### Run All Integration Tests
```bash
cd ai-orchestrator
pytest tests/test_bedrock_integration.py -v
pytest tests/test_sagemaker_integration.py -v
pytest tests/test_e2e_aws_integration.py -v
```

### Run Specific Test Class
```bash
pytest tests/test_bedrock_integration.py::TestBedrockIntegration -v
```

### Run Specific Test
```bash
pytest tests/test_bedrock_integration.py::TestBedrockIntegration::test_claude_chat_completion -v
```

### Run with Output
```bash
# See print statements and detailed output
pytest tests/test_e2e_aws_integration.py -v -s
```

### Run with Coverage
```bash
pytest tests/test_bedrock_integration.py \
  --cov=app.services.bedrock_provider \
  --cov=app.services.sagemaker_provider \
  --cov-report=html
```

### Skip Tests if AWS Not Configured
Tests automatically skip if AWS is not configured:
```bash
pytest tests/test_bedrock_integration.py -v
# Output: SKIPPED [1] AWS not configured
```

## Test Fixtures

### Common Fixtures
- `claude_provider`: BedrockProvider for Claude 4.5 Sonnet
- `qwen_provider`: BedrockProvider for Qwen3
- `nova_provider`: BedrockProvider for Nova 2 Lite
- `qwen_image_provider`: SageMakerProvider for Qwen-Image
- `wan_video_provider`: SageMakerProvider for Wan2.2
- `model_factory`: ModelFactory for creating providers

## Troubleshooting

### Tests Skip with "AWS not configured"
- Verify AWS credentials are set
- Check `ai-orchestrator/.env` file
- Ensure `AWS_REGION` is set

### Bedrock Tests Fail with "Access Denied"
- Enable model access in Bedrock console
- Verify IAM permissions
- Check model IDs are correct

### SageMaker Tests Fail with "Endpoint Not Found"
- Deploy SageMaker endpoints first
- Verify endpoint names in `.env`
- Check endpoints are in "InService" status:
  ```bash
  aws sagemaker describe-endpoint --endpoint-name qwen-image-endpoint
  ```

### Tests Timeout
- Increase timeout values in provider initialization
- Check network connectivity to AWS
- Verify endpoints are responding:
  ```bash
  aws sagemaker invoke-endpoint \
    --endpoint-name qwen-image-endpoint \
    --body '{"prompt":"test"}' \
    --content-type application/json \
    output.json
  ```

### Rate Limiting Errors
- Tests include retry logic for rate limits
- Reduce concurrent test execution
- Request quota increase from AWS if needed

## Performance Expectations

### Bedrock Models
- Claude 4.5 Sonnet: 2-10s for typical responses
- Qwen3: 2-8s for typical responses
- Nova 2 Lite: 1-5s for typical responses
- Streaming: First token < 2s

### SageMaker Models
- Qwen-Image: 10-60s depending on parameters
- Wan2.2 Video: 30-180s depending on duration
- Endpoint cold start: Additional 30-60s

## CI/CD Integration

### GitHub Actions Example
```yaml
name: AI Orchestrator Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          cd ai-orchestrator
          pip install -e .
          pip install pytest pytest-asyncio
      
      - name: Run Bedrock tests
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_REGION: us-west-2
        run: |
          cd ai-orchestrator
          pytest tests/test_bedrock_integration.py -v
      
      - name: Run E2E tests
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_REGION: us-west-2
        run: |
          cd ai-orchestrator
          pytest tests/test_e2e_aws_integration.py -v
```

## Cost Considerations

Running these tests will incur AWS costs:
- **Bedrock**: ~$0.01-0.10 per test run
- **SageMaker**: ~$0.50-2.00 per hour (endpoint hosting)
- **Total**: ~$1-5 per full test suite run

To minimize costs:
1. Run tests selectively during development
2. Use smaller models (Nova Lite) when possible
3. Delete SageMaker endpoints when not in use
4. Set up budget alerts in AWS

## Test Data

Tests use:
- Simple prompts for fast execution
- Low token limits to reduce costs
- Deterministic temperature (0.0) for consistency
- Minimal inference steps for generation models

## Contributing

When adding new integration tests:
1. Follow existing test patterns
2. Use appropriate fixtures
3. Add proper error handling
4. Document requirements validated
5. Add skip conditions for missing dependencies
6. Consider cost implications
7. Update this README

## Monitoring

Monitor test execution:
```bash
# View Bedrock metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name Invocations \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Sum

# View SageMaker metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/SageMaker \
  --metric-name ModelLatency \
  --dimensions Name=EndpointName,Value=qwen-image-endpoint \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Average
```
