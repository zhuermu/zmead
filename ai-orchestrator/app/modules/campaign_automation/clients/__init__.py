"""
Campaign Automation Clients - External service clients.

This module provides client wrappers for external services:
- AIClient: Gemini AI client for ad copy generation
"""

from app.modules.campaign_automation.clients.ai_client import AIClient

__all__ = ["AIClient"]
