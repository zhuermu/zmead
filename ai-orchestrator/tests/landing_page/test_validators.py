"""
Tests for Landing Page validators.

Tests the input validation functions for:
- HEX color format validation
- Image URL format validation
- Field value validation

Requirements: 3.3, 3.4
"""

import pytest

from app.modules.landing_page.utils.validators import (
    validate_hex_color,
    validate_image_url,
    validate_url,
    validate_field_value,
    FieldValidator,
    ValidationError,
    InvalidColorError,
    InvalidImageURLError,
)


class TestHexColorValidation:
    """Tests for HEX color validation."""

    def test_valid_hex_colors(self):
        """Test that valid HEX colors pass validation."""
        valid_colors = [
            "#FF6B6B",
            "#4ECDC4",
            "#000000",
            "#FFFFFF",
            "#ffffff",
            "#123456",
            "#abcdef",
            "#ABCDEF",
        ]
        for color in valid_colors:
            assert validate_hex_color(color) is True

    def test_invalid_hex_color_missing_hash(self):
        """Test that colors without # are rejected."""
        with pytest.raises(InvalidColorError) as exc_info:
            validate_hex_color("FF6B6B")
        assert "HEX format" in exc_info.value.message

    def test_invalid_hex_color_too_short(self):
        """Test that short colors are rejected."""
        with pytest.raises(InvalidColorError):
            validate_hex_color("#FFF")

    def test_invalid_hex_color_too_long(self):
        """Test that long colors are rejected."""
        with pytest.raises(InvalidColorError):
            validate_hex_color("#FF6B6B00")

    def test_invalid_hex_color_invalid_chars(self):
        """Test that invalid characters are rejected."""
        with pytest.raises(InvalidColorError):
            validate_hex_color("#GGGGGG")

    def test_invalid_hex_color_empty(self):
        """Test that empty string is rejected."""
        with pytest.raises(InvalidColorError):
            validate_hex_color("")

    def test_invalid_hex_color_none(self):
        """Test that None is rejected."""
        with pytest.raises(InvalidColorError):
            validate_hex_color(None)


class TestImageURLValidation:
    """Tests for image URL validation."""

    def test_valid_image_urls(self):
        """Test that valid image URLs pass validation."""
        valid_urls = [
            "https://example.com/image.jpg",
            "https://cdn.example.com/path/to/image.png",
            "http://example.com/image.webp",
            "https://example.com/image.gif",
            "https://example.com/image.svg",
            "https://cdn.cloudfront.net/images/product.jpeg",
        ]
        for url in valid_urls:
            assert validate_image_url(url) is True

    def test_valid_image_url_without_extension(self):
        """Test that CDN URLs without extension pass validation."""
        # Many CDN URLs don't have file extensions
        assert validate_image_url("https://cdn.example.com/abc123") is True

    def test_invalid_image_url_no_scheme(self):
        """Test that URLs without scheme are rejected."""
        with pytest.raises(InvalidImageURLError):
            validate_image_url("example.com/image.jpg")

    def test_invalid_image_url_ftp_scheme(self):
        """Test that FTP URLs are rejected."""
        with pytest.raises(InvalidImageURLError) as exc_info:
            validate_image_url("ftp://example.com/image.jpg")
        assert "http or https" in exc_info.value.message

    def test_invalid_image_url_no_domain(self):
        """Test that URLs without domain are rejected."""
        with pytest.raises(InvalidImageURLError):
            validate_image_url("https:///image.jpg")

    def test_invalid_image_url_not_url(self):
        """Test that non-URLs are rejected."""
        with pytest.raises(InvalidImageURLError):
            validate_image_url("not-a-url")

    def test_invalid_image_url_empty(self):
        """Test that empty string is rejected."""
        with pytest.raises(InvalidImageURLError):
            validate_image_url("")


class TestURLValidation:
    """Tests for general URL validation."""

    def test_valid_urls(self):
        """Test that valid URLs pass validation."""
        valid_urls = [
            "https://example.com",
            "https://example.com/page",
            "http://example.com/path/to/page",
            "https://shop.example.com/checkout?id=123",
        ]
        for url in valid_urls:
            assert validate_url(url) is True

    def test_invalid_url_no_scheme(self):
        """Test that URLs without scheme are rejected."""
        with pytest.raises(ValidationError):
            validate_url("example.com/page")

    def test_invalid_url_empty(self):
        """Test that empty string is rejected."""
        with pytest.raises(ValidationError):
            validate_url("")


class TestFieldValidator:
    """Tests for FieldValidator class."""

    def test_validate_image_field(self):
        """Test validation of image fields."""
        validator = FieldValidator()
        assert validator.validate("hero.image", "https://example.com/image.jpg") is True

    def test_validate_color_field(self):
        """Test validation of color fields."""
        validator = FieldValidator()
        assert validator.validate("theme.primary_color", "#FF6B6B") is True
        assert validator.validate("theme.secondary_color", "#4ECDC4") is True

    def test_validate_url_field(self):
        """Test validation of URL fields."""
        validator = FieldValidator()
        assert validator.validate("cta.url", "https://example.com/checkout") is True

    def test_validate_text_field(self):
        """Test validation of text fields."""
        validator = FieldValidator()
        assert validator.validate("hero.headline", "Amazing Product") is True
        assert validator.validate("hero.subheadline", "Best value for money") is True

    def test_invalid_image_field(self):
        """Test that invalid image URLs are rejected."""
        validator = FieldValidator()
        with pytest.raises(ValidationError):
            validator.validate("hero.image", "not-a-url")

    def test_invalid_color_field(self):
        """Test that invalid colors are rejected."""
        validator = FieldValidator()
        with pytest.raises(ValidationError):
            validator.validate("theme.primary_color", "red")

    def test_validate_updates(self):
        """Test batch validation of updates."""
        validator = FieldValidator()
        updates = {
            "hero.headline": "New Headline",
            "hero.image": "https://example.com/image.jpg",
            "theme.primary_color": "#FF6B6B",
        }
        result = validator.validate_updates(updates)
        assert len(result["valid"]) == 3
        assert len(result["errors"]) == 0

    def test_validate_updates_with_errors(self):
        """Test batch validation with some invalid values."""
        validator = FieldValidator()
        updates = {
            "hero.headline": "New Headline",
            "hero.image": "not-a-url",  # Invalid
            "theme.primary_color": "red",  # Invalid
        }
        result = validator.validate_updates(updates)
        assert len(result["valid"]) == 1
        assert len(result["errors"]) == 2


class TestValidateFieldValue:
    """Tests for validate_field_value function."""

    def test_validate_image_field_path(self):
        """Test that image field paths trigger image validation."""
        assert validate_field_value("hero.image", "https://example.com/image.jpg") is True

    def test_validate_color_field_path(self):
        """Test that color field paths trigger color validation."""
        assert validate_field_value("theme.primary_color", "#FF6B6B") is True

    def test_validate_url_field_path(self):
        """Test that URL field paths trigger URL validation."""
        assert validate_field_value("cta.url", "https://example.com") is True

    def test_validate_other_field_path(self):
        """Test that other field paths pass without specific validation."""
        assert validate_field_value("hero.headline", "Any text") is True
        assert validate_field_value("unknown.field", 12345) is True

