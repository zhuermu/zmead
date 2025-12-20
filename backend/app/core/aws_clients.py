"""AWS service client factories with proper error handling and configuration."""

import logging
from functools import lru_cache
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global flag to track if AWS is available
_aws_available: bool | None = None


class AWSClientError(Exception):
    """Custom exception for AWS client errors."""

    pass


def _get_aws_session() -> boto3.Session | None:
    """Create AWS session with configured credentials.
    
    Returns:
        boto3.Session instance or None if credentials are not available.
    """
    global _aws_available
    
    try:
        # Create session with explicit credentials if provided
        session_kwargs: dict[str, Any] = {}
        
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            session_kwargs["aws_access_key_id"] = settings.aws_access_key_id
            session_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
            
            if settings.aws_session_token:
                session_kwargs["aws_session_token"] = settings.aws_session_token
        
        if settings.aws_region:
            session_kwargs["region_name"] = settings.aws_region
        
        session = boto3.Session(**session_kwargs)
        
        # Test credentials by making a simple STS call
        sts = session.client("sts")
        sts.get_caller_identity()
        
        _aws_available = True
        logger.info("AWS session initialized successfully")
        return session
        
    except NoCredentialsError:
        logger.warning(
            "AWS credentials not found. AWS services will be disabled. "
            "Configure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY or use IAM roles."
        )
        _aws_available = False
        return None
    except ClientError as e:
        logger.warning(f"AWS credentials validation failed: {e}. AWS services will be disabled.")
        _aws_available = False
        return None
    except Exception as e:
        logger.warning(f"AWS session initialization failed: {e}. AWS services will be disabled.")
        _aws_available = False
        return None


def is_aws_available() -> bool:
    """Check if AWS services are available.
    
    Returns:
        True if AWS credentials are configured and valid, False otherwise.
    """
    if _aws_available is None:
        _get_aws_session()  # Trigger lazy initialization
    return _aws_available or False


@lru_cache(maxsize=1)
def get_s3_client():
    """Get S3 client with retry configuration.
    
    Returns:
        boto3 S3 client or None if AWS is not available.
        
    Raises:
        AWSClientError: If client creation fails after AWS is confirmed available.
    """
    if not is_aws_available():
        return None
    
    try:
        session = _get_aws_session()
        if session is None:
            return None
        
        # Configure retry behavior
        config = Config(
            region_name=settings.aws_region,
            retries={
                "max_attempts": 3,
                "mode": "adaptive",
            },
            signature_version="s3v4",
        )
        
        client = session.client("s3", config=config)
        logger.info("S3 client initialized successfully")
        return client
        
    except Exception as e:
        logger.error(f"Failed to create S3 client: {e}")
        raise AWSClientError(f"S3 client initialization failed: {e}") from e


@lru_cache(maxsize=1)
def get_bedrock_runtime_client():
    """Get Bedrock Runtime client for model inference.
    
    Returns:
        boto3 Bedrock Runtime client or None if AWS is not available.
        
    Raises:
        AWSClientError: If client creation fails after AWS is confirmed available.
    """
    if not is_aws_available():
        return None
    
    try:
        session = _get_aws_session()
        if session is None:
            return None
        
        # Configure retry behavior
        config = Config(
            region_name=settings.bedrock_region,
            retries={
                "max_attempts": 3,
                "mode": "adaptive",
            },
            read_timeout=300,  # 5 minutes for long-running inference
        )
        
        client = session.client("bedrock-runtime", config=config)
        logger.info("Bedrock Runtime client initialized successfully")
        return client
        
    except Exception as e:
        logger.error(f"Failed to create Bedrock Runtime client: {e}")
        raise AWSClientError(f"Bedrock Runtime client initialization failed: {e}") from e


