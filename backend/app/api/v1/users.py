"""User management API endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.notification import NotificationPreferencesUpdate
from app.schemas.user import (
    ModelPreferencesResponse,
    ModelPreferencesUpdateRequest,
    NotificationPreferences,
    UserDeleteRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user: CurrentUser) -> UserResponse:
    """Get current authenticated user information."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        avatar_url=current_user.avatar_url,
        oauth_provider=current_user.oauth_provider,
        gifted_credits=current_user.gifted_credits,
        purchased_credits=current_user.purchased_credits,
        total_credits=current_user.total_credits,
        language=current_user.language,
        timezone=current_user.timezone,
        notification_preferences=current_user.notification_preferences,
        conversational_provider=current_user.conversational_provider,
        conversational_model=current_user.conversational_model,
        image_generation_provider=getattr(current_user, 'image_generation_provider', 'gemini'),
        image_generation_model=getattr(current_user, 'image_generation_model', 'gemini-2.5-flash-image'),
        video_generation_provider=getattr(current_user, 'video_generation_provider', 'sagemaker'),
        video_generation_model=getattr(current_user, 'video_generation_model', 'wan2.2'),
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        last_login_at=current_user.last_login_at,
    )


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    update_data: UserUpdateRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> UserResponse:
    """Update current user profile."""
    user_service = UserService(db)
    updated_user = await user_service.update_user(current_user, update_data)

    return UserResponse(
        id=updated_user.id,
        email=updated_user.email,
        display_name=updated_user.display_name,
        avatar_url=updated_user.avatar_url,
        oauth_provider=updated_user.oauth_provider,
        gifted_credits=updated_user.gifted_credits,
        purchased_credits=updated_user.purchased_credits,
        total_credits=updated_user.total_credits,
        language=updated_user.language,
        timezone=updated_user.timezone,
        notification_preferences=updated_user.notification_preferences,
        conversational_provider=updated_user.conversational_provider,
        conversational_model=updated_user.conversational_model,
        image_generation_provider=getattr(updated_user, 'image_generation_provider', 'gemini'),
        image_generation_model=getattr(updated_user, 'image_generation_model', 'gemini-2.5-flash-image'),
        video_generation_provider=getattr(updated_user, 'video_generation_provider', 'sagemaker'),
        video_generation_model=getattr(updated_user, 'video_generation_model', 'wan2.2'),
        is_active=updated_user.is_active,
        created_at=updated_user.created_at,
        updated_at=updated_user.updated_at,
        last_login_at=updated_user.last_login_at,
    )


@router.delete("/me")
async def delete_current_user(
    delete_request: UserDeleteRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """
    Permanently delete current user account and all associated data.
    
    Requires confirmation by sending {"confirmation": "DELETE"} in the request body.
    
    This operation:
    - Deletes all S3 files (creatives, landing pages, exports)
    - Deletes all database records (ad accounts, campaigns, etc.)
    - Sends confirmation email
    - Cannot be undone
    
    Returns:
        dict with deletion summary
    """
    if delete_request.confirmation != "DELETE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation must be 'DELETE' to delete account",
        )

    user_service = UserService(db)
    
    try:
        deletion_summary = await user_service.hard_delete_user(current_user)
        return {
            "message": "Account successfully deleted",
            "summary": deletion_summary
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete account: {str(e)}"
        )


@router.get("/me/notification-preferences", response_model=NotificationPreferences)
async def get_notification_preferences(
    current_user: CurrentUser,
) -> NotificationPreferences:
    """Get current user's notification preferences."""
    prefs = current_user.notification_preferences or {}
    return NotificationPreferences(
        email_enabled=prefs.get("email_enabled", True),
        in_app_enabled=prefs.get("in_app_enabled", True),
        credit_warning_threshold=prefs.get("credit_warning_threshold", 50),
        credit_critical_threshold=prefs.get("credit_critical_threshold", 10),
    )


