"""
Campaign Automation module for AAE.

This module provides automated campaign creation, management, and optimization
capabilities for advertising platforms (Meta, TikTok, Google Ads).
"""

from .capability import CampaignAutomation
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
    "CampaignAutomation",
    "Campaign",
    "Adset",
    "Ad",
    "Rule",
    "ABTest",
    "OptimizationResult",
    "ABTestResult",
]
