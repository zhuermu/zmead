# AWS Integration and E2E Tests

This directory contains comprehensive integration and end-to-end tests for the AWS migration.

## Test Categories

### 1. S3 Integration Tests (`test_s3_integration.py`)
Tests S3 storage operations including:
- File upload and download
- Presigned URL generation
- CDN URL generation
- File listing and metadata
- Storage backend factory

**Requirements Validated:** 1.1, 1.2, 1.3, 1.4, 1.5

### 2. End-to-End Model Selection Tests (`test_e2e_model_selection.py`)
Tests complete user workflows for model selection:
- Model preference selection
- Model switching
- Preference persistence
- Validation and error handling

**Requirements Validated:** 2.5, 7.4

### 3. Performance Tests (`test_performance_aws.py`)
Tests AWS service performance characteristics:
- S3 upload/download performance
- Presigned URL generation speed
- Concurrent operations
- Latency distribution
- Throughput measurements

**Requirements Validated:** 8.5

## Prerequisites

### AWS Configuration

1. **AWS Credentials**: Set up AWS credentials in one of these ways:
   ```bash
   # Option 1: Environment variables
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_REGION=us-west-2
   
   # Option 2: AWS credentials file (~/.aws/credentials)
   [default]
   aws_access_key_id = your_access_key
   aws_secret_access_key = your_secret_key
   ```

2. **S3 Buckets**: Create test S3 buckets:
   ```bash
   aws s3 mb s3://aae-test-bucket --region us-west-2
   ```

3. **IAM Permissions**: Ensure your AWS user/role has permissions for:
   - S3: `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject`, `s3:ListBucket`
   - Bedrock: `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`
   - SageMaker: `sagemaker:InvokeEndpoint`

### Environment Variables

Set these in `backend/.env`:
```bash
# AWS Configuration
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# S3 Buckets
S3_BUCKET_CREATIVES=aae-test-bucket
S3_BUCKET_LANDING_PAGES=aae-test-bucket
S3_BUCKET_EXPORTS=aae-test-bucket
S3_BUCKET_UPLOADS=aae-test-bucket

# CloudFront (optional)
CLOUDFRONT_DOMAIN=d1234567890.cloudfront.net
```

## Running Tests

### Run All Integration Tests
```bash
cd backend
pytest tests/test_s3_integration.py -v
pytest tests/test_e2e_model_selection.py -v
pytest tests/test_performance_aws.py -v
```

### Run Specific Test Class
```bash
pytest tests/test_s3_integration.py::TestS3Integration -v
```

### Run Specific Test
```bash
pytest tests/test_s3_integration.py::TestS3Integration::test_upload_and_download_file -v
```

### Run with Coverage
```bash
pytest tests/test_s3_integration.py --cov=app.core.storage --cov-report=html
```

### Skip Tests if AWS Not Configured
Tests automatically skip if AWS is not configured:
```bash
pytest tests/test_s3_integration.py -v
# Output: SKIPPED [1] AWS not configured
```

### Run Performance Tests
```bash
# Performance tests print detailed statistics
pytest tests/test_performance_aws.py -v -s
```

## Test Markers

Tests use pytest markers for categorization:
- `@pytest.mark.asyncio`: Async tests
- `@pytest.mark.skipif(not is_aws_available())`: Skip if AWS not configured

## Troubleshooting

### Tests Skip with "AWS not configured"
- Verify AWS credentials are set correctly
- Check `backend/.env` file exists and has correct values
- Ensure `AWS_REGION` is set

### S3 Tests Fail with "Access Denied"
- Verify IAM permissions for S3 operations
- Check bucket names are correct
- Ensure buckets exist in the specified region

### Performance Tests Timeout
- Increase timeout values in test fixtures
- Check network connectivity to AWS
- Verify AWS region is geographically close

### Cleanup Issues
- Tests automatically cleanup created files
- If cleanup fails, manually delete test files:
  ```bash
  aws s3 rm s3://aae-test-bucket/perf-test/ --recursive
  aws s3 rm s3://aae-test-bucket/test/ --recursive
  ```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Integration Tests

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
          cd backend
          pip install -e .
          pip install pytest pytest-asyncio pytest-cov
      
      - name: Run integration tests
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_REGION: us-west-2
        run: |
          cd backend
          pytest tests/test_s3_integration.py -v
          pytest tests/test_e2e_model_selection.py -v
```

## Test Data

Tests use:
- Randomly generated file names to avoid conflicts
- Small file sizes for fast execution
- Automatic cleanup after each test
- In-memory SQLite database for backend tests

## Performance Benchmarks

Expected performance (approximate):
- S3 small file upload (1KB): < 2s
- S3 medium file upload (100KB): < 5s
- S3 large file upload (1MB): < 10s
- Presigned URL generation: < 0.5s
- File existence check: < 1s
- File listing (50 files): < 5s

## Contributing

When adding new integration tests:
1. Follow existing test patterns
2. Use appropriate fixtures
3. Add cleanup in `finally` blocks
4. Document requirements validated
5. Add skip conditions for missing dependencies
6. Update this README with new test information
