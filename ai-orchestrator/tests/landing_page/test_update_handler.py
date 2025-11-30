"""
Tests for Landing Page update handler.

Tests the update handler functionality for:
- Field path parsing
- Update application
- Validation integration
- Response format

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
"""

import pytest
from datetime import datetime

from app.modules.landing_page.managers.update_handler import (
    UpdateHandler,
    InvalidFieldPathError,
)


class TestFieldPathParsing:
    """Tests for field path parsing."""

    def test_parse_simple_path(self):
        """Test parsing a simple field path."""
        handler = UpdateHandler(validate_values=False)
        parts = handler.parse_field_path("hero.headline")
        assert parts == ["hero", "headline"]

    def test_parse_nested_path(self):
        """Test parsing a nested field path."""
        handler = UpdateHandler(validate_values=False)
        parts = handler.parse_field_path("theme.primary_color")
        assert parts == ["theme", "primary_color"]

    def test_parse_array_index_path(self):
        """Test parsing a path with array index."""
        handler = UpdateHandler(validate_values=False)
        parts = handler.parse_field_path("features.0.title")
        assert parts == ["features", "0", "title"]

    def test_parse_empty_path_raises_error(self):
        """Test that empty path raises error."""
        handler = UpdateHandler(validate_values=False)
        with pytest.raises(InvalidFieldPathError):
            handler.parse_field_path("")

    def test_parse_whitespace_path_raises_error(self):
        """Test that whitespace-only path raises error."""
        handler = UpdateHandler(validate_values=False)
        with pytest.raises(InvalidFieldPathError):
            handler.parse_field_path("   ")


class TestFieldPathValidation:
    """Tests for field path validation."""

    def test_validate_hero_fields(self):
        """Test validation of hero section fields."""
        handler = UpdateHandler(validate_values=False)
        assert handler.validate_field_path("hero.headline") is True
        assert handler.validate_field_path("hero.subheadline") is True
        assert handler.validate_field_path("hero.image") is True
        assert handler.validate_field_path("hero.cta_text") is True

    def test_validate_theme_fields(self):
        """Test validation of theme fields."""
        handler = UpdateHandler(validate_values=False)
        assert handler.validate_field_path("theme.primary_color") is True
        assert handler.validate_field_path("theme.secondary_color") is True
        assert handler.validate_field_path("theme.font_family") is True

    def test_validate_cta_fields(self):
        """Test validation of CTA fields."""
        handler = UpdateHandler(validate_values=False)
        assert handler.validate_field_path("cta.text") is True
        assert handler.validate_field_path("cta.url") is True

    def test_validate_direct_fields(self):
        """Test validation of direct fields."""
        handler = UpdateHandler(validate_values=False)
        assert handler.validate_field_path("pixel_id") is True
        assert handler.validate_field_path("language") is True

    def test_validate_list_fields_with_index(self):
        """Test validation of list fields with numeric index."""
        handler = UpdateHandler(validate_values=False)
        assert handler.validate_field_path("features.0") is True
        assert handler.validate_field_path("reviews.1") is True
        assert handler.validate_field_path("faq.2") is True

    def test_invalid_top_level_field(self):
        """Test that invalid top-level fields are rejected."""
        handler = UpdateHandler(validate_values=False)
        with pytest.raises(InvalidFieldPathError) as exc_info:
            handler.validate_field_path("invalid_field")
        assert "not updatable" in exc_info.value.message

    def test_invalid_nested_field(self):
        """Test that invalid nested fields are rejected."""
        handler = UpdateHandler(validate_values=False)
        with pytest.raises(InvalidFieldPathError) as exc_info:
            handler.validate_field_path("hero.invalid_field")
        assert "not updatable" in exc_info.value.message