@lru_cache(maxsize=1)
def get_sagemaker_runtime_client():
    """Get SageMaker Runtime client for custom model inference.
    
    Returns:
        boto3 SageMaker Runtime client or None if AWS is not available.
        
    Raises:
        AWSClientError: If client creation fails after AWS is confirmed available.
    """
    if not is_aws_available():
        return None
    
    try:
        session = _get_aws_session()
        if session is None:
            return None
        
        # Configure retry behavior
        config = Config(
            region_name=settings.sagemaker_region,
            retries={
                "max_attempts": 3,
                "mode": "adaptive",
            },
            read_timeout=300,  # 5 minutes for long-running inference
        )
        
        client = session.client("sagemaker-runtime", config=config)
        logger.info("SageMaker Runtime client initialized successfully")
        return client
        
    except Exception as e:
        logger.error(f"Failed to create SageMaker Runtime client: {e}")
        raise AWSClientError(f"SageMaker Runtime client initialization failed: {e}") from e


@lru_cache(maxsize=1)
def get_cloudfront_client():
    """Get CloudFront client for CDN management.
    
    Returns:
        boto3 CloudFront client or None if AWS is not available.
        
    Raises:
        AWSClientError: If client creation fails after AWS is confirmed available.
    """
    if not is_aws_available():
        return None
    
    try:
        session = _get_aws_session()
        if session is None:
            return None
        
        # CloudFront is a global service, but we still specify region
        config = Config(
            region_name=settings.aws_region,
            retries={
                "max_attempts": 3,
                "mode": "adaptive",
            },
        )
        
        client = session.client("cloudfront", config=config)
        logger.info("CloudFront client initialized successfully")
        return client
        
    except Exception as e:
        logger.error(f"Failed to create CloudFront client: {e}")
        raise AWSClientError(f"CloudFront client initialization failed: {e}") from e


def validate_aws_configuration() -> dict[str, bool]:
    """Validate AWS configuration and service availability.
    
    Returns:
        Dictionary with service availability status.
    """
    results = {
        "aws_available": is_aws_available(),
        "s3_available": False,
        "bedrock_available": False,
        "sagemaker_available": False,
        "cloudfront_available": False,
    }
    
    if not results["aws_available"]:
        logger.warning("AWS is not available. Skipping service validation.")
        return results
    
    # Test S3
    try:
        s3_client = get_s3_client()
        if s3_client:
            s3_client.list_buckets()
            results["s3_available"] = True
    except Exception as e:
        logger.warning(f"S3 validation failed: {e}")
    
    # Test Bedrock
    try:
        bedrock_client = get_bedrock_runtime_client()
        if bedrock_client:
            # Bedrock doesn't have a simple list operation, so we just check client creation
            results["bedrock_available"] = True
    except Exception as e:
        logger.warning(f"Bedrock validation failed: {e}")
    
    # Test SageMaker
    try:
        sagemaker_client = get_sagemaker_runtime_client()
        if sagemaker_client:
            # SageMaker Runtime doesn't have a simple list operation
            results["sagemaker_available"] = True
    except Exception as e:
        logger.warning(f"SageMaker validation failed: {e}")
    
    # Test CloudFront
    try:
        cloudfront_client = get_cloudfront_client()
        if cloudfront_client:
            cloudfront_client.list_distributions(MaxItems="1")
            results["cloudfront_available"] = True
    except Exception as e:
        logger.warning(f"CloudFront validation failed: {e}")
    
    return results


def get_aws_health_status() -> dict[str, Any]:
    """Get comprehensive AWS service health status.
    
    Returns:
        Dictionary with detailed health information.
    """
    validation = validate_aws_configuration()
    
    return {
        "aws_configured": bool(settings.aws_access_key_id and settings.aws_secret_access_key),
        "aws_region": settings.aws_region,
        "services": validation,
        "configuration": {
            "s3_buckets": {
                "creatives": settings.s3_bucket_creatives,
                "landing_pages": settings.s3_bucket_landing_pages,
                "exports": settings.s3_bucket_exports,
                "uploads": settings.s3_bucket_uploads,
            },
            "cloudfront_domain": settings.cloudfront_domain or None,
            "bedrock_model": settings.bedrock_default_model,
            "sagemaker_endpoints": {
                "qwen_image": settings.sagemaker_qwen_image_endpoint or None,
                "wan_video": settings.sagemaker_wan_video_endpoint or None,
            },
        },
    }
