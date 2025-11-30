"""
Dual Tracker for Landing Page module.

This module provides the DualTracker class that combines Facebook Pixel
and internal event tracking to ensure events are sent to both destinations.

Requirements: 9.1, 9.2, 9.3
"""

import structlog
from typing import Literal

from .pixel_injector import PixelInjector
from .event_tracker import EventTracker

logger = structlog.get_logger(__name__)


# Event types supported by dual tracking
EventType = Literal["PageView", "AddToCart", "Purchase"]


class DualTracker:
    """双重追踪器

    Combines Facebook Pixel and internal event tracking to ensure all events
    are sent to both Facebook and Web Platform for comprehensive analytics.

    Requirements: 9.1, 9.2, 9.3
    """

    def __init__(self, api_base_url: str = ""):
        """Initialize DualTracker.

        Args:
            api_base_url: Base URL for Web Platform API
        """
        self.pixel_injector = PixelInjector()
        self.event_tracker = EventTracker(api_base_url=api_base_url)

    def inject_dual_tracking(
        self,
        html: str,
        landing_page_id: str,
        pixel_id: str | None = None,
        campaign_id: str | None = None,
        events: list[EventType] | None = None,
    ) -> str:
        """注入双重追踪脚本

        Injects both Facebook Pixel and internal tracking scripts into HTML.
        Ensures events are sent to both destinations.

        Args:
            html: Original HTML content
            landing_page_id: Landing page ID for internal tracking
            pixel_id: Facebook Pixel ID (optional)
            campaign_id: Campaign ID for attribution (optional)
            events: List of events to track (default: ["PageView", "AddToCart", "Purchase"])

        Returns:
            HTML with both tracking scripts injected

        Requirements: 9.1, 9.2, 9.3
        """
        if events is None:
            events = ["PageView", "AddToCart", "Purchase"]

        logger.info(
            "dual_tracking_injection_start",
            landing_page_id=landing_page_id,
            has_pixel=pixel_id is not None,
            campaign_id=campaign_id,
            events=events,
        )

        # Step 1: Inject Facebook Pixel (if pixel_id provided)
        if pixel_id:
            html = self.pixel_injector.inject(
                html=html,
                pixel_id=pixel_id,
                events=events,
            )
            logger.info("facebook_pixel_injected", pixel_id=pixel_id[:6] + "***")
        else:
            logger.info("facebook_pixel_skipped", reason="no_pixel_id")

        # Step 2: Inject internal tracking (always)
        html = self.event_tracker.inject_tracking_script(
            html=html,
            landing_page_id=landing_page_id,
            campaign_id=campaign_id,
        )
        logger.info("internal_tracking_injected", landing_page_id=landing_page_id)

        logger.info(
            "dual_tracking_injection_complete",
            facebook_pixel=pixel_id is not None,
            internal_tracking=True,
        )

        return html

    def generate_cta_tracking_script(
        self,
        landing_page_id: str,
        pixel_id: str | None = None,
        product_info: dict | None = None,
    ) -> str:
        """生成 CTA 点击追踪脚本

        Generates JavaScript that tracks AddToCart events on CTA clicks
        to both Facebook and Web Platform.

        Args:
            landing_page_id: Landing page ID
            pixel_id: Facebook Pixel ID (optional)
            product_info: Product information for event data (optional)

        Returns:
            JavaScript code for CTA click tracking

        Requirements: 9.2
        """
        scripts = []

        # Facebook Pixel CTA tracking
        if pixel_id:
            fb_script = self.pixel_injector.generate_cta_click_script(
                pixel_id=pixel_id,
                product_info=product_info,
            )
            scripts.append(fb_script)

        # Note: Internal tracking is already handled by EventTracker's
        # attachCTAListeners in the main tracking script

        return "\n".join(scripts)

    def generate_purchase_tracking_script(
        self,
        landing_page_id: str,
        pixel_id: str | None = None,
        order_info: dict | None = None,
    ) -> str:
        """生成购买追踪脚本

        Generates JavaScript that tracks Purchase events to both
        Facebook and Web Platform.

        Args:
            landing_page_id: Landing page ID
            pixel_id: Facebook Pixel ID (optional)
            order_info: Order information for event data (optional)

        Returns:
            JavaScript code for purchase tracking

        Requirements: 9.3
        """
        scripts = []

        # Facebook Pixel purchase tracking
        if pixel_id:
            fb_script = self.pixel_injector.generate_purchase_script(
                pixel_id=pixel_id,
                order_info=order_info,
            )
            scripts.append(fb_script)

        # Internal purchase tracking
        if order_info:
            internal_script = self.event_tracker.generate_purchase_tracking_call(
                order_value=order_info.get("value", 0),
                currency=order_info.get("currency", "USD"),
                order_id=order_info.get("order_id"),
            )
            scripts.append(internal_script)

        return "\n".join(scripts)

    def verify_dual_tracking(self, html: str) -> dict:
        """验证双重追踪是否正确注入

        Verifies that both Facebook Pixel and internal tracking scripts
        are present in the HTML.

        Args:
            html: HTML content to verify

        Returns:
            Dictionary with verification results
        """
        has_facebook_pixel = "fbq('init'" in html or "fbevents.js" in html
        has_internal_tracking = "AAE_TRACKING" in html or "AAE Internal Tracking" in html

        result = {
            "facebook_pixel_present": has_facebook_pixel,
            "internal_tracking_present": has_internal_tracking,
            "dual_tracking_complete": has_facebook_pixel or has_internal_tracking,
            "both_present": has_facebook_pixel and has_internal_tracking,
        }

        logger.info("dual_tracking_verification", **result)

        return result
