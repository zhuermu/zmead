"""AWS configuration validation utilities."""

import logging
from typing import Literal

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from app.core.config import settings

logger = logging.getLogger(__name__)


class AWSConfigValidator:
    """Validates AWS configuration and service connectivity."""

    @staticmethod
    def validate_credentials() -> tuple[bool, str]:
        """Validate AWS credentials are configured and valid.

        Returns:
            Tuple of (is_valid, message)
        """
        try:
            # Try to get caller identity to validate credentials
            sts = boto3.client(
                "sts",
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id or None,
                aws_secret_access_key=settings.aws_secret_access_key or None,
                aws_session_token=settings.aws_session_token or None,
            )
            identity = sts.get_caller_identity()
            account_id = identity.get("Account", "unknown")
            arn = identity.get("Arn", "unknown")

            logger.info(f"AWS credentials validated. Account: {account_id}, ARN: {arn}")
            return True, f"AWS credentials valid for account {account_id}"

        except NoCredentialsError:
            msg = "AWS credentials not found. Configure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY or use IAM roles."
            logger.warning(msg)
            return False, msg

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            msg = f"AWS credentials invalid: {error_code} - {str(e)}"
            logger.error(msg)
            return False, msg

        except BotoCoreError as e:
            msg = f"AWS configuration error: {str(e)}"
            logger.error(msg)
            return False, msg

    @staticmethod
    def validate_s3_access(bucket_name: str) -> tuple[bool, str]:
        """Validate S3 bucket access.

        Args:
            bucket_name: Name of the S3 bucket to validate

        Returns:
            Tuple of (is_valid, message)
        """
        try:
            s3 = boto3.client(
                "s3",
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id or None,
                aws_secret_access_key=settings.aws_secret_access_key or None,
                aws_session_token=settings.aws_session_token or None,
            )

            # Try to head the bucket to verify access
            s3.head_bucket(Bucket=bucket_name)
            logger.info(f"S3 bucket '{bucket_name}' is accessible")
            return True, f"S3 bucket '{bucket_name}' is accessible"

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "404":
                msg = f"S3 bucket '{bucket_name}' does not exist"
            elif error_code == "403":
                msg = f"Access denied to S3 bucket '{bucket_name}'"
            else:
                msg = f"S3 bucket validation failed: {error_code} - {str(e)}"
            logger.error(msg)
            return False, msg

        except BotoCoreError as e:
            msg = f"S3 configuration error: {str(e)}"
            logger.error(msg)
            return False, msg

    @staticmethod
    def validate_bedrock_access() -> tuple[bool, str]:
        """Validate AWS Bedrock service access.

        Returns:
            Tuple of (is_valid, message)
        """
        try:
            bedrock = boto3.client(
                "bedrock-runtime",
                region_name=settings.bedrock_region,
                aws_access_key_id=settings.aws_access_key_id or None,
                aws_secret_access_key=settings.aws_secret_access_key or None,
                aws_session_token=settings.aws_session_token or None,
            )

            # Try to list foundation models to verify access
            # Note: This is a read-only operation that doesn't incur charges
            bedrock_client = boto3.client(
                "bedrock",
                region_name=settings.bedrock_region,
                aws_access_key_id=settings.aws_access_key_id or None,
                aws_secret_access_key=settings.aws_secret_access_key or None,
                aws_session_token=settings.aws_session_token or None,
            )
            bedrock_client.list_foundation_models(byProvider="Anthropic")

            logger.info("AWS Bedrock service is accessible")
            return True, "AWS Bedrock service is accessible"

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            msg = f"Bedrock access validation failed: {error_code} - {str(e)}"
            logger.error(msg)
            return False, msg

        except BotoCoreError as e:
            msg = f"Bedrock configuration error: {str(e)}"
            logger.error(msg)
            return False, msg

    @staticmethod
    def validate_sagemaker_endpoint(endpoint_name: str) -> tuple[bool, str]:
        """Validate SageMaker endpoint exists and is in service.

        Args:
            endpoint_name: Name of the SageMaker endpoint

        Returns:
            Tuple of (is_valid, message)
        """
        if not endpoint_name:
            return False, "SageMaker endpoint name not configured"

        try:
            sagemaker = boto3.client(
                "sagemaker",
                region_name=settings.sagemaker_region,
                aws_access_key_id=settings.aws_access_key_id or None,
                aws_secret_access_key=settings.aws_secret_access_key or None,
                aws_session_token=settings.aws_session_token or None,
            )

            response = sagemaker.describe_endpoint(EndpointName=endpoint_name)
            status = response.get("EndpointStatus", "Unknown")

            if status == "InService":
                logger.info(f"SageMaker endpoint '{endpoint_name}' is in service")
                return True, f"SageMaker endpoint '{endpoint_name}' is in service"
            else:
                msg = f"SageMaker endpoint '{endpoint_name}' status: {status}"
                logger.warning(msg)
                return False, msg

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "ValidationException":
                msg = f"SageMaker endpoint '{endpoint_name}' does not exist"
            else:
                msg = f"SageMaker endpoint validation failed: {error_code} - {str(e)}"
            logger.error(msg)
            return False, msg

        except BotoCoreError as e:
            msg = f"SageMaker configuration error: {str(e)}"
            logger.error(msg)
            return False, msg

    @classmethod
    def validate_all(
        self, check_optional: bool = False
    ) -> dict[str, tuple[bool, str]]:
        """Validate all AWS configurations.

        Args:
            check_optional: Whether to check optional services (SageMaker endpoints)

        Returns:
            Dictionary mapping service name to (is_valid, message) tuple
        """
        results = {}

        # Always validate credentials
        results["credentials"] = self.validate_credentials()

        # Validate S3 buckets
        results["s3_creatives"] = self.validate_s3_access(settings.s3_bucket_creatives)
        results["s3_landing_pages"] = self.validate_s3_access(settings.s3_bucket_landing_pages)
        results["s3_exports"] = self.validate_s3_access(settings.s3_bucket_exports)
        results["s3_uploads"] = self.validate_s3_access(settings.s3_bucket_uploads)

        # Validate Bedrock
        results["bedrock"] = self.validate_bedrock_access()

        # Optionally validate SageMaker endpoints
        if check_optional:
            if settings.sagemaker_qwen_image_endpoint:
                results["sagemaker_qwen_image"] = self.validate_sagemaker_endpoint(
                    settings.sagemaker_qwen_image_endpoint
                )
            if settings.sagemaker_wan_video_endpoint:
                results["sagemaker_wan_video"] = self.validate_sagemaker_endpoint(
                    settings.sagemaker_wan_video_endpoint
                )

        return results

    @classmethod
    def get_validation_summary(
        self, check_optional: bool = False
    ) -> tuple[bool, dict[str, str]]:
        """Get a summary of AWS configuration validation.

        Args:
            check_optional: Whether to check optional services

        Returns:
            Tuple of (all_valid, results_dict) where results_dict maps service to message
        """
        results = self.validate_all(check_optional=check_optional)

        all_valid = all(is_valid for is_valid, _ in results.values())
        messages = {service: msg for service, (_, msg) in results.items()}

        return all_valid, messages


def validate_aws_config_on_startup(check_optional: bool = False) -> None:
    """Validate AWS configuration on application startup.

    Args:
        check_optional: Whether to check optional services

    Raises:
        RuntimeError: If critical AWS services are not accessible
    """
    logger.info("Validating AWS configuration...")

    all_valid, messages = AWSConfigValidator.get_validation_summary(
        check_optional=check_optional
    )

    # Log all validation results
    for service, message in messages.items():
        if "valid" in message.lower() or "accessible" in message.lower():
            logger.info(f"✓ {service}: {message}")
        else:
            logger.warning(f"✗ {service}: {message}")

    if not all_valid:
        logger.warning(
            "Some AWS services are not accessible. "
            "Application will start but AWS features may not work correctly."
        )
    else:
        logger.info("All AWS services validated successfully")
