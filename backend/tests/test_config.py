"""Tests for configuration module."""

from app.core.config import Settings, get_settings


def test_settings_defaults():
    """Test that settings have correct default values when explicitly set."""
    settings = Settings(
        _env_file=None,  # Ignore .env file for this test
        debug=False,
    )
    assert settings.app_name == "AAE Web Platform"
    assert settings.app_version == "0.1.0"
    assert settings.debug is False
    assert settings.environment == "development"
    assert settings.api_v1_prefix == "/api/v1"


def test_database_url_construction():
    """Test database URL is constructed correctly."""
    settings = Settings(
        mysql_host="testhost",
        mysql_port=3307,
        mysql_user="testuser",
        mysql_password="testpass",
        mysql_database="testdb",
    )
    assert "testhost:3307" in settings.database_url
    assert "testuser:testpass" in settings.database_url
    assert "testdb" in settings.database_url


def test_redis_url_construction():
    """Test Redis URL is constructed correctly."""
    settings = Settings(
        redis_host="redishost",
        redis_port=6380,
        redis_db=2,
    )
    assert "redishost:6380/2" in settings.redis_url


def test_redis_url_with_password():
    """Test Redis URL includes password when set."""
    settings = Settings(
        redis_host="redishost",
        redis_port=6379,
        redis_password="secret",
        redis_db=0,
    )
    assert ":secret@" in settings.redis_url


def test_get_settings_cached():
    """Test that get_settings returns cached instance."""
    settings1 = get_settings()
    settings2 = get_settings()
    assert settings1 is settings2
