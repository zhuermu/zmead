"""User schemas for API requests and responses."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class UserResponse(BaseModel):
    """User response schema."""

    id: int
    email: EmailStr
    display_name: str
    avatar_url: str | None = None
    oauth_provider: str
    gifted_credits: Decimal
    purchased_credits: Decimal
    total_credits: Decimal
    language: str
    timezone: str
    notification_preferences: dict
    # Conversational AI preferences
    conversational_provider: str
    conversational_model: str
    # Image generation preferences
    image_generation_provider: str = "gemini"
    image_generation_model: str = "gemini-2.5-flash-image"
    # Video generation preferences
    video_generation_provider: str = "sagemaker"
    video_generation_model: str = "wan2.2"
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None
    last_login_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    """User profile update request."""

    display_name: str | None = Field(None, min_length=1, max_length=255)
    avatar_url: str | None = Field(None, max_length=512)
    language: str | None = Field(None, min_length=2, max_length=10)
    timezone: str | None = Field(None, max_length=50)
    notification_preferences: dict | None = None
    # Conversational AI preferences
    conversational_provider: str | None = Field(None, max_length=50)
    conversational_model: str | None = Field(None, max_length=100)
    # Image generation preferences
    image_generation_provider: str | None = Field(None, max_length=50)
    image_generation_model: str | None = Field(None, max_length=100)
    # Video generation preferences
    video_generation_provider: str | None = Field(None, max_length=50)
    video_generation_model: str | None = Field(None, max_length=100)


class UserDeleteRequest(BaseModel):
    """User account deletion request."""

    confirmation: str = Field(
        ...,
        description="Must be 'DELETE' to confirm account deletion"
    )


class NotificationPreferences(BaseModel):
    """User notification preferences."""

    email_enabled: bool = True
    in_app_enabled: bool = True
    credit_warning_threshold: int = Field(default=50, ge=0)
    credit_critical_threshold: int = Field(default=10, ge=0)


class ModelPreferencesResponse(BaseModel):
    """User AI model preferences response."""

    # Conversational AI preferences
    conversational_provider: str
    conversational_model: str
    # Image generation preferences
    image_generation_provider: str = "gemini"
    image_generation_model: str = "gemini-2.5-flash-image"
    # Video generation preferences
    video_generation_provider: str = "sagemaker"
    video_generation_model: str = "wan2.2"
    
    # Available providers for each category
    available_conversational_providers: dict = Field(
        default={
            "gemini": {
                "name": "Google Gemini",
                "models": {
                    "gemini-2.5-flash": "Gemini 2.5 Flash (Fast)",
                    "gemini-2.5-pro": "Gemini 2.5 Pro (Advanced)"
                }
            },
            "bedrock": {
                "name": "AWS Bedrock",
                "models": {
                    "global.anthropic.claude-sonnet-4-5-20250929-v1:0": "Claude 4.5 Sonnet",
                    "qwen.qwen3-235b-a22b-2507-v1:0": "Qwen3 235B",
                    "us.amazon.nova-2-lite-v1:0": "Amazon Nova 2 Lite"
                }
            }
        }
    )
    
    available_image_providers: dict = Field(
        default={
            "gemini": {
                "name": "Google Gemini",
                "models": {
                    "gemini-2.5-flash-image": "Gemini 2.5 Flash (Image Generation)",
                    "gemini-2.0-flash-exp": "Gemini 2.0 Flash Experimental",
                    "imagen-3.0-generate-002": "Imagen 3.0 (High Quality)"
                }
            },
            "sagemaker": {
                "name": "AWS SageMaker",
                "models": {
                    "qwen-image": "Qwen-Image (Open Source)"
                }
            },
            "bedrock": {
                "name": "AWS Bedrock",
                "models": {
                    "amazon.nova-canvas-v1:0": "Amazon Nova Canvas",
                    "stability.sd3-5-large-v1:0": "Stable Diffusion 3.5 Large",
                    "amazon.titan-image-generator-v2:0": "Amazon Titan Image Generator v2"
                }
            }
        }
    )
    
    available_video_providers: dict = Field(
        default={
            "gemini": {
                "name": "Google Gemini",
                "models": {
                    "gemini-veo-3.1": "Gemini Veo 3.1 (Video Generation)"
                }
            },
            "sagemaker": {
                "name": "AWS SageMaker",
                "models": {
                    "wan2.2": "Wan2.2 (Open Source)"
                }
            },
            "bedrock": {
                "name": "AWS Bedrock",
                "models": {
                    "amazon.nova-reel-v1:1": "Amazon Nova Reel v1.1",
                    "luma.ray-v2:0": "Luma Ray v2"
                }
            }
        }
    )


class ModelPreferencesUpdateRequest(BaseModel):
    """Update user AI model preferences."""

    # Conversational AI (optional)
    conversational_provider: Literal["gemini", "bedrock"] | None = Field(
        None, description="AI model provider for conversations"
    )
    conversational_model: str | None = Field(
        None, min_length=1, max_length=100, description="Specific conversational model ID"
    )
    
    # Image generation (optional)
    image_generation_provider: Literal["gemini", "sagemaker", "bedrock"] | None = Field(
        None, description="AI model provider for image generation"
    )
    image_generation_model: str | None = Field(
        None, min_length=1, max_length=100, description="Specific image generation model ID"
    )
    
    # Video generation (optional)
    video_generation_provider: Literal["gemini", "sagemaker", "bedrock"] | None = Field(
        None, description="AI model provider for video generation"
    )
    video_generation_model: str | None = Field(
        None, min_length=1, max_length=100, description="Specific video generation model ID"
    )
