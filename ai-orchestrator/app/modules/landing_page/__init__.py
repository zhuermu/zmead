"""
Landing Page module for AI Orchestrator.

This module provides landing page generation and management capabilities including:
- Product information extraction (Shopify, Amazon)
- AI-powered landing page generation
- Copy optimization
- Multi-language translation
- A/B testing
- Landing page hosting (S3 + CloudFront)
- Landing page export
- Conversion tracking

This module provides implementation functions that are called directly
by Agent Custom Tools.

Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 8.1, 9.1
"""

from .models import (
    ProductInfo,
    Review,
    LandingPageContent,
    HeroSection,
    Feature,
    CTASection,
    OptimizationResult,
    TranslationResult,
    ABTest,
    ABTestAnalysis,
    PublishResult,
    ExportResult,
)

__all__ = [
    "ProductInfo",
    "Review",
    "LandingPageContent",
    "HeroSection",
    "Feature",
    "CTASection",
    "OptimizationResult",
    "TranslationResult",
    "ABTest",
    "ABTestAnalysis",
    "PublishResult",
    "ExportResult",
]
