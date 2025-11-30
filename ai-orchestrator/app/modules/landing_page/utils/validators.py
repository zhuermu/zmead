"""
Input validators for Landing Page module.

Provides validation functions for:
- Image URL format and accessibility
- HEX color format
- Field value validation

Requirements: 3.3, 3.4
"""

import re
import structlog
from typing import Any
from urllib.parse import urlparse

logger = structlog.get_logger(__name__)


class ValidationError(Exception):
    """Base exception for validation errors."""

    def __init__(self, message: str, field: str, code: str = "VALIDATION_ERROR"):
        self.message = message
        self.field = field
        self.code = code
        super().__init__(message)


class InvalidImageURLError(ValidationError):
    """Raised when an image URL is invalid."""

    def __init__(self, url: str, reason: str = "Invalid image URL"):
        super().__init__(
            message=f"Invalid image URL '{url}': {reason}",
            field="image",
            code="INVALID_IMAGE_URL",
        )
        self.url = url


class InvalidColorError(ValidationError):
    """Raised when a color format is invalid."""

    def __init__(self, color: str, reason: str = "Invalid color format"):
        super().__init__(
            message=f"Invalid color '{color}': {reason}",
            field="color",
            code="INVALID_COLOR_FORMAT",
        )
        self.color = color


# HEX color pattern: # followed by 6 hex characters
HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")

# Valid image extensions
VALID_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp"}

# Valid URL schemes
VALID_URL_SCHEMES = {"http", "https"}


def validate_hex_color(color: str) -> bool:
    """Validate that a string is a valid HEX color.

    Args:
        color: Color string to validate (e.g., "#FF6B6B")

    Returns:
        True if valid

    Raises:
        InvalidColorError: If the color format is invalid

    Requirements: 3.4

    Examples:
        >>> validate_hex_color("#FF6B6B")
        True
        >>> validate_hex_color("#4ECDC4")
        True
        >>> validate_hex_color("FF6B6B")  # Missing #
        Raises InvalidColorError
        >>> validate_hex_color("#FFF")  # Too short
        Raises InvalidColorError
    """
    if not color:
        raise InvalidColorError(color, "Color cannot be empty")

    if not isinstance(color, str):
        raise InvalidColorError(str(color), "Color must be a string")

    if not HEX_COLOR_PATTERN.match(color):
        raise InvalidColorError(
            color,
            "Color must be in HEX format (#RRGGBB). "
            "Example: #FF6B6B, #4ECDC4",
        )

    logger.debug("hex_color_validated", color=color)
    return True


def validate_image_url(url: str, check_extension: bool = True) -> bool:
    """Validate that a string is a valid image URL.

    Validates:
    - URL format (scheme, netloc)
    - URL scheme (http/https)
    - Image file extension (optional)

    Args:
        url: URL string to validate
        check_extension: Whether to validate image file extension

    Returns:
        True if valid

    Raises:
        InvalidImageURLError: If the URL format is invalid

    Requirements: 3.3

    Examples:
        >>> validate_image_url("https://example.com/image.jpg")
        True
        >>> validate_image_url("https://cdn.example.com/path/to/image.png")
        True
        >>> validate_image_url("not-a-url")
        Raises InvalidImageURLError
        >>> validate_image_url("ftp://example.com/image.jpg")
        Raises InvalidImageURLError
    """
    if not url:
        raise InvalidImageURLError(url, "URL cannot be empty")

    if not isinstance(url, str):
        raise InvalidImageURLError(str(url), "URL must be a string")

    try:
        parsed = urlparse(url)
    except Exception as e:
        raise InvalidImageURLError(url, f"Failed to parse URL: {str(e)}")

    # Check scheme
    if not parsed.scheme:
        raise InvalidImageURLError(url, "URL must include a scheme (http or https)")

    if parsed.scheme.lower() not in VALID_URL_SCHEMES:
        raise InvalidImageURLError(
            url,
            f"URL scheme must be http or https, got '{parsed.scheme}'",
        )

    # Check netloc (domain)
    if not parsed.netloc:
        raise InvalidImageURLError(url, "URL must include a domain")

    # Check extension (optional)
    if check_extension:
        path = parsed.path.lower()
        # Allow URLs without extension (CDN URLs often don't have extensions)
        if path and "." in path:
            ext = "." + path.rsplit(".", 1)[-1]
            # Only validate if there's a clear extension
            if len(ext) <= 5 and ext not in VALID_IMAGE_EXTENSIONS:
                # Log warning but don't fail - many CDN URLs don't have extensions
                logger.warning(
                    "image_url_unusual_extension",
                    url=url,
                    extension=ext,
                )

    logger.debug("image_url_validated", url=url)
    return True


