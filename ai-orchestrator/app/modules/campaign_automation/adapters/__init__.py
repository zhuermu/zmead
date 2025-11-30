"""
Platform Adapters

Provides adapters for different advertising platforms (Meta, TikTok, Google).
"""

from .base import PlatformAdapter
from .meta_adapter import MetaAdapter
from .tiktok_adapter import TikTokAdapter
from .google_adapter import GoogleAdapter
from .router import PlatformRouter

__all__ = [
    "PlatformAdapter",
    "MetaAdapter",
    "TikTokAdapter",
    "GoogleAdapter",
    "PlatformRouter"
]
