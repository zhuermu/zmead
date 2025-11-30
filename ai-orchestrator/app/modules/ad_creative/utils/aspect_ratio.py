"""
Aspect ratio handling utilities.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
- 5.1: Auto-select aspect ratio based on platform
- 5.2: TikTok -> 9:16
- 5.3: Instagram Feed -> 1:1
- 5.4: Facebook Feed -> 4:5
- 5.5: Support custom aspect ratio input
"""

import re
from typing import Literal


Platform = Literal["tiktok", "instagram", "facebook"]


class AspectRatioHandler:
    """Handles aspect ratio mapping and parsing.

    Maps platforms to aspect ratios:
    - TikTok: 9:16
    - Instagram Feed: 1:1
    - Facebook Feed: 4:5

    Also supports custom aspect ratios in formats:
    - "W:H" (e.g., "9:16", "16:9")
    - "WxH" (e.g., "1080x1920")
    """

    # Platform to aspect ratio mapping (Requirements 5.1-5.4)
    PLATFORM_RATIOS: dict[str, str] = {
        "tiktok": "9:16",      # Requirement 5.2
        "instagram": "1:1",   # Requirement 5.3
        "facebook": "4:5",    # Requirement 5.4
    }

    # Aspect ratio to pixel dimensions (minimum 1080 on shorter side)
    RATIO_DIMENSIONS: dict[str, tuple[int, int]] = {
        "9:16": (1080, 1920),   # TikTok vertical
        "1:1": (1080, 1080),    # Instagram square
        "4:5": (1080, 1350),    # Facebook feed
        "16:9": (1920, 1080),   # Landscape
        "4:3": (1440, 1080),    # Traditional
        "3:4": (1080, 1440),    # Portrait
        "2:3": (1080, 1620),    # Portrait
        "3:2": (1620, 1080),    # Landscape
    }

    # Minimum dimension for generated images
    MIN_DIMENSION = 1080

    def get_ratio_for_platform(self, platform: str) -> str:
        """Get aspect ratio for a platform (Requirement 5.1).

        Args:
            platform: Platform name (tiktok, instagram, facebook)

        Returns:
            Aspect ratio string (e.g., "9:16")

        Raises:
            ValueError: If platform is not supported
        """
        normalized = platform.lower().strip()
        ratio = self.PLATFORM_RATIOS.get(normalized)
        if ratio is None:
            supported = ", ".join(self.PLATFORM_RATIOS.keys())
            raise ValueError(f"Unsupported platform: {platform}. Supported: {supported}")
        return ratio

    def get_dimensions(self, aspect_ratio: str) -> tuple[int, int]:
        """Get pixel dimensions for an aspect ratio.

        Args:
            aspect_ratio: Aspect ratio string (e.g., "9:16")

        Returns:
            Tuple of (width, height)

        Raises:
            ValueError: If aspect ratio is invalid
        """
        normalized = aspect_ratio.strip()

        # Check predefined ratios first
        if normalized in self.RATIO_DIMENSIONS:
            return self.RATIO_DIMENSIONS[normalized]

        # Parse custom ratio (Requirement 5.5)
        return self.parse_custom_ratio(normalized)

    def parse_custom_ratio(self, ratio_str: str) -> tuple[int, int]:
        """Parse a custom aspect ratio string (Requirement 5.5).

        Supports formats:
        - "W:H" (e.g., "9:16", "16:9", "3:2")
        - "WxH" (e.g., "1080x1920", "1920x1080")

        Args:
            ratio_str: Ratio string like "9:16" or "1920x1080"

        Returns:
            Tuple of (width, height)

        Raises:
            ValueError: If ratio string is invalid
        """
        ratio_str = ratio_str.strip()

        # Try "W:H" format (ratio-based)
        match = re.match(r"^(\d+):(\d+)$", ratio_str)
        if match:
            w_ratio = int(match.group(1))
            h_ratio = int(match.group(2))

            if w_ratio <= 0 or h_ratio <= 0:
                raise ValueError(f"Aspect ratio values must be positive: {ratio_str}")

            # Calculate dimensions ensuring minimum dimension is 1080
            if w_ratio >= h_ratio:
                # Landscape or square
                width = max(self.MIN_DIMENSION, int(self.MIN_DIMENSION * w_ratio / h_ratio))
                height = self.MIN_DIMENSION
            else:
                # Portrait
                width = self.MIN_DIMENSION
                height = max(self.MIN_DIMENSION, int(self.MIN_DIMENSION * h_ratio / w_ratio))

            return (width, height)

        # Try "WxH" format (pixel-based)
        match = re.match(r"^(\d+)[xX](\d+)$", ratio_str)
        if match:
            width = int(match.group(1))
            height = int(match.group(2))

            if width <= 0 or height <= 0:
                raise ValueError(f"Dimensions must be positive: {ratio_str}")

            return (width, height)

        raise ValueError(
            f"Invalid aspect ratio format: {ratio_str}. "
            "Use 'W:H' (e.g., '9:16') or 'WxH' (e.g., '1080x1920')"
        )

    def is_valid_ratio(self, ratio_str: str) -> bool:
        """Check if an aspect ratio string is valid.

        Args:
            ratio_str: Ratio string to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            self.get_dimensions(ratio_str)
            return True
        except ValueError:
            return False

    def get_aspect_ratio_string(self, width: int, height: int) -> str:
        """Convert dimensions to aspect ratio string.

        Args:
            width: Image width
            height: Image height

        Returns:
            Aspect ratio string (e.g., "9:16")
        """
        from math import gcd

        divisor = gcd(width, height)
        w_ratio = width // divisor
        h_ratio = height // divisor

        return f"{w_ratio}:{h_ratio}"

    def resolve_aspect_ratio(
        self,
        platform: str | None = None,
        custom_ratio: str | None = None,
        default: str = "1:1",
    ) -> tuple[str, tuple[int, int]]:
        """Resolve aspect ratio from platform or custom input.

        Priority:
        1. Custom ratio if provided
        2. Platform-based ratio if platform provided
        3. Default ratio

        Args:
            platform: Optional platform name
            custom_ratio: Optional custom aspect ratio
            default: Default aspect ratio if neither provided

        Returns:
            Tuple of (aspect_ratio_string, (width, height))

        Raises:
            ValueError: If custom_ratio is invalid or platform unsupported
        """
        # Custom ratio takes priority (Requirement 5.5)
        if custom_ratio:
            dimensions = self.get_dimensions(custom_ratio)
            return (custom_ratio, dimensions)

        # Platform-based ratio (Requirements 5.1-5.4)
        if platform:
            ratio = self.get_ratio_for_platform(platform)
            dimensions = self.RATIO_DIMENSIONS[ratio]
            return (ratio, dimensions)

        # Default
        dimensions = self.get_dimensions(default)
        return (default, dimensions)


# Module-level instance for convenience
aspect_ratio_handler = AspectRatioHandler()
