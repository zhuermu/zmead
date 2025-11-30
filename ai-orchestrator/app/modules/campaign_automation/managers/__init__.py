"""
Campaign Automation Managers

This package contains manager classes for campaign automation:
- CampaignManager: Handles campaign creation, updates, and status queries
- ABTestManager: Handles A/B test creation and analysis
"""

from .ab_test_manager import ABTestManager
from .campaign_manager import CampaignManager

__all__ = ["ABTestManager", "CampaignManager"]
