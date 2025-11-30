"""
Update handler for Landing Page module.

Provides functionality to parse field paths and apply updates to landing page structures.
Integrates with validators for image URL and HEX color validation.

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
"""

import copy
import structlog
from datetime import datetime, timezone
from typing import Any

from ..models import LandingPageContent
from ..utils.validators import (
    FieldValidator,
    ValidationError,
    InvalidImageURLError,
    InvalidColorError,
)

logger = structlog.get_logger(__name__)


class UpdateError(Exception):
    """Base exception for update operations."""

    def __init__(self, message: str, code: str = "UPDATE_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class InvalidFieldPathError(UpdateError):
    """Raised when a field path is invalid or doesn't exist."""

    def __init__(self, field_path: str, reason: str = "Field path not found"):
        super().__init__(
            message=f"Invalid field path '{field_path}': {reason}",
            code="INVALID_FIELD_PATH",
        )
        self.field_path = field_path


class UpdateHandler:
    """Handler for landing page updates.

    Parses field paths (e.g., "hero.headline") and applies updates
    to landing page structures while preserving unchanged fields.
    Integrates with FieldValidator for image URL and HEX color validation.

    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
    """

    # Valid top-level fields that can be updated
    UPDATABLE_FIELDS = {
        "hero": {"headline", "subheadline", "image", "cta_text"},
        "features": None,  # List - special handling
        "reviews": None,  # List - special handling
        "faq": None,  # List - special handling
        "cta": {"text", "url"},
        "theme": {"primary_color", "secondary_color", "font_family"},
        "pixel_id": None,  # Direct field
        "language": None,  # Direct field
    }

    def __init__(self, validate_values: bool = True):
        """Initialize the update handler.

        Args:
            validate_values: Whether to validate field values (default: True)
        """
        self.validate_values = validate_values
        self.field_validator = FieldValidator() if validate_values else None
        logger.info(
            "update_handler_initialized",
            validate_values=validate_values,
        )

    def parse_field_path(self, field_path: str) -> list[str]:
        """Parse a dot-notation field path into components.

        Args:
            field_path: Dot-notation path (e.g., "hero.headline", "features.0.title")

        Returns:
            List of path components

        Raises:
            InvalidFieldPathError: If the path is empty or malformed

        Requirements: 3.1
        """
        if not field_path or not field_path.strip():
            raise InvalidFieldPathError(field_path, "Field path cannot be empty")

        parts = field_path.strip().split(".")

        # Validate each part is non-empty
        for i, part in enumerate(parts):
            if not part:
                raise InvalidFieldPathError(
                    field_path, f"Empty component at position {i}"
                )

        return parts

    def get_nested_value(self, data: dict, field_path: str) -> Any:
        """Get a value from nested dictionary using dot notation.

        Args:
            data: The dictionary to traverse
            field_path: Dot-notation path (e.g., "hero.headline")

        Returns:
            The value at the specified path

        Raises:
            InvalidFieldPathError: If the path doesn't exist

        Requirements: 3.1
        """
        parts = self.parse_field_path(field_path)
        current = data

        for i, part in enumerate(parts):
            try:
                if isinstance(current, dict):
                    if part not in current:
                        raise InvalidFieldPathError(
                            field_path,
                            f"Key '{part}' not found at position {i}",
                        )
                    current = current[part]
                elif isinstance(current, list):
                    try:
                        index = int(part)
                        if index < 0 or index >= len(current):
                            raise InvalidFieldPathError(
                                field_path,
                                f"Index {index} out of range at position {i}",
                            )
                        current = current[index]
                    except ValueError:
                        raise InvalidFieldPathError(
                            field_path,
                            f"Expected integer index, got '{part}' at position {i}",
                        )
                else:
                    raise InvalidFieldPathError(
                        field_path,
                        f"Cannot traverse into {type(current).__name__} at position {i}",
                    )
            except (KeyError, IndexError, TypeError) as e:
                raise InvalidFieldPathError(field_path, str(e))

        return current

    def set_nested_value(
        self, data: dict, field_path: str, value: Any
    ) -> dict:
        """Set a value in nested dictionary using dot notation.

        Creates a deep copy of the data and modifies the copy,
        preserving the original structure.

        Args:
            data: The dictionary to modify (will be deep copied)
            field_path: Dot-notation path (e.g., "hero.headline")
            value: The value to set

        Returns:
            Modified copy of the dictionary

        Raises:
            InvalidFieldPathError: If the path is invalid

        Requirements: 3.1, 3.2
        """
        parts = self.parse_field_path(field_path)

        # Deep copy to preserve original
        result = copy.deepcopy(data)
        current = result

        # Navigate to parent of target
        for i, part in enumerate(parts[:-1]):
            if isinstance(current, dict):
                if part not in current:
                    raise InvalidFieldPathError(
                        field_path,
                        f"Key '{part}' not found at position {i}",
                    )
                current = current[part]
            elif isinstance(current, list):
                try:
                    index = int(part)
                    if index < 0 or index >= len(current):
                        raise InvalidFieldPathError(
                            field_path,
                            f"Index {index} out of range at position {i}",
                        )
                    current = current[index]
                except ValueError:
                    raise InvalidFieldPathError(
                        field_path,
                        f"Expected integer index, got '{part}' at position {i}",
                    )
            else:
                raise InvalidFieldPathError(
                    field_path,
                    f"Cannot traverse into {type(current).__name__} at position {i}",
                )

        # Set the final value
        final_key = parts[-1]
        if isinstance(current, dict):
            current[final_key] = value
        elif isinstance(current, list):
            try:
                index = int(final_key)
                if index < 0 or index >= len(current):
                    raise InvalidFieldPathError(
                        field_path,
                        f"Index {index} out of range for final key",
                    )
                current[index] = value
            except ValueError:
                raise InvalidFieldPathError(
                    field_path,
                    f"Expected integer index, got '{final_key}' for list",
                )
        else:
            raise InvalidFieldPathError(
                field_path,
                f"Cannot set value on {type(current).__name__}",
            )

        return result

    def validate_field_path(self, field_path: str) -> bool:
        """Validate that a field path is allowed for updates.

        Args:
            field_path: Dot-notation path to validate

        Returns:
            True if the path is valid for updates

        Raises:
            InvalidFieldPathError: If the path is not allowed

        Requirements: 3.1
        """
        parts = self.parse_field_path(field_path)

        if not parts:
            raise InvalidFieldPathError(field_path, "Empty field path")

        top_level = parts[0]

        if top_level not in self.UPDATABLE_FIELDS:
            raise InvalidFieldPathError(
                field_path,
                f"Field '{top_level}' is not updatable. "
                f"Allowed fields: {list(self.UPDATABLE_FIELDS.keys())}",
            )

        # Check nested fields for known structures
        allowed_subfields = self.UPDATABLE_FIELDS.get(top_level)
        if allowed_subfields is not None and len(parts) > 1:
            subfield = parts[1]
            # For list fields (features, reviews, faq), allow index access
            if top_level in ("features", "reviews", "faq"):
                # Allow numeric indices
                try:
                    int(subfield)
                except ValueError:
                    raise InvalidFieldPathError(
                        field_path,
                        f"Expected numeric index for '{top_level}', got '{subfield}'",
                    )
            elif subfield not in allowed_subfields:
                raise InvalidFieldPathError(
                    field_path,
                    f"Field '{subfield}' is not updatable in '{top_level}'. "
                    f"Allowed: {allowed_subfields}",
                )

        return True

    def validate_value(self, field_path: str, value: Any) -> None:
        """Validate a field value using the FieldValidator.

        Args:
            field_path: Dot-notation field path
            value: Value to validate

        Raises:
            InvalidFieldPathError: If validation fails

        Requirements: 3.3, 3.4
        """
        if not self.validate_values or self.field_validator is None:
            return

        try:
            self.field_validator.validate(field_path, value)
        except (InvalidImageURLError, InvalidColorError, ValidationError) as e:
            raise InvalidFieldPathError(
                field_path,
                f"Validation failed: {e.message}",
            )

    def apply_updates(
        self, landing_page_data: dict, updates: dict[str, Any]
    ) -> tuple[dict, list[str]]:
        """Apply multiple updates to landing page data.

        Validates field paths and values before applying updates.
        For image fields, validates URL format.
        For color fields, validates HEX format.

        Args:
            landing_page_data: Current landing page data as dictionary
            updates: Dictionary of field_path -> new_value

        Returns:
            Tuple of (updated_data, list_of_updated_fields)

        Raises:
            InvalidFieldPathError: If any field path is invalid or validation fails

        Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
        """
        if not updates:
            logger.info("apply_updates_no_changes")
            return landing_page_data, []

        updated_data = copy.deepcopy(landing_page_data)
        updated_fields = []

        for field_path, value in updates.items():
            logger.debug(
                "applying_update",
                field_path=field_path,
                value_type=type(value).__name__,
            )

            # Validate the field path is allowed
            self.validate_field_path(field_path)

            # Validate the field value (image URL, HEX color, etc.)
            self.validate_value(field_path, value)

            # Apply the update
            updated_data = self.set_nested_value(updated_data, field_path, value)
            updated_fields.append(field_path)

            logger.debug("update_applied", field_path=field_path)

        # Update the updated_at timestamp
        updated_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        logger.info(
            "apply_updates_complete",
            updated_count=len(updated_fields),
            fields=updated_fields,
        )

        return updated_data, updated_fields

    def apply_updates_to_model(
        self, landing_page: LandingPageContent, updates: dict[str, Any]
    ) -> tuple[LandingPageContent, list[str]]:
        """Apply updates to a LandingPageContent model.

        Converts the model to dict, applies updates, and converts back.

        Args:
            landing_page: Current landing page model
            updates: Dictionary of field_path -> new_value

        Returns:
            Tuple of (updated_model, list_of_updated_fields)

        Requirements: 3.1, 3.2
        """
        # Convert model to dict for manipulation
        landing_page_data = landing_page.model_dump(mode="json")

        # Apply updates
        updated_data, updated_fields = self.apply_updates(
            landing_page_data, updates
        )

        # Convert back to model
        updated_model = LandingPageContent(**updated_data)

        return updated_model, updated_fields
