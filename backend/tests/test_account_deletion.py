"""Tests for account deletion service."""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.user import User
from app.services.account_deletion import AccountDeletionService, AccountDeletionError


@pytest.fixture
def mock_db():
    """Create mock database session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.delete = AsyncMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def test_user():
    """Create test user."""
    user = User(
        id=123,
        email="test@example.com",
        display_name="Test User",
        oauth_provider="google",
        oauth_id="google_123",
        gifted_credits=Decimal("100.00"),
        purchased_credits=Decimal("50.00"),
    )
    return user


@pytest.fixture
def deletion_service(mock_db):
    """Create account deletion service with mocked dependencies."""
    with patch('app.services.account_deletion.GCSStorage') as mock_storage, \
         patch('app.services.account_deletion.EmailService') as mock_email:
        
        service = AccountDeletionService(mock_db)
        service.creatives_storage = MagicMock()
        service.landing_pages_storage = MagicMock()
        service.exports_storage = MagicMock()
        service.email_service = AsyncMock()
        
        return service


@pytest.mark.asyncio
async def test_extract_s3_key_from_s3_url(deletion_service):
    """Test extracting S3 key from s3:// URL."""
    url = "s3://bucket-name/path/to/file.jpg"
    key = deletion_service._extract_s3_key(url)
    assert key == "path/to/file.jpg"


@pytest.mark.asyncio
async def test_extract_s3_key_from_https_url(deletion_service):
    """Test extracting S3 key from HTTPS URL."""
    url = "https://bucket.s3.ap-southeast-1.amazonaws.com/path/to/file.jpg"
    key = deletion_service._extract_s3_key(url)
    assert key == "path/to/file.jpg"


@pytest.mark.asyncio
async def test_extract_s3_key_from_cloudfront_url(deletion_service):
    """Test extracting S3 key from CloudFront URL."""
    url = "https://cdn.example.com/path/to/file.jpg"
    key = deletion_service._extract_s3_key(url)
    assert key == "path/to/file.jpg"


@pytest.mark.asyncio
async def test_delete_user_account_success(deletion_service, test_user, mock_db):
    """Test successful account deletion."""
    # Mock database queries to return empty results
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    
    # Mock S3 operations
    deletion_service.creatives_storage.delete_file = MagicMock()
    deletion_service.landing_pages_storage.delete_file = MagicMock()
    deletion_service._delete_files_by_prefix = MagicMock(return_value=0)
    
    # Mock email sending
    deletion_service._send_deletion_confirmation_email = AsyncMock()
    
    # Execute deletion
    result = await deletion_service.delete_user_account(test_user)
    
    # Verify result
    assert result["status"] == "completed"
    assert result["user_id"] == 123
    assert result["email"] == "test@example.com"
    assert "started_at" in result
    assert "completed_at" in result
    
    # Verify database operations
    mock_db.delete.assert_called_once_with(test_user)
    mock_db.flush.assert_called()
    mock_db.commit.assert_called_once()
    
    # Verify email was sent
    deletion_service._send_deletion_confirmation_email.assert_called_once_with(test_user)


@pytest.mark.asyncio
async def test_delete_user_account_rollback_on_error(deletion_service, test_user, mock_db):
    """Test that account deletion rolls back on error."""
    # Mock database to raise error during deletion
    mock_db.delete.side_effect = Exception("Database error")
    
    # Mock database queries to return empty results
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    
    # Mock S3 operations
    deletion_service._delete_files_by_prefix = MagicMock(return_value=0)
    
    # Execute deletion and expect error
    with pytest.raises(AccountDeletionError) as exc_info:
        await deletion_service.delete_user_account(test_user)
    
    assert "Failed to delete account" in str(exc_info.value)
    
    # Verify rollback was called
    mock_db.rollback.assert_called_once()
    
    # Verify commit was not called
    mock_db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_delete_files_by_prefix(deletion_service):
    """Test deleting files by prefix."""
    # Mock S3 client
    mock_storage = MagicMock()
    mock_storage.bucket = "test-bucket"
    mock_storage.client.list_objects_v2.return_value = {
        'Contents': [
            {'Key': 'exports/user_123_file1.zip'},
            {'Key': 'exports/user_123_file2.zip'},
        ]
    }
    mock_storage.client.delete_objects.return_value = {}
    
    # Execute deletion
    count = deletion_service._delete_files_by_prefix(mock_storage, "exports/user_123_")
    
    # Verify
    assert count == 2
    mock_storage.client.list_objects_v2.assert_called_once_with(
        Bucket="test-bucket",
        Prefix="exports/user_123_"
    )
    mock_storage.client.delete_objects.assert_called_once()


@pytest.mark.asyncio
async def test_delete_files_by_prefix_no_files(deletion_service):
    """Test deleting files by prefix when no files exist."""
    # Mock S3 client with no files
    mock_storage = MagicMock()
    mock_storage.bucket = "test-bucket"
    mock_storage.client.list_objects_v2.return_value = {}
    
    # Execute deletion
    count = deletion_service._delete_files_by_prefix(mock_storage, "exports/user_123_")
    
    # Verify
    assert count == 0
    mock_storage.client.delete_objects.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
