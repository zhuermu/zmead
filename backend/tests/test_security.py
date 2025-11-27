"""Tests for security module."""

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    token_encryption,
    verify_password,
)


def test_password_hashing():
    """Test password hashing and verification."""
    password = "test_password_123"
    hashed = get_password_hash(password)

    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong_password", hashed)


def test_access_token_creation():
    """Test JWT access token creation."""
    data = {"sub": "user123", "email": "test@example.com"}
    token = create_access_token(data)

    assert token is not None
    assert isinstance(token, str)

    decoded = decode_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user123"
    assert decoded["email"] == "test@example.com"
    assert decoded["type"] == "access"


def test_refresh_token_creation():
    """Test JWT refresh token creation."""
    data = {"sub": "user123"}
    token = create_refresh_token(data)

    assert token is not None
    decoded = decode_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user123"
    assert decoded["type"] == "refresh"


def test_invalid_token_decode():
    """Test that invalid tokens return None."""
    result = decode_token("invalid_token")
    assert result is None


def test_token_encryption_round_trip():
    """Test OAuth token encryption and decryption."""
    original = "ya29.a0AfH6SMBx..."
    encrypted = token_encryption.encrypt(original)

    assert encrypted != original

    decrypted = token_encryption.decrypt(encrypted)
    assert decrypted == original