def validate_url(url: str) -> bool:
    """Validate that a string is a valid URL.

    Args:
        url: URL string to validate

    Returns:
        True if valid

    Raises:
        ValidationError: If the URL format is invalid

    Examples:
        >>> validate_url("https://example.com/page")
        True
        >>> validate_url("not-a-url")
        Raises ValidationError
    """
    if not url:
        raise ValidationError("URL cannot be empty", field="url", code="INVALID_URL")

    if not isinstance(url, str):
        raise ValidationError("URL must be a string", field="url", code="INVALID_URL")

    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValidationError(
            f"Failed to parse URL: {str(e)}", field="url", code="INVALID_URL"
        )

    if not parsed.scheme:
        raise ValidationError(
            "URL must include a scheme (http or https)",
            field="url",
            code="INVALID_URL",
        )

    if parsed.scheme.lower() not in VALID_URL_SCHEMES:
        raise ValidationError(
            f"URL scheme must be http or https, got '{parsed.scheme}'",
            field="url",
            code="INVALID_URL",
        )

    if not parsed.netloc:
        raise ValidationError(
            "URL must include a domain", field="url", code="INVALID_URL"
        )

    logger.debug("url_validated", url=url)
    return True


def validate_field_value(field_path: str, value: Any) -> bool:
    """Validate a field value based on its path.

    Automatically selects the appropriate validator based on the field path.

    Args:
        field_path: Dot-notation field path (e.g., "hero.image", "theme.primary_color")
        value: Value to validate

    Returns:
        True if valid

    Raises:
        ValidationError: If validation fails

    Requirements: 3.3, 3.4
    """
    # Determine validator based on field path
    parts = field_path.split(".")

    # Image fields
    if "image" in parts or field_path.endswith(".image"):
        validate_image_url(str(value))
        return True

    # Color fields
    if "color" in parts[-1].lower() or field_path.endswith("_color"):
        validate_hex_color(str(value))
        return True

    # URL fields (cta.url, etc.)
    if parts[-1] == "url":
        validate_url(str(value))
        return True

    # No specific validation needed for other fields
    logger.debug("field_value_no_validation", field_path=field_path)
    return True


class FieldValidator:
    """Validator class for landing page field updates.

    Provides comprehensive validation for landing page field updates,
    including type checking and format validation.

    Requirements: 3.3, 3.4
    """

    # Field type definitions
    FIELD_TYPES = {
        "hero.headline": str,
        "hero.subheadline": str,
        "hero.image": str,  # URL
        "hero.cta_text": str,
        "cta.text": str,
        "cta.url": str,  # URL
        "theme.primary_color": str,  # HEX color
        "theme.secondary_color": str,  # HEX color
        "theme.font_family": str,
        "pixel_id": str,
        "language": str,
    }

    # Fields requiring specific validation
    IMAGE_FIELDS = {"hero.image"}
    COLOR_FIELDS = {"theme.primary_color", "theme.secondary_color"}
    URL_FIELDS = {"cta.url"}

    def __init__(self):
        """Initialize the field validator."""
        logger.info("field_validator_initialized")

    def validate(self, field_path: str, value: Any) -> bool:
        """Validate a field value.

        Args:
            field_path: Dot-notation field path
            value: Value to validate

        Returns:
            True if valid

        Raises:
            ValidationError: If validation fails

        Requirements: 3.3, 3.4
        """
        # Check for image fields
        if field_path in self.IMAGE_FIELDS or field_path.endswith(".image"):
            validate_image_url(str(value))
            return True

        # Check for color fields
        if field_path in self.COLOR_FIELDS or "_color" in field_path:
            validate_hex_color(str(value))
            return True

        # Check for URL fields
        if field_path in self.URL_FIELDS or field_path.endswith(".url"):
            validate_url(str(value))
            return True

        # Type checking for known fields
        expected_type = self.FIELD_TYPES.get(field_path)
        if expected_type and not isinstance(value, expected_type):
            raise ValidationError(
                f"Expected {expected_type.__name__} for '{field_path}', "
                f"got {type(value).__name__}",
                field=field_path,
                code="INVALID_TYPE",
            )

        logger.debug("field_validated", field_path=field_path)
        return True

    def validate_updates(self, updates: dict[str, Any]) -> dict[str, list[str]]:
        """Validate multiple field updates.

        Args:
            updates: Dictionary of field_path -> value

        Returns:
            Dictionary with "valid" and "errors" lists

        Requirements: 3.3, 3.4
        """
        valid_fields = []
        errors = []

        for field_path, value in updates.items():
            try:
                self.validate(field_path, value)
                valid_fields.append(field_path)
            except ValidationError as e:
                errors.append(f"{field_path}: {e.message}")

        return {
            "valid": valid_fields,
            "errors": errors,
        }

