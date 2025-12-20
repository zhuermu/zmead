"""AWS configuration validation utilities for AI Orchestrator."""

import logging
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class AWSConfigValidator:
    """Validates AWS configuration and service connectivity for AI Orchestrator."""

    def __init__(self) -> None:
        """Initialize validator with settings."""
        self.settings = get_settings()

    def validate_credentials(self) -> tuple[bool, str]:
        """Validate AWS credentials are configured and valid.

        Returns:
            Tuple of (is_valid, message)
        """
        try:
            # Try to get caller identity to validate credentials
            sts = boto3.client(
                "sts",
                region_name=self.settings.aws_region,
                aws_access_key_id=self.settings.aws_access_key_id or None,
                aws_secret_access_key=self.settings.aws_secret_access_key or None,
                aws_session_token=self.settings.aws_session_token or None,
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

    def validate_bedrock_access(self) -> tuple[bool, str]:
        """Validate AWS Bedrock service access.

        Returns:
            Tuple of (is_valid, message)
        """
        try:
            # Try to list foundation models to verify access
            bedrock_client = boto3.client(
                "bedrock",
                region_name=self.settings.bedrock_region,
                aws_access_key_id=self.settings.aws_access_key_id or None,
                aws_secret_access_key=self.settings.aws_secret_access_key or None,
                aws_session_token=self.settings.aws_session_token or None,
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

    def validate_sagemaker_endpoint(self, endpoint_name: str) -> tuple[bool, str]:
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
                region_name=self.settings.sagemaker_region,
                aws_access_key_id=self.settings.aws_access_key_id or None,
                aws_secret_access_key=self.settings.aws_secret_access_key or None,
                aws_session_token=self.settings.aws_session_token or None,
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

    def validate_all(self, check_optional: bool = False) -> dict[str, tuple[bool, str]]:
        """Validate all AWS configurations.

        Args:
            check_optional: Whether to check optional services (SageMaker endpoints)

        Returns:
            Dictionary mapping service name to (is_valid, message) tuple
        """
        results: dict[str, tuple[bool, str]] = {}

        # Always validate credentials
        results["credentials"] = self.validate_credentials()

        # Validate Bedrock
        results["bedrock"] = self.validate_bedrock_access()

        # Optionally validate SageMaker endpoints
        if check_optional:
            if self.settings.sagemaker_qwen_image_endpoint:
                results["sagemaker_qwen_image"] = self.validate_sagemaker_endpoint(
                    self.settings.sagemaker_qwen_image_endpoint
                )
            if self.settings.sagemaker_wan_video_endpoint:
                results["sagemaker_wan_video"] = self.validate_sagemaker_endpoint(
                    self.settings.sagemaker_wan_video_endpoint
                )

        return results

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
        check_optional: Whether to check optional services (SageMaker endpoints)

    Note:
        This function logs warnings but does not raise exceptions to allow
        the application to start even if AWS services are not fully configured.
    """
    logger.info("Validating AWS configuration...")

    validator = AWSConfigValidator()
    all_valid, messages = validator.get_validation_summary(check_optional=check_optional)

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
