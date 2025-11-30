"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
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

    # Google Cloud Storage
    gcs_project_id: str = Field(default="")
    gcs_credentials_path: str = Field(default="")  # Path to service account JSON
    gcs_bucket_creatives: str = "aae-creatives"
    gcs_bucket_landing_pages: str = "aae-landing-pages"
    gcs_bucket_exports: str = "aae-exports"
    gcs_cdn_domain: str = Field(default="")  # Custom domain or Cloud CDN domain

    # OAuth - Google
    google_client_id: str = Field(default="")
    google_client_secret: str = Field(default="")
    google_redirect_uri: str = "http://localhost:3000/api/auth/callback/google"

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

    # Development - Disable authentication for local development
    disable_auth: bool = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