class TestNestedValueOperations:
    """Tests for getting and setting nested values."""

    def test_get_nested_value(self):
        """Test getting a nested value."""
        handler = UpdateHandler(validate_values=False)
        data = {
            "hero": {
                "headline": "Original Headline",
                "subheadline": "Original Subheadline",
            }
        }
        value = handler.get_nested_value(data, "hero.headline")
        assert value == "Original Headline"

    def test_get_nested_value_from_list(self):
        """Test getting a value from a list."""
        handler = UpdateHandler(validate_values=False)
        data = {
            "features": [
                {"title": "Feature 1"},
                {"title": "Feature 2"},
            ]
        }
        value = handler.get_nested_value(data, "features.0.title")
        assert value == "Feature 1"

    def test_get_nested_value_invalid_path(self):
        """Test that invalid path raises error."""
        handler = UpdateHandler(validate_values=False)
        data = {"hero": {"headline": "Test"}}
        with pytest.raises(InvalidFieldPathError):
            handler.get_nested_value(data, "hero.invalid")

    def test_set_nested_value(self):
        """Test setting a nested value."""
        handler = UpdateHandler(validate_values=False)
        data = {
            "hero": {
                "headline": "Original Headline",
            }
        }
        result = handler.set_nested_value(data, "hero.headline", "New Headline")
        assert result["hero"]["headline"] == "New Headline"
        # Original should be unchanged
        assert data["hero"]["headline"] == "Original Headline"

    def test_set_nested_value_in_list(self):
        """Test setting a value in a list."""
        handler = UpdateHandler(validate_values=False)
        data = {
            "features": [
                {"title": "Feature 1"},
                {"title": "Feature 2"},
            ]
        }
        result = handler.set_nested_value(data, "features.0.title", "Updated Feature")
        assert result["features"][0]["title"] == "Updated Feature"
        assert result["features"][1]["title"] == "Feature 2"


class TestApplyUpdates:
    """Tests for applying updates."""

    def test_apply_single_update(self):
        """Test applying a single update."""
        handler = UpdateHandler(validate_values=False)
        data = {
            "hero": {
                "headline": "Original",
                "subheadline": "Original Sub",
            }
        }
        updates = {"hero.headline": "New Headline"}
        
        updated_data, updated_fields = handler.apply_updates(data, updates)
        
        assert updated_data["hero"]["headline"] == "New Headline"
        assert updated_data["hero"]["subheadline"] == "Original Sub"
        assert updated_fields == ["hero.headline"]
        assert "updated_at" in updated_data

    def test_apply_multiple_updates(self):
        """Test applying multiple updates."""
        handler = UpdateHandler(validate_values=False)
        data = {
            "hero": {
                "headline": "Original",
                "subheadline": "Original Sub",
            },
            "theme": {
                "primary_color": "#000000",
            }
        }
        updates = {
            "hero.headline": "New Headline",
            "hero.subheadline": "New Subheadline",
            "theme.primary_color": "#FF6B6B",
        }
        
        updated_data, updated_fields = handler.apply_updates(data, updates)
        
        assert updated_data["hero"]["headline"] == "New Headline"
        assert updated_data["hero"]["subheadline"] == "New Subheadline"
        assert updated_data["theme"]["primary_color"] == "#FF6B6B"
        assert len(updated_fields) == 3

    def test_apply_empty_updates(self):
        """Test applying empty updates."""
        handler = UpdateHandler(validate_values=False)
        data = {"hero": {"headline": "Original"}}
        
        updated_data, updated_fields = handler.apply_updates(data, {})
        
        assert updated_data == data
        assert updated_fields == []

    def test_apply_updates_preserves_original(self):
        """Test that original data is not modified."""
        handler = UpdateHandler(validate_values=False)
        data = {"hero": {"headline": "Original"}}
        updates = {"hero.headline": "New"}
        
        handler.apply_updates(data, updates)
        
        assert data["hero"]["headline"] == "Original"


