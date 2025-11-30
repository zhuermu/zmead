"""
Tests for Landing Page tracking functionality.

Tests PixelInjector, EventTracker, and DualTracker classes.
"""

import pytest

from app.modules.landing_page.tracking import DualTracker, EventTracker, PixelInjector


class TestPixelInjector:
    """Tests for PixelInjector class."""

    def test_inject_pageview_event(self):
        """Test injecting PageView event."""
        injector = PixelInjector()
        html = "<html><head></head><body>Test</body></html>"
        pixel_id = "123456789"

        result = injector.inject(html, pixel_id, events=["PageView"])

        assert pixel_id in result
        assert "fbq('track', 'PageView')" in result
        assert "<!-- Facebook Pixel Code -->" in result

    def test_inject_multiple_events(self):
        """Test injecting multiple events (PageView, AddToCart, Purchase)."""
        injector = PixelInjector()
        html = "<html><head></head><body>Test</body></html>"
        pixel_id = "123456789"

        result = injector.inject(
            html, pixel_id, events=["PageView", "AddToCart", "Purchase"]
        )

        assert pixel_id in result
        assert "fbq('track', 'PageView')" in result
        assert "fbq('track', 'AddToCart')" in result
        assert "fbq('track', 'Purchase')" in result

    def test_generate_event_script_with_params(self):
        """Test generating event script with parameters."""
        injector = PixelInjector()

        result = injector.generate_event_script(
            "AddToCart",
            event_data={"content_name": "Product", "value": 99.99, "currency": "USD"},
        )

        assert "fbq('track', 'AddToCart'" in result
        assert "content_name: 'Product'" in result
        assert "value: 99.99" in result
        assert "currency: 'USD'" in result

    def test_generate_cta_click_script(self):
        """Test generating CTA click tracking script."""
        injector = PixelInjector()
        pixel_id = "123456789"
        product_info = {"title": "Test Product", "price": 49.99, "currency": "USD"}

        result = injector.generate_cta_click_script(pixel_id, product_info)

        assert "AddToCart" in result
        assert "content_name: 'Test Product'" in result
        assert "value: 49.99" in result
        assert "currency: 'USD'" in result

    def test_generate_purchase_script(self):
        """Test generating purchase tracking script."""
        injector = PixelInjector()
        pixel_id = "123456789"
        order_info = {"value": 149.99, "currency": "USD", "order_id": "ORD123"}

        result = injector.generate_purchase_script(pixel_id, order_info)

        assert "fbq('track', 'Purchase'" in result
        assert "value: 149.99" in result
        assert "currency: 'USD'" in result

    def test_inject_without_pixel_id(self):
        """Test that injection is skipped when pixel_id is empty."""
        injector = PixelInjector()
        html = "<html><head></head><body>Test</body></html>"

        result = injector.inject(html, "", events=["PageView"])

        assert result == html  # HTML unchanged
        assert "fbq" not in result


class TestEventTracker:
    """Tests for EventTracker class."""

    def test_generate_tracking_script(self):
        """Test generating internal tracking script."""
        tracker = EventTracker(api_base_url="https://api.aae.com")
        landing_page_id = "lp_123"
        campaign_id = "camp_456"

        result = tracker.generate_tracking_script(landing_page_id, campaign_id)

        assert "AAE_TRACKING" in result
        assert landing_page_id in result
        assert campaign_id in result
        assert "PageView" in result
        assert "AddToCart" in result
        assert "Purchase" in result
        assert "/api/v1/landing-pages/events" in result

    def test_generate_tracking_script_without_campaign(self):
        """Test generating tracking script without campaign ID."""
        tracker = EventTracker()
        landing_page_id = "lp_123"

        result = tracker.generate_tracking_script(landing_page_id)

        assert "AAE_TRACKING" in result
        assert landing_page_id in result
        assert "PageView" in result

    def test_generate_purchase_tracking_call(self):
        """Test generating purchase tracking call."""
        tracker = EventTracker()

        result = tracker.generate_purchase_tracking_call(
            order_value=199.99, currency="USD", order_id="ORD789"
        )

        assert "AAE_TRACKING.trackPurchase" in result
        assert "199.99" in result
        assert "USD" in result
        assert "ORD789" in result

    def test_inject_tracking_script(self):
        """Test injecting tracking script into HTML."""
        tracker = EventTracker()
        html = "<html><head></head><body>Test</body></html>"
        landing_page_id = "lp_123"

        result = tracker.inject_tracking_script(html, landing_page_id)

        assert "AAE_TRACKING" in result
        assert landing_page_id in result
        assert "</body>" in result
        # Script should be injected before </body>
        assert result.index("AAE_TRACKING") < result.index("</body>")

    def test_inject_tracking_script_with_campaign(self):
        """Test injecting tracking script with campaign ID."""
        tracker = EventTracker()
        html = "<html><head></head><body>Test</body></html>"
        landing_page_id = "lp_123"
        campaign_id = "camp_456"

        result = tracker.inject_tracking_script(html, landing_page_id, campaign_id)

        assert "AAE_TRACKING" in result
        assert landing_page_id in result
        assert campaign_id in result


