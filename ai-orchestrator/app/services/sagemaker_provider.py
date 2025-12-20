"""AWS SageMaker model provider implementation.

This module provides integration with AWS SageMaker for deploying
and invoking custom models like Qwen-Image and Wan2.2 video generation.
"""

import json
from typing import Any, AsyncIterator, TypeVar

import boto3
import structlog
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import BaseModel

from app.services.model_provider import ModelProvider, ModelProviderError

logger = structlog.get_logger(__name__)

# Type variable for structured output
T = TypeVar("T", bound=BaseModel)


class SageMakerProvider(ModelProvider):
    """AWS SageMaker model provider implementation.

    Supports custom model deployments on SageMaker endpoints
    for specialized tasks like image and video generation.

    Example:
        provider = SageMakerProvider(
            endpoint_name="qwen-image-endpoint",
            region_name="us-west-2"
        )
        result = await provider.invoke_endpoint({
            "prompt": "A beautiful sunset",
            "aspect_ratio": "16:9"
        })
    """

    def __init__(
        self,
        endpoint_name: str,
        region_name: str = "us-west-2",
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
        max_retries: int = 3,
        backoff_base: float = 1.0,
        backoff_factor: float = 2.0,
        timeout: float = 120.0,  # Longer timeout for generation tasks
    ):
        """Initialize SageMaker provider.

        Args:
            endpoint_name: SageMaker endpoint name
            region_name: AWS region (default: us-west-2)
            aws_access_key_id: AWS access key (optional)
            aws_secret_access_key: AWS secret key (optional)
            aws_session_token: AWS session token (optional)
            max_retries: Maximum retry attempts
            backoff_base: Base wait time for retries in seconds
            backoff_factor: Multiplier for exponential backoff
            timeout: Request timeout in seconds
        """
        super().__init__(
            provider_name="sagemaker",
            max_retries=max_retries,
            backoff_base=backoff_base,
            backoff_factor=backoff_factor,
            timeout=timeout,
        )

        self.endpoint_name = endpoint_name
        self.region_name = region_name

        # Configure boto3 client
        config = Config(
            region_name=region_name,
            retries={"max_attempts": 0},  # We handle retries ourselves
            connect_timeout=timeout,
            read_timeout=timeout,
        )

        # Build session kwargs
        session_kwargs = {}
        if aws_access_key_id:
            session_kwargs["aws_access_key_id"] = aws_access_key_id
        if aws_secret_access_key:
            session_kwargs["aws_secret_access_key"] = aws_secret_access_key
        if aws_session_token:
            session_kwargs["aws_session_token"] = aws_session_token

        # Create SageMaker Runtime client
        self.client = boto3.client(
            "sagemaker-runtime",
            config=config,
            **session_kwargs,
        )

        logger.info(
            "sagemaker_provider_initialized",
            endpoint=endpoint_name,
            region=region_name,
        )

    async def invoke_endpoint(
        self,
        payload: dict[str, Any],
        content_type: str = "application/json",
        accept: str = "application/json",
    ) -> dict[str, Any]:
        """Invoke SageMaker endpoint with payload.

        Args:
            payload: Request payload for the model
            content_type: Content type of the request
            accept: Accept type for the response

        Returns:
            Response from the model

        Raises:
            ModelProviderError: If invocation fails
        """
        log = logger.bind(
            provider="sagemaker",
            endpoint=self.endpoint_name,
        )
        log.info("invoke_endpoint_start")

        try:
            # Serialize payload
            body = json.dumps(payload)

            # Invoke endpoint
            async def _invoke():
                response = self.client.invoke_endpoint(
                    EndpointName=self.endpoint_name,
                    ContentType=content_type,
                    Accept=accept,
                    Body=body,
                )
                return response

            response = await self._execute_with_retry(_invoke, "invoke_endpoint")

            # Parse response
            response_body = response["Body"].read()
            result = json.loads(response_body)

            log.info(
                "invoke_endpoint_complete",
                response_size=len(response_body),
            )

            return result

        except (BotoCoreError, ClientError) as e:
            error = self._handle_aws_error(e)
            log.error("invoke_endpoint_failed", error=str(e))
            raise error
        except Exception as e:
            raise self._handle_error(e)

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Generate chat completion.

        Note: SageMaker endpoints are typically for specialized tasks,
        not general chat. This method is provided for interface compatibility
        but may not be supported by all endpoints.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Optional temperature override
            max_tokens: Optional maximum tokens

        Returns:
            Generated response text

        Raises:
            ModelProviderError: If generation fails or not supported
        """
        log = logger.bind(
            provider="sagemaker",
            endpoint=self.endpoint_name,
        )
        log.warning("chat_completion_not_recommended_for_sagemaker")

        try:
            # Build payload for text generation
            payload = {
                "messages": messages,
                "temperature": temperature or 0.7,
                "max_tokens": max_tokens or 2048,
            }

            result = await self.invoke_endpoint(payload)

            # Extract text from response (format depends on model)
            if isinstance(result, dict):
                # Try common response formats
                if "generated_text" in result:
                    return result["generated_text"]
                elif "text" in result:
                    return result["text"]
                elif "output" in result:
                    return result["output"]

            return str(result)

        except Exception as e:
            raise ModelProviderError(
                message=f"Chat completion not supported by endpoint: {e}",
                code="NOT_SUPPORTED",
                retryable=False,
                provider="sagemaker",
            )

    async def chat_completion_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Generate streaming chat completion.

        Note: Streaming is not typically supported by SageMaker endpoints.
        This method raises an error.

        Args:
            messages: List of message dicts
            temperature: Optional temperature
            max_tokens: Optional max tokens

        Yields:
            str: Text chunks

        Raises:
            ModelProviderError: Streaming not supported
        """
        raise ModelProviderError(
            message="Streaming not supported by SageMaker endpoints",
            code="NOT_SUPPORTED",
            retryable=False,
            provider="sagemaker",
        )

    async def structured_output(
        self,
        messages: list[dict[str, str]],
        schema: type[T],
        temperature: float | None = None,
    ) -> T:
        """Generate structured output.

        Note: Structured output depends on the specific model deployed.
        This method attempts to parse the response as JSON.

        Args:
            messages: List of message dicts
            schema: Pydantic model class
            temperature: Optional temperature

        Returns:
            Parsed Pydantic model instance

        Raises:
            ModelProviderError: If generation or parsing fails
        """
        try:
            # Get completion
            response_text = await self.chat_completion(
                messages=messages,
                temperature=temperature,
            )

            # Parse JSON response
            result = schema.model_validate_json(response_text)

            return result

        except Exception as e:
            raise ModelProviderError(
                message=f"Failed to generate structured output: {e}",
                code="PARSE_ERROR",
                retryable=False,
                provider="sagemaker",
            )

    async def generate_image(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> bytes:
        """Generate image using SageMaker endpoint.

        This is a convenience method for image generation models.

        Args:
            prompt: Text description of the image
            **kwargs: Additional parameters for the model

        Returns:
            Generated image bytes

        Raises:
            ModelProviderError: If generation fails
        """
        log = logger.bind(
            provider="sagemaker",
            endpoint=self.endpoint_name,
        )
        log.info("generate_image_start")

        try:
            # Build payload
            payload = {
                "prompt": prompt,
                **kwargs,
            }

            result = await self.invoke_endpoint(payload)

            # Extract image data (format depends on model)
            if isinstance(result, dict):
                if "image" in result:
                    # Assume base64 encoded
                    import base64
                    return base64.b64decode(result["image"])
                elif "image_bytes" in result:
                    return result["image_bytes"]

            raise ModelProviderError(
                message="No image data in response",
                code="INVALID_RESPONSE",
                retryable=False,
                provider="sagemaker",
            )

        except Exception as e:
            if isinstance(e, ModelProviderError):
                raise
            raise self._handle_error(e)

    async def generate_video(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate video using SageMaker endpoint.

        This is a convenience method for video generation models.

        Args:
            prompt: Text description of the video
            **kwargs: Additional parameters for the model

        Returns:
            Video generation result (format depends on model)

        Raises:
            ModelProviderError: If generation fails
        """
        log = logger.bind(
            provider="sagemaker",
            endpoint=self.endpoint_name,
        )
        log.info("generate_video_start")

        try:
            # Build payload
            payload = {
                "prompt": prompt,
                **kwargs,
            }

            result = await self.invoke_endpoint(payload)

            log.info("generate_video_complete")

            return result

        except Exception as e:
            if isinstance(e, ModelProviderError):
                raise
            raise self._handle_error(e)

    def _handle_aws_error(self, error: Exception) -> ModelProviderError:
        """Convert AWS error to ModelProviderError.

        Args:
            error: AWS exception

        Returns:
            ModelProviderError with appropriate code and retryable flag
        """
        error_str = str(error).lower()
        error_code = None

        if isinstance(error, ClientError):
            error_code = error.response.get("Error", {}).get("Code", "")

        # Check for throttling
        if error_code in ["ThrottlingException", "TooManyRequestsException"]:
            return ModelProviderError(
                message=str(error),
                code="RATE_LIMIT",
                retryable=True,
                provider="sagemaker",
            )

        # Check for model errors
        if error_code in ["ModelError", "ModelNotReadyException"]:
            return ModelProviderError(
                message=str(error),
                code="MODEL_ERROR",
                retryable=True,
                provider="sagemaker",
            )

        # Check for service errors
        if error_code in ["ServiceUnavailableException", "InternalFailure"]:
            return ModelProviderError(
                message=str(error),
                code="SERVICE_ERROR",
                retryable=True,
                provider="sagemaker",
            )

        # Check for validation errors
        if error_code in ["ValidationError", "InvalidRequestException"]:
            return ModelProviderError(
                message=str(error),
                code="VALIDATION_ERROR",
                retryable=False,
                provider="sagemaker",
            )

        # Default to retryable error
        return ModelProviderError(
            message=str(error),
            code=error_code or "AWS_ERROR",
            retryable=True,
            provider="sagemaker",
        )