@router.put("/me/notification-preferences", response_model=NotificationPreferences)
async def update_notification_preferences(
    preferences: NotificationPreferencesUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> NotificationPreferences:
    """
    Update current user's notification preferences.
    
    Note: Urgent notifications (ad rejected, token expired, credit depleted)
    will always be sent regardless of preferences.
    """
    user_service = UserService(db)

    # Get current preferences
    current_prefs = current_user.notification_preferences or {}

    # Update with new values
    if preferences.email_enabled is not None:
        current_prefs["email_enabled"] = preferences.email_enabled
    if preferences.in_app_enabled is not None:
        current_prefs["in_app_enabled"] = preferences.in_app_enabled
    if preferences.credit_warning_threshold is not None:
        current_prefs["credit_warning_threshold"] = preferences.credit_warning_threshold
    if preferences.credit_critical_threshold is not None:
        current_prefs["credit_critical_threshold"] = preferences.credit_critical_threshold
    if preferences.category_preferences is not None:
        current_prefs["category_preferences"] = preferences.category_preferences

    # Update user
    update_data = UserUpdateRequest(notification_preferences=current_prefs)
    updated_user = await user_service.update_user(current_user, update_data)

    prefs = updated_user.notification_preferences or {}
    return NotificationPreferences(
        email_enabled=prefs.get("email_enabled", True),
        in_app_enabled=prefs.get("in_app_enabled", True),
        credit_warning_threshold=prefs.get("credit_warning_threshold", 50),
        credit_critical_threshold=prefs.get("credit_critical_threshold", 10),
    )


@router.post("/me/avatar-upload-url")
async def get_avatar_upload_url(
    current_user: CurrentUser,
) -> dict:
    """Get presigned URL for avatar upload."""
    from app.core.storage import get_presigned_upload_url
    import uuid
    
    # Generate unique filename
    file_key = f"avatars/{current_user.id}/{uuid.uuid4()}.jpg"
    
    # Get presigned URL (15 minutes expiry)
    upload_url = get_presigned_upload_url(file_key, expires_in=900)
    
    # Generate the file URL
    from app.core.config import settings
    file_url = f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{file_key}"
    
    return {
        "upload_url": upload_url,
        "file_url": file_url,
    }


@router.post("/me/export")
async def request_data_export(
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """
    Request data export for current user.
    Returns a job ID that can be used to check export status.
    """
    user_service = UserService(db)
    job_id = await user_service.request_data_export(current_user)
    
    return {
        "job_id": job_id,
        "message": "Data export request submitted. This may take a few minutes.",
    }


@router.get("/me/export/{job_id}")
async def get_export_status(
    job_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """
    Check the status of a data export job.
    Returns status and download URL when ready.
    """
    user_service = UserService(db)
    export_status = await user_service.get_export_status(current_user, job_id)
    
    return export_status


@router.get("/me/model-preferences", response_model=ModelPreferencesResponse)
async def get_model_preferences(
    current_user: CurrentUser,
) -> ModelPreferencesResponse:
    """Get current user's AI model preferences for all model types."""
    return ModelPreferencesResponse(
        conversational_provider=current_user.conversational_provider,
        conversational_model=current_user.conversational_model,
        image_generation_provider=getattr(current_user, 'image_generation_provider', 'gemini'),
        image_generation_model=getattr(current_user, 'image_generation_model', 'gemini-2.5-flash-image'),
        video_generation_provider=getattr(current_user, 'video_generation_provider', 'sagemaker'),
        video_generation_model=getattr(current_user, 'video_generation_model', 'wan2.2'),
    )


@router.put("/me/model-preferences", response_model=ModelPreferencesResponse)
async def update_model_preferences(
    preferences: ModelPreferencesUpdateRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> ModelPreferencesResponse:
    """
    Update current user's AI model preferences.
    
    This controls which AI model provider and specific model is used for:
    - Conversational AI interactions
    - Image generation
    - Video generation
    
    All fields are optional - only provided fields will be updated.
    """
    # Valid models for each category
    valid_conversational_models = {
        "gemini": ["gemini-2.5-flash", "gemini-2.5-pro"],
        "bedrock": [
            "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
            "qwen.qwen3-235b-a22b-2507-v1:0",
            "us.amazon.nova-2-lite-v1:0"
        ]
    }
    
    valid_image_models = {
        "gemini": ["gemini-2.5-flash-image", "gemini-2.0-flash-exp", "imagen-3.0-generate-002"],
        "sagemaker": ["qwen-image"],
        "bedrock": [
            "amazon.nova-canvas-v1:0",
            "stability.sd3-5-large-v1:0",  # Latest SD3.5 Large (replaces deprecated sd3-large-v1:0)
            "amazon.titan-image-generator-v2:0"
        ]
    }
    
    valid_video_models = {
        "gemini": ["gemini-veo-3.1"],
        "sagemaker": ["wan2.2"],
        "bedrock": ["amazon.nova-reel-v1:1", "luma.ray-v2:0"]
    }
    
    # Validate conversational model if provided
    if preferences.conversational_provider and preferences.conversational_model:
        if preferences.conversational_model not in valid_conversational_models.get(preferences.conversational_provider, []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid conversational model '{preferences.conversational_model}' for provider '{preferences.conversational_provider}'"
            )
    
    # Validate image generation model if provided
    if preferences.image_generation_provider and preferences.image_generation_model:
        if preferences.image_generation_model not in valid_image_models.get(preferences.image_generation_provider, []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid image model '{preferences.image_generation_model}' for provider '{preferences.image_generation_provider}'"
            )
    
    # Validate video generation model if provided
    if preferences.video_generation_provider and preferences.video_generation_model:
        if preferences.video_generation_model not in valid_video_models.get(preferences.video_generation_provider, []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid video model '{preferences.video_generation_model}' for provider '{preferences.video_generation_provider}'"
            )
    
    user_service = UserService(db)
    
    # Build update data with only provided fields
    update_data = UserUpdateRequest(
        conversational_provider=preferences.conversational_provider,
        conversational_model=preferences.conversational_model,
        image_generation_provider=preferences.image_generation_provider,
        image_generation_model=preferences.image_generation_model,
        video_generation_provider=preferences.video_generation_provider,
        video_generation_model=preferences.video_generation_model,
    )
    updated_user = await user_service.update_user(current_user, update_data)
    
    return ModelPreferencesResponse(
        conversational_provider=updated_user.conversational_provider,
        conversational_model=updated_user.conversational_model,
        image_generation_provider=getattr(updated_user, 'image_generation_provider', 'gemini'),
        image_generation_model=getattr(updated_user, 'image_generation_model', 'gemini-2.5-flash-image'),
        video_generation_provider=getattr(updated_user, 'video_generation_provider', 'sagemaker'),
        video_generation_model=getattr(updated_user, 'video_generation_model', 'wan2.2'),
    )
