"""Configuration management using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """AI Orchestrator application settings.

    Settings are loaded from environment variables and .env file.
    Required settings will raise an error if not provided.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application settings
    app_name: str = Field(default="AI Orchestrator", description="Application name")
    environment: Literal["development", "staging", "production"] = Field(
        default="development", description="Environment name"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )

    # Gemini API configuration (Optional - only needed if using Gemini models)
    # Reference: https://ai.google.dev/gemini-api/docs/gemini-3
    gemini_api_key: str = Field(default="", description="Google Gemini API key (optional - only for Gemini models)")

    # Main chat model - Gemini 3 Pro for complex reasoning and function calling
    gemini_model_chat: str = Field(
        default="gemini-3-pro-preview",
        description="Gemini 3 Pro for chat, reasoning, and function calling",
    )

    # Fast model for quick responses
    gemini_model_fast: str = Field(
        default="gemini-2.5-flash",
        description="Gemini 2.5 Flash for fast responses",
    )

    # Image generation models
    # Reference: https://ai.google.dev/gemini-api/docs/image-generation
    gemini_model_imagen: str = Field(
        default="gemini-2.5-flash-image",
        description="Gemini 2.5 Flash Image for fast image generation",
    )
    gemini_model_imagen_pro: str = Field(
        default="gemini-3-pro-image-preview",
        description="Gemini 3 Pro Image for high-quality image generation (up to 4K)",
    )

    # Video generation models (Veo 3.1)
    # Reference: https://ai.google.dev/gemini-api/docs/video
    gemini_model_veo: str = Field(
        default="veo-3.1-generate-preview",
        description="Veo 3.1 for high-quality video generation",
    )
    gemini_model_veo_fast: str = Field(
        default="veo-3.1-fast-generate-preview",
        description="Veo 3.1 Fast for quick video generation",
    )

    # Google Cloud Storage configuration
    gcs_project_id: str = Field(
        default="",
        description="GCS project ID",
    )
    gcs_credentials_path: str | None = Field(
        default=None,
        description="Path to GCS service account credentials JSON",
    )
    gcs_bucket_name: str = Field(
        default="zmead-creatives",
        description="GCS bucket for storing creatives",
    )
    gcs_bucket_uploads: str = Field(
        default="aae-user-uploads",
        description="GCS bucket for all file uploads (permanent storage)",
    )
    gcs_signed_url_expiration: int = Field(
        default=60,
        description="Signed URL expiration time in minutes",
    )

    # AWS Configuration
    aws_region: str = Field(default="us-west-2", description="AWS region")
    aws_access_key_id: str = Field(default="", description="AWS access key ID (optional if using IAM roles)")
    aws_secret_access_key: str = Field(default="", description="AWS secret access key (optional if using IAM roles)")
    aws_session_token: str = Field(default="", description="AWS session token for temporary credentials")

    # AWS S3 Configuration
    s3_bucket_creatives: str = Field(default="aae-creatives", description="S3 bucket for creatives")
    s3_bucket_landing_pages: str = Field(default="aae-landing-pages", description="S3 bucket for landing pages")
    s3_bucket_exports: str = Field(default="aae-exports", description="S3 bucket for exports")
    s3_bucket_uploads: str = Field(default="aae-user-uploads", description="S3 bucket for user uploads")
    cloudfront_domain: str = Field(default="", description="CloudFront CDN domain")

    # AWS Bedrock Configuration
    bedrock_region: str = Field(default="us-west-2", description="AWS Bedrock region")
    bedrock_default_model: str = Field(
        default="global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        description="Default Bedrock model ID"
    )
    bedrock_temperature: float = Field(default=0.7, description="Bedrock model temperature")
    bedrock_max_tokens: int = Field(default=4096, description="Bedrock model max tokens")

    # AWS SageMaker Configuration
    sagemaker_region: str = Field(default="us-west-2", description="AWS SageMaker region")
    sagemaker_qwen_image_endpoint: str = Field(default="", description="SageMaker Qwen-Image endpoint name")
    sagemaker_wan_video_endpoint: str = Field(default="", description="SageMaker Wan2.2 video endpoint name")

    # Web Platform integration
    web_platform_url: str = Field(
        default="http://localhost:8000", description="Web Platform backend URL"
    )
    web_platform_service_token: str = Field(
        ..., description="Service token for Web Platform authentication (required)"
    )

    # Redis configuration
    redis_url: str = Field(default="redis://localhost:6379/3", description="Redis connection URL")
    redis_max_connections: int = Field(default=10, description="Maximum Redis connections in pool")
    redis_socket_timeout: float = Field(default=5.0, description="Redis socket timeout in seconds")
    redis_socket_connect_timeout: float = Field(
        default=5.0, description="Redis socket connect timeout in seconds"
    )

    # Performance settings
    max_concurrent_requests: int = Field(default=100, description="Maximum concurrent requests")
    request_timeout: int = Field(default=60, description="Request timeout in seconds")

    @field_validator("web_platform_service_token")
    @classmethod
    def validate_service_token(cls, v: str) -> str:
        """Validate service token is not empty or placeholder."""
        if not v or v == "your_service_token_here":
            raise ValueError(
                "WEB_PLATFORM_SERVICE_TOKEN is required. "
                'Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )
        return v

    @computed_field
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @computed_field
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    @computed_field
    @property
    def mcp_endpoint(self) -> str:
        """Get the MCP execute endpoint URL."""
        return f"{self.web_platform_url}/api/v1/mcp/execute"

    @computed_field
    @property
    def mcp_tools_endpoint(self) -> str:
        """Get the MCP tools list endpoint URL."""
        return f"{self.web_platform_url}/api/v1/mcp/tools"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Uses lru_cache to ensure settings are only loaded once.

    Returns:
        Settings: Application settings instance

    Raises:
        ValidationError: If required settings are missing or invalid
    """
    return Settings()