class TestDualTracking:
    """Tests for dual tracking (Facebook Pixel + Internal)."""

    def test_both_tracking_systems_injected(self):
        """Test that both Facebook Pixel and internal tracking can be injected."""
        pixel_injector = PixelInjector()
        event_tracker = EventTracker()

        html = "<html><head></head><body>Test</body></html>"
        pixel_id = "123456789"
        landing_page_id = "lp_123"

        # Inject Facebook Pixel
        html_with_pixel = pixel_injector.inject(
            html, pixel_id, events=["PageView", "AddToCart", "Purchase"]
        )

        # Inject internal tracking
        html_with_both = event_tracker.inject_tracking_script(
            html_with_pixel, landing_page_id
        )

        # Verify both are present
        assert "fbq('track', 'PageView')" in html_with_both
        assert "AAE_TRACKING" in html_with_both
        assert pixel_id in html_with_both
        assert landing_page_id in html_with_both

    def test_tracking_events_match(self):
        """Test that both tracking systems track the same events."""
        pixel_injector = PixelInjector()
        event_tracker = EventTracker()

        html = "<html><head></head><body>Test</body></html>"
        pixel_id = "123456789"
        landing_page_id = "lp_123"

        # Inject both
        html_with_pixel = pixel_injector.inject(
            html, pixel_id, events=["PageView", "AddToCart", "Purchase"]
        )
        html_with_both = event_tracker.inject_tracking_script(
            html_with_pixel, landing_page_id
        )

        # Verify all three events are tracked by both systems
        # Facebook Pixel
        assert "fbq('track', 'PageView')" in html_with_both
        assert "fbq('track', 'AddToCart')" in html_with_both
        assert "fbq('track', 'Purchase')" in html_with_both

        # Internal tracking
        assert "trackPageView" in html_with_both
        assert "trackAddToCart" in html_with_both
        assert "trackPurchase" in html_with_both


