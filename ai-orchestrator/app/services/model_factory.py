"""Model provider factory for configuration-based selection.

This module provides a factory for creating model providers based on
configuration, enabling easy switching between different AI providers.
"""

from typing import Literal

import structlog
from pydantic import BaseModel, Field

from app.services.bedrock_provider import BedrockProvider
from app.services.gemini_provider import GeminiProvider
from app.services.model_provider import ModelProvider
from app.services.sagemaker_provider import SageMakerProvider

logger = structlog.get_logger(__name__)


class ModelConfig(BaseModel):
    """Configuration for model provider selection.

    This configuration determines which AI provider and model to use
    for different types of requests.
    """

    # Provider selection
    provider: Literal["gemini", "bedrock", "sagemaker"] = Field(
        default="gemini",
        description="AI provider to use",
    )

    # Provider-specific settings
    # Gemini
    gemini_api_key: str | None = None
    gemini_chat_model: str | None = None
    gemini_fast_model: str | None = None

    # AWS Bedrock
    bedrock_region: str = "us-west-2"
    bedrock_model_id: str | None = None
    bedrock_model_name: str | None = None  # Short name like "claude-4.5-sonnet"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_session_token: str | None = None

    # AWS SageMaker
    sagemaker_endpoint_name: str | None = None
    sagemaker_region: str = "us-west-2"

    # Common settings
    max_retries: int = 3
    timeout: float = 60.0


class ConversationalModelConfig(BaseModel):
    """Configuration for conversational AI models.

    Defines available models for user selection.
    """

    # Gemini models
    gemini_models: dict[str, str] = Field(
        default={
            "gemini-2.5-flash": "gemini-2.5-flash",
            "gemini-2.5-pro": "gemini-2.5-pro",
            "gemini-3-pro": "gemini-3-pro-preview",
        },
        description="Available Gemini models",
    )

    # Bedrock models
    bedrock_models: dict[str, str] = Field(
        default={
            "claude-4.5-sonnet": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
            "qwen3": "qwen.qwen3-235b-a22b-2507-v1:0",
            "nova-2-lite": "us.amazon.nova-lite-v1:0",
        },
        description="Available Bedrock models",
    )


class GenerationModelConfig(BaseModel):
    """Configuration for creative generation models.

    These models are fixed and not user-selectable.
    """

    # Image generation
    image_provider: Literal["gemini", "sagemaker"] = "gemini"
    image_endpoint: str | None = None  # For SageMaker

    # Video generation
    video_provider: Literal["gemini", "sagemaker"] = "gemini"
    video_endpoint: str | None = None  # For SageMaker


class ModelProviderFactory:
    """Factory for creating model providers based on configuration.

    Example:
        factory = ModelProviderFactory()

        # Create Gemini provider
        provider = factory.create_provider(ModelConfig(
            provider="gemini",
            gemini_api_key="..."
        ))

        # Create Bedrock provider
        provider = factory.create_provider(ModelConfig(
            provider="bedrock",
            bedrock_model_name="claude-4.5-sonnet"
        ))
    """

    @staticmethod
    def create_provider(config: ModelConfig) -> ModelProvider:
        """Create a model provider based on configuration.

        Args:
            config: Model configuration

        Returns:
            Configured ModelProvider instance

        Raises:
            ValueError: If provider is not supported or configuration is invalid
        """
        logger.info(
            "creating_model_provider",
            provider=config.provider,
        )

        if config.provider == "gemini":
            return GeminiProvider(
                api_key=config.gemini_api_key,
                chat_model=config.gemini_chat_model,
                fast_model=config.gemini_fast_model,
                max_retries=config.max_retries,
                timeout=config.timeout,
            )

        elif config.provider == "bedrock":
            return BedrockProvider(
                region_name=config.bedrock_region,
                model_id=config.bedrock_model_id,
                model_name=config.bedrock_model_name,
                aws_access_key_id=config.aws_access_key_id,
                aws_secret_access_key=config.aws_secret_access_key,
                aws_session_token=config.aws_session_token,
                max_retries=config.max_retries,
                timeout=config.timeout,
            )

        elif config.provider == "sagemaker":
            if not config.sagemaker_endpoint_name:
                raise ValueError("sagemaker_endpoint_name is required for SageMaker provider")

            return SageMakerProvider(
                endpoint_name=config.sagemaker_endpoint_name,
                region_name=config.sagemaker_region,
                aws_access_key_id=config.aws_access_key_id,
                aws_secret_access_key=config.aws_secret_access_key,
                aws_session_token=config.aws_session_token,
                max_retries=config.max_retries,
                timeout=config.timeout,
            )

        else:
            raise ValueError(f"Unsupported provider: {config.provider}")

    @staticmethod
    def create_from_user_preference(
        provider: str,
        model: str,
        conversational_config: ConversationalModelConfig | None = None,
    ) -> ModelProvider:
        """Create a provider based on user's model preference.

        Args:
            provider: Provider name ("gemini" or "bedrock")
            model: Model identifier
            conversational_config: Optional conversational model configuration

        Returns:
            Configured ModelProvider instance

        Raises:
            ValueError: If provider/model combination is invalid
        """
        logger.info(
            "creating_provider_from_user_preference",
            provider=provider,
            model=model,
        )

        if conversational_config is None:
            conversational_config = ConversationalModelConfig()

        if provider == "gemini":
            # Validate model is available
            if model not in conversational_config.gemini_models:
                raise ValueError(f"Invalid Gemini model: {model}")

            return ModelProviderFactory.create_provider(
                ModelConfig(
                    provider="gemini",
                    gemini_chat_model=conversational_config.gemini_models[model],
                )
            )

        elif provider == "bedrock":
            # Validate model is available
            if model not in conversational_config.bedrock_models:
                raise ValueError(f"Invalid Bedrock model: {model}")

            return ModelProviderFactory.create_provider(
                ModelConfig(
                    provider="bedrock",
                    bedrock_model_id=conversational_config.bedrock_models[model],
                )
            )

        else:
            raise ValueError(f"Unsupported provider for conversational AI: {provider}")

    @staticmethod
    def get_available_models() -> dict[str, list[str]]:
        """Get list of available models by provider.

        Returns:
            Dictionary mapping provider names to lists of model identifiers
        """
        config = ConversationalModelConfig()

        return {
            "gemini": list(config.gemini_models.keys()),
            "bedrock": list(config.bedrock_models.keys()),
        }

    @staticmethod
    def get_default_provider() -> ModelProvider:
        """Get the default model provider (Gemini).

        Returns:
            Default ModelProvider instance
        """
        return ModelProviderFactory.create_provider(
            ModelConfig(provider="gemini")
        )
