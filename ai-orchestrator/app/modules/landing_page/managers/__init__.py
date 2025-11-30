"""
Managers for Landing Page module.

Provides managers for various landing page operations:
- UpdateHandler: Handles landing page field updates with validation
- ABTestManager: Manages A/B testing
- HostingManager: Manages landing page hosting (S3 + CloudFront)
- ExportManager: Manages landing page export

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 6.1, 7.1, 8.1
"""

from .update_handler import UpdateHandler, UpdateError, InvalidFieldPathError
from .ab_test_manager import ABTestManager
from .hosting_manager import HostingManager
from .export_manager import ExportManager

# Re-export validation errors for convenience
from ..utils.validators import (
    ValidationError,
    InvalidImageURLError,
    InvalidColorError,
)

__all__ = [
    "UpdateHandler",
    "UpdateError",
    "InvalidFieldPathError",
    "ABTestManager",
    "HostingManager",
    "ExportManager",
    "ValidationError",
    "InvalidImageURLError",
    "InvalidColorError",
]