class TestDualTrackerClass:
    """Tests for DualTracker class that combines both tracking systems."""

    def test_inject_dual_tracking_with_pixel(self):
        """Test injecting dual tracking with Facebook Pixel."""
        tracker = DualTracker(api_base_url="https://api.aae.com")
        html = "<html><head></head><body>Test</body></html>"
        landing_page_id = "lp_123"
        pixel_id = "123456789"
        campaign_id = "camp_456"

        result = tracker.inject_dual_tracking(
            html=html,
            landing_page_id=landing_page_id,
            pixel_id=pixel_id,
            campaign_id=campaign_id,
            events=["PageView", "AddToCart", "Purchase"],
        )

        # Verify Facebook Pixel is present
        assert "fbq('track', 'PageView')" in result
        assert "fbq('track', 'AddToCart')" in result
        assert "fbq('track', 'Purchase')" in result
        assert pixel_id in result

        # Verify internal tracking is present
        assert "AAE_TRACKING" in result
        assert landing_page_id in result
        assert campaign_id in result

    def test_inject_dual_tracking_without_pixel(self):
        """Test injecting dual tracking without Facebook Pixel (internal only)."""
        tracker = DualTracker()
        html = "<html><head></head><body>Test</body></html>"
        landing_page_id = "lp_123"

        result = tracker.inject_dual_tracking(
            html=html,
            landing_page_id=landing_page_id,
            pixel_id=None,
            campaign_id=None,
        )

        # Verify Facebook Pixel is NOT present
        assert "fbq" not in result

        # Verify internal tracking IS present
        assert "AAE_TRACKING" in result
        assert landing_page_id in result

    def test_verify_dual_tracking_both_present(self):
        """Test verification when both tracking systems are present."""
        tracker = DualTracker()
        html = "<html><head></head><body>Test</body></html>"
        landing_page_id = "lp_123"
        pixel_id = "123456789"

        html_with_tracking = tracker.inject_dual_tracking(
            html=html,
            landing_page_id=landing_page_id,
            pixel_id=pixel_id,
        )

        verification = tracker.verify_dual_tracking(html_with_tracking)

        assert verification["facebook_pixel_present"] is True
        assert verification["internal_tracking_present"] is True
        assert verification["dual_tracking_complete"] is True
        assert verification["both_present"] is True

    def test_verify_dual_tracking_internal_only(self):
        """Test verification when only internal tracking is present."""
        tracker = DualTracker()
        html = "<html><head></head><body>Test</body></html>"
        landing_page_id = "lp_123"

        html_with_tracking = tracker.inject_dual_tracking(
            html=html,
            landing_page_id=landing_page_id,
            pixel_id=None,
        )

        verification = tracker.verify_dual_tracking(html_with_tracking)

        assert verification["facebook_pixel_present"] is False
        assert verification["internal_tracking_present"] is True
        assert verification["dual_tracking_complete"] is True
        assert verification["both_present"] is False

    def test_generate_cta_tracking_script(self):
        """Test generating CTA tracking script for both systems."""
        tracker = DualTracker()
        landing_page_id = "lp_123"
        pixel_id = "123456789"
        product_info = {"title": "Test Product", "price": 49.99, "currency": "USD"}

        result = tracker.generate_cta_tracking_script(
            landing_page_id=landing_page_id,
            pixel_id=pixel_id,
            product_info=product_info,
        )

        # Should include Facebook Pixel CTA tracking
        assert "AddToCart" in result
        assert "content_name: 'Test Product'" in result

    def test_generate_purchase_tracking_script(self):
        """Test generating purchase tracking script for both systems."""
        tracker = DualTracker()
        landing_page_id = "lp_123"
        pixel_id = "123456789"
        order_info = {"value": 199.99, "currency": "USD", "order_id": "ORD123"}

        result = tracker.generate_purchase_tracking_script(
            landing_page_id=landing_page_id,
            pixel_id=pixel_id,
            order_info=order_info,
        )

        # Should include both Facebook Pixel and internal tracking
        assert "fbq('track', 'Purchase'" in result
        assert "AAE_TRACKING.trackPurchase" in result
        assert "199.99" in result
        assert "ORD123" in result

    def test_events_sent_to_both_destinations(self):
        """
        Test that events are configured to be sent to both destinations.
        
        Requirements: 9.1, 9.2, 9.3
        """
        tracker = DualTracker(api_base_url="https://api.aae.com")
        html = "<html><head></head><body><button class='cta-button'>Buy Now</button></body></html>"
        landing_page_id = "lp_123"
        pixel_id = "123456789"
        campaign_id = "camp_456"

        result = tracker.inject_dual_tracking(
            html=html,
            landing_page_id=landing_page_id,
            pixel_id=pixel_id,
            campaign_id=campaign_id,
            events=["PageView", "AddToCart", "Purchase"],
        )

        # Verify PageView event is tracked by both
        assert "fbq('track', 'PageView')" in result
        assert "trackPageView" in result

        # Verify AddToCart event is tracked by both
        assert "fbq('track', 'AddToCart')" in result
        assert "trackAddToCart" in result

        # Verify Purchase event is tracked by both
        assert "fbq('track', 'Purchase')" in result
        assert "trackPurchase" in result

        # Verify both tracking systems are initialized
        assert "fbq('init'" in result
        assert "AAE_TRACKING.init" in result