class TestApplyUpdatesWithValidation:
    """Tests for applying updates with validation enabled."""

    def test_apply_update_with_valid_color(self):
        """Test applying update with valid HEX color."""
        handler = UpdateHandler(validate_values=True)
        data = {"theme": {"primary_color": "#000000"}}
        updates = {"theme.primary_color": "#FF6B6B"}
        
        updated_data, updated_fields = handler.apply_updates(data, updates)
        
        assert updated_data["theme"]["primary_color"] == "#FF6B6B"
        assert "theme.primary_color" in updated_fields

    def test_apply_update_with_invalid_color(self):
        """Test that invalid color is rejected."""
        handler = UpdateHandler(validate_values=True)
        data = {"theme": {"primary_color": "#000000"}}
        updates = {"theme.primary_color": "red"}
        
        with pytest.raises(InvalidFieldPathError) as exc_info:
            handler.apply_updates(data, updates)
        assert "Validation failed" in exc_info.value.message

    def test_apply_update_with_valid_image_url(self):
        """Test applying update with valid image URL."""
        handler = UpdateHandler(validate_values=True)
        data = {"hero": {"image": "https://old.com/image.jpg"}}
        updates = {"hero.image": "https://new.com/image.png"}
        
        updated_data, updated_fields = handler.apply_updates(data, updates)
        
        assert updated_data["hero"]["image"] == "https://new.com/image.png"

    def test_apply_update_with_invalid_image_url(self):
        """Test that invalid image URL is rejected."""
        handler = UpdateHandler(validate_values=True)
        data = {"hero": {"image": "https://old.com/image.jpg"}}
        updates = {"hero.image": "not-a-url"}
        
        with pytest.raises(InvalidFieldPathError) as exc_info:
            handler.apply_updates(data, updates)
        assert "Validation failed" in exc_info.value.message


class TestUpdateResponse:
    """Tests for update response format.
    
    Requirements: 3.5
    """

    def test_response_contains_updated_fields(self):
        """Test that response contains list of updated fields."""
        handler = UpdateHandler(validate_values=False)
        data = {
            "hero": {"headline": "Original", "subheadline": "Sub"},
            "theme": {"primary_color": "#000000"},
        }
        updates = {
            "hero.headline": "New Headline",
            "theme.primary_color": "#FF6B6B",
        }
        
        updated_data, updated_fields = handler.apply_updates(data, updates)
        
        assert "hero.headline" in updated_fields
        assert "theme.primary_color" in updated_fields
        assert len(updated_fields) == 2

    def test_response_contains_updated_at_timestamp(self):
        """Test that response contains updated_at timestamp."""
        handler = UpdateHandler(validate_values=False)
        data = {"hero": {"headline": "Original"}}
        updates = {"hero.headline": "New"}
        
        updated_data, updated_fields = handler.apply_updates(data, updates)
        
        assert "updated_at" in updated_data
        # Verify it's a valid ISO timestamp
        timestamp = updated_data["updated_at"]
        assert isinstance(timestamp, str)
        assert "T" in timestamp  # ISO format contains T

    def test_response_preserves_unchanged_fields(self):
        """Test that unchanged fields are preserved in response."""
        handler = UpdateHandler(validate_values=False)
        data = {
            "hero": {
                "headline": "Original",
                "subheadline": "Keep This",
                "image": "https://example.com/image.jpg",
            },
            "cta": {
                "text": "Buy Now",
                "url": "https://example.com/checkout",
            },
        }
        updates = {"hero.headline": "New Headline"}
        
        updated_data, updated_fields = handler.apply_updates(data, updates)
        
        # Changed field
        assert updated_data["hero"]["headline"] == "New Headline"
        # Unchanged fields
        assert updated_data["hero"]["subheadline"] == "Keep This"
        assert updated_data["hero"]["image"] == "https://example.com/image.jpg"
        assert updated_data["cta"]["text"] == "Buy Now"
        assert updated_data["cta"]["url"] == "https://example.com/checkout"

