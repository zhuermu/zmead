# SageMaker Deployment Scripts

This directory contains scripts for deploying and testing custom models on AWS SageMaker.

## Prerequisites

1. AWS Account with SageMaker access
2. AWS CLI configured with credentials
3. IAM role for SageMaker with appropriate permissions
4. Model artifacts uploaded to S3
5. Docker images for inference pushed to ECR

## Deployment Scripts

### deploy_qwen_image.py

Deploy the Qwen-Image model for image generation.

**Usage:**
```bash
python deploy_qwen_image.py \
  --region us-west-2 \
  --model-name qwen-image-model \
  --endpoint-name qwen-image-endpoint \
  --role-arn arn:aws:iam::ACCOUNT_ID:role/SageMakerRole \
  --image-uri ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/qwen-image:latest \
  --model-data s3://my-bucket/models/qwen-image/model.tar.gz \
  --instance-type ml.g4dn.xlarge \
  --wait
```

**Parameters:**
- `--region`: AWS region (default: us-west-2)
- `--model-name`: Name for the SageMaker model
- `--endpoint-name`: Name for the endpoint
- `--role-arn`: IAM role ARN for SageMaker (required)
- `--image-uri`: Docker image URI from ECR (required)
- `--model-data`: S3 URL to model artifacts (required)
- `--instance-type`: EC2 instance type (default: ml.g4dn.xlarge)
- `--wait`: Wait for endpoint to be ready

### deploy_wan_video.py

Deploy the Wan2.2 model for video generation.

**Usage:**
```bash
python deploy_wan_video.py \
  --region us-west-2 \
  --model-name wan-video-model \
  --endpoint-name wan-video-endpoint \
  --role-arn arn:aws:iam::ACCOUNT_ID:role/SageMakerRole \
  --image-uri ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/wan-video:latest \
  --model-data s3://my-bucket/models/wan-video/model.tar.gz \
  --instance-type ml.g5.2xlarge \
  --wait
```

**Parameters:**
- Same as deploy_qwen_image.py
- Default instance type: ml.g5.2xlarge (more GPU for video)

## Test Scripts

### test_qwen_image.py

Test the deployed Qwen-Image endpoint.

**Usage:**
```bash
# Using environment variables
export SAGEMAKER_QWEN_IMAGE_ENDPOINT=qwen-image-endpoint
export SAGEMAKER_REGION=us-west-2
python test_qwen_image.py

# Or with command line arguments
python test_qwen_image.py \
  --endpoint qwen-image-endpoint \
  --region us-west-2 \
  --prompt "A beautiful sunset over mountains"
```

### test_wan_video.py

Test the deployed Wan2.2 video endpoint.

**Usage:**
```bash
# Using environment variables
export SAGEMAKER_WAN_VIDEO_ENDPOINT=wan-video-endpoint
export SAGEMAKER_REGION=us-west-2
python test_wan_video.py

# Or with command line arguments
python test_wan_video.py \
  --endpoint wan-video-endpoint \
  --region us-west-2 \
  --prompt "A cat playing with a ball of yarn"
```

## Environment Configuration

After deployment, add the endpoint names to your `.env` files:

**ai-orchestrator/.env:**
```bash
SAGEMAKER_REGION=us-west-2
SAGEMAKER_QWEN_IMAGE_ENDPOINT=qwen-image-endpoint
SAGEMAKER_WAN_VIDEO_ENDPOINT=wan-video-endpoint
```

**backend/.env:**
```bash
SAGEMAKER_REGION=us-west-2
SAGEMAKER_QWEN_IMAGE_ENDPOINT=qwen-image-endpoint
SAGEMAKER_WAN_VIDEO_ENDPOINT=wan-video-endpoint
```

## IAM Role Requirements

The SageMaker execution role needs the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-bucket/*",
        "arn:aws:s3:::my-bucket"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

## Troubleshooting

### Endpoint Creation Fails

1. Check IAM role permissions
2. Verify model artifacts are accessible in S3
3. Ensure Docker image is in ECR and accessible
4. Check CloudWatch logs for detailed error messages

### Endpoint Takes Too Long

- Image models: ~5-10 minutes
- Video models: ~10-15 minutes
- Use `--wait` flag to monitor progress

### Test Scripts Fail

1. Verify endpoint is "InService" in AWS Console
2. Check AWS credentials are configured
3. Ensure endpoint names match in .env files
4. Review CloudWatch logs for endpoint errors

## Cost Optimization

- Use smaller instance types for testing (ml.g4dn.xlarge)
- Delete endpoints when not in use
- Use auto-scaling for production workloads
- Monitor usage with AWS Cost Explorer
