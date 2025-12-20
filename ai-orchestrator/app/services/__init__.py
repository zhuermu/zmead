"""Services package for AI Orchestrator."""

from app.services.gemini_client import (
    GeminiAPIError,
    GeminiClient,
    GeminiError,
    GeminiQuotaExceededError,
    GeminiRateLimitError,
    GeminiTimeoutError,
)
from app.services.mcp_client import (
    InsufficientCreditsError,
    MCPClient,
    MCPConnectionError,
    MCPError,
    MCPTimeoutError,
    MCPToolError,
)
from app.services.model_provider import ModelProvider, ModelProviderError
from app.services.gemini_provider import GeminiProvider
from app.services.bedrock_provider import BedrockProvider
from app.services.sagemaker_provider import SageMakerProvider
from app.services.model_factory import (
    ModelProviderFactory,
    ModelConfig,
    ConversationalModelConfig,
    GenerationModelConfig,
)

__all__ = [
    # MCP Client
    "MCPClient",
    "MCPError",
    "MCPConnectionError",
    "MCPToolError",
    "MCPTimeoutError",
    "InsufficientCreditsError",
    # Gemini Client (legacy)
    "GeminiClient",
    "GeminiError",
    "GeminiAPIError",
    "GeminiRateLimitError",
    "GeminiQuotaExceededError",
    "GeminiTimeoutError",
    # Model Providers
    "ModelProvider",
    "ModelProviderError",
    "GeminiProvider",
    "BedrockProvider",
    "SageMakerProvider",
    # Model Factory
    "ModelProviderFactory",
    "ModelConfig",
    "ConversationalModelConfig",
    "GenerationModelConfig",
]
