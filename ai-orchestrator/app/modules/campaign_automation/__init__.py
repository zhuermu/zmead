"""
Campaign Automation module for AAE.

This module provides automated campaign creation, management, and optimization
capabilities for advertising platforms (Meta, TikTok, Google Ads).

This module provides implementation functions that are called directly
by Agent Custom Tools.
"""

from .models import (
    Campaign,
    Adset,
    Ad,
    Rule,
    ABTest,
    OptimizationResult,
    ABTestResult,
)

__all__ = [
    "Campaign",
    "Adset",
    "Ad",
    "Rule",
    "ABTest",
    "OptimizationResult",
    "ABTestResult",
]
