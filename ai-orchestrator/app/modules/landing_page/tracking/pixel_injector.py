"""
Facebook Pixel Injector for Landing Page module.

This module provides the PixelInjector class for injecting Facebook Pixel
tracking code into landing page HTML.

Requirements: 2.5, 9.1, 9.2, 9.3
"""

import re
from typing import Literal

import structlog

logger = structlog.get_logger(__name__)


# Facebook Pixel event types
EventType = Literal["PageView", "AddToCart", "Purchase", "Lead", "ViewContent"]


class PixelInjector:
    """Facebook Pixel 注入器

    Injects Facebook Pixel tracking code into landing page HTML.
    Supports multiple event types including PageView, AddToCart, and Purchase.

    Requirements: 2.5, 9.1, 9.2, 9.3
    """

    # Facebook Pixel base script template
    PIXEL_BASE_SCRIPT = """
<!-- Facebook Pixel Code -->
<script>
!function(f,b,e,v,n,t,s)
{{if(f.fbq)return;n=f.fbq=function(){{n.callMethod?
n.callMethod.apply(n,arguments):n.queue.push(arguments)}};
if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
n.queue=[];t=b.createElement(e);t.async=!0;
t.src=v;s=b.getElementsByTagName(e)[0];
s.parentNode.insertBefore(t,s)}}(window, document,'script',
'https://connect.facebook.net/en_US/fbevents.js');
fbq('init', '{pixel_id}');
{events}
</script>
<noscript><img height="1" width="1" style="display:none"
src="https://www.facebook.com/tr?id={pixel_id}&ev=PageView&noscript=1"
/></noscript>
<!-- End Facebook Pixel Code -->
"""

    # Event tracking script templates
    EVENT_TEMPLATES = {
        "PageView": "fbq('track', 'PageView');",
        "AddToCart": "fbq('track', 'AddToCart'{params});",
        "Purchase": "fbq('track', 'Purchase'{params});",
        "Lead": "fbq('track', 'Lead'{params});",
        "ViewContent": "fbq('track', 'ViewContent'{params});",
    }

    def __init__(self):
        """Initialize PixelInjector."""
        pass

    def inject(
        self,
        html: str,
        pixel_id: str,
        events: list[EventType] | None = None,
    ) -> str:
        """注入 Facebook Pixel 代码

        Injects Facebook Pixel tracking code into HTML.

        Args:
            html: Original HTML content
            pixel_id: Facebook Pixel ID
            events: List of events to track (default: ["PageView"])

        Returns:
            HTML with injected Pixel code

        Requirements: 2.5
        """
        if not pixel_id:
            logger.warning("pixel_injection_skipped", reason="no_pixel_id")
            return html

        if events is None:
            events = ["PageView"]

        logger.info(
            "pixel_injection_start",
            pixel_id=pixel_id[:6] + "***",  # Mask for logging
            events=events,
        )

        # Generate event tracking code
        event_scripts = []
        for event in events:
            event_script = self._generate_event_script(event)
            if event_script:
                event_scripts.append(event_script)

        events_code = "\n".join(event_scripts)

        # Generate complete pixel script
        pixel_script = self.PIXEL_BASE_SCRIPT.format(
            pixel_id=pixel_id,
            events=events_code,
        )

        # Inject into HTML
        injected_html = self._inject_into_head(html, pixel_script)

        logger.info(
            "pixel_injection_complete",
            events_count=len(events),
        )

        return injected_html

    def generate_event_script(
        self,
        event_type: EventType,
        event_data: dict | None = None,
    ) -> str:
        """生成事件追踪脚本

        Generates JavaScript code for tracking a specific event.

        Args:
            event_type: Type of event (PageView, AddToCart, Purchase, etc.)
            event_data: Optional event parameters

        Returns:
            JavaScript event tracking code

        Requirements: 9.1, 9.2, 9.3
        """
        return self._generate_event_script(event_type, event_data)

    def _generate_event_script(
        self,
        event_type: EventType,
        event_data: dict | None = None,
    ) -> str:
        """Generate event tracking script.

        Args:
            event_type: Type of event
            event_data: Optional event parameters

        Returns:
            JavaScript event tracking code
        """
        template = self.EVENT_TEMPLATES.get(event_type)
        if not template:
            logger.warning("unknown_event_type", event_type=event_type)
            return ""

        # Format parameters if provided
        if event_data and "{params}" in template:
            params_str = ", " + self._format_event_params(event_data)
            return template.replace("{params}", params_str)
        else:
            return template.replace("{params}", "")

    def _format_event_params(self, event_data: dict) -> str:
        """Format event parameters as JavaScript object.

        Args:
            event_data: Event parameters dict

        Returns:
            JavaScript object string
        """
        # Filter and format parameters
        formatted_params = {}

        for key, value in event_data.items():
            if value is not None:
                if isinstance(value, str):
                    formatted_params[key] = value
                elif isinstance(value, (int, float)):
                    formatted_params[key] = value
                elif isinstance(value, bool):
                    formatted_params[key] = value

        if not formatted_params:
            return "{}"

        # Build JavaScript object string
        parts = []
        for key, value in formatted_params.items():
            if isinstance(value, str):
                parts.append(f"{key}: '{self._escape_js_string(value)}'")
            elif isinstance(value, bool):
                parts.append(f"{key}: {'true' if value else 'false'}")
            else:
                parts.append(f"{key}: {value}")

        return "{" + ", ".join(parts) + "}"

    def _escape_js_string(self, s: str) -> str:
        """Escape string for JavaScript.

        Args:
            s: String to escape

        Returns:
            Escaped string safe for JavaScript
        """
        return (
            s.replace("\\", "\\\\")
            .replace("'", "\\'")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
        )

    def _inject_into_head(self, html: str, script: str) -> str:
        """Inject script into HTML head section.

        Args:
            html: Original HTML
            script: Script to inject

        Returns:
            HTML with injected script
        """
        # Try to inject before </head>
        head_close_pattern = re.compile(r"</head>", re.IGNORECASE)
        match = head_close_pattern.search(html)

        if match:
            return html[: match.start()] + script + "\n" + html[match.start() :]

        # Try to inject after <head>
        head_open_pattern = re.compile(r"<head[^>]*>", re.IGNORECASE)
        match = head_open_pattern.search(html)

        if match:
            return html[: match.end()] + "\n" + script + html[match.end() :]

        # Fallback: prepend to HTML
        logger.warning("no_head_tag_found", action="prepending_script")
        return script + "\n" + html

    def generate_cta_click_script(
        self,
        pixel_id: str,
        product_info: dict | None = None,
    ) -> str:
        """Generate CTA click tracking script.

        Creates JavaScript that tracks AddToCart event when CTA is clicked.

        Args:
            pixel_id: Facebook Pixel ID
            product_info: Optional product information for event data

        Returns:
            JavaScript code for CTA click tracking

        Requirements: 9.2
        """
        event_data = {}
        if product_info:
            if "title" in product_info:
                event_data["content_name"] = product_info["title"]
            if "price" in product_info:
                event_data["value"] = product_info["price"]
            if "currency" in product_info:
                event_data["currency"] = product_info["currency"]

        params = self._format_event_params(event_data) if event_data else "{}"

        return f"""
<script>
document.addEventListener('DOMContentLoaded', function() {{
    var ctaButtons = document.querySelectorAll('.cta-button, [data-cta="true"]');
    ctaButtons.forEach(function(btn) {{
        btn.addEventListener('click', function() {{
            fbq('track', 'AddToCart', {params});
        }});
    }});
}});
</script>
"""

    def generate_purchase_script(
        self,
        pixel_id: str,
        order_info: dict | None = None,
    ) -> str:
        """Generate purchase tracking script.

        Creates JavaScript that tracks Purchase event.

        Args:
            pixel_id: Facebook Pixel ID
            order_info: Optional order information for event data

        Returns:
            JavaScript code for purchase tracking

        Requirements: 9.3
        """
        event_data = {}
        if order_info:
            if "value" in order_info:
                event_data["value"] = order_info["value"]
            if "currency" in order_info:
                event_data["currency"] = order_info["currency"]
            if "order_id" in order_info:
                event_data["content_ids"] = [order_info["order_id"]]

        params = self._format_event_params(event_data) if event_data else "{}"

        return f"""
<script>
// Track purchase event
fbq('track', 'Purchase', {params});
</script>
"""
