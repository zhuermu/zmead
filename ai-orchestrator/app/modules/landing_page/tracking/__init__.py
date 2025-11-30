"""
Tracking package for Landing Page module.

This package provides tracking functionality:
- PixelInjector: Facebook Pixel code injection
- EventTracker: Internal event tracking to Web Platform
- DualTracker: Combined Facebook Pixel + Internal tracking
"""

from .dual_tracker import DualTracker
from .event_tracker import EventTracker
from .pixel_injector import PixelInjector

__all__ = ["DualTracker", "EventTracker", "PixelInjector"]
