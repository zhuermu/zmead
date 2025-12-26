"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "AAE Web Platform"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # API
    api_v1_prefix: str = "/api/v1"

    # Security
    secret_key: str = Field(default="change-me-in-production")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Database - MySQL
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "aae_user"
    mysql_password: str = Field(default="")
    mysql_database: str = "aae_platform"

    @computed_field
    @property
    def database_url(self) -> str:
        """Construct MySQL database URL."""
        return (
            f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    @computed_field
    @property
    def database_url_sync(self) -> str:
        """Construct synchronous MySQL database URL for migrations."""
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )


    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = Field(default="")
    redis_db: int = 0

    @computed_field
    @property
    def redis_url(self) -> str:
        """Construct Redis URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # AWS Configuration
    aws_region: str = Field(default="us-west-2")
    aws_access_key_id: str = Field(default="")
    aws_secret_access_key: str = Field(default="")
    aws_session_token: str = Field(default="")  # Optional for temporary credentials
    
    # AWS S3 Configuration
    s3_bucket_creatives: str = "aae-creatives"
    s3_bucket_landing_pages: str = "aae-landing-pages"
    s3_bucket_exports: str = "aae-exports"
    s3_bucket_uploads: str = "aae-user-uploads"
    cloudfront_domain: str = Field(default="landing.zmead.com")  # CloudFront CDN domain for landing pages
    
    # AWS Bedrock Configuration
    bedrock_region: str = Field(default="us-west-2")
    bedrock_default_model: str = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
    bedrock_temperature: float = 0.7
    bedrock_max_tokens: int = 4096
    
    # AWS SageMaker Configuration
    sagemaker_region: str = Field(default="us-west-2")
    sagemaker_qwen_image_endpoint: str = Field(default="")
    sagemaker_wan_video_endpoint: str = Field(default="")

    # OAuth - Google
    google_client_id: str = Field(default="")
    google_client_secret: str = Field(default="")
    google_redirect_uri: str = "http://localhost:3000/api/auth/callback/google"

    # Google Ads API
    google_ads_developer_token: str = Field(default="")
    google_ads_login_customer_id: str = Field(default="")  # Optional MCC account ID

    # OAuth - Facebook
    facebook_client_id: str = Field(default="")
    facebook_client_secret: str = Field(default="")
    facebook_redirect_uri: str = "http://localhost:3000/api/auth/callback/facebook"

    # Stripe
    stripe_api_key: str = Field(default="")
    stripe_webhook_secret: str = Field(default="")

    # Celery
    celery_broker_url: str = Field(default="redis://localhost:6379/1")
    celery_result_backend: str = Field(default="redis://localhost:6379/2")

    # Encryption key for OAuth tokens
    token_encryption_key: str = Field(default="change-me-32-bytes-key-here!!")

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Email
    email_provider: Literal["console", "ses"] = "console"
    email_from_address: str = "noreply@aae.com"
    email_from_name: str = "AAE - Automated Ad Engine"

    # Frontend URL (for email links)
    frontend_url: str = "http://localhost:3000"

    # AI Orchestrator URL
    ai_orchestrator_url: str = "http://localhost:8001"
    ai_orchestrator_timeout: int = 60  # seconds
    ai_orchestrator_service_token: str = Field(default="")

    # Gemini API
    gemini_api_key: str = Field(default="")

    # Development - Disable authentication for local development
    disable_auth: bool = False

    # Beta Access - Super Admin emails (comma-separated)
    super_admin_emails: str = Field(default="")

    @computed_field
    @property
    def super_admin_list(self) -> list[str]:
        """Parse comma-separated super admin emails."""
        if not self.super_admin_emails:
            return []
        return [email.strip() for email in self.super_admin_emails.split(",") if email.strip()]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
