"""
Internal Event Tracker for Landing Page module.

This module provides the EventTracker class for generating internal tracking
scripts that send events to the Web Platform for analytics.

Requirements: 9.1, 9.2, 9.3
"""

import structlog
from typing import Literal

logger = structlog.get_logger(__name__)


# Event types for internal tracking
EventType = Literal["PageView", "AddToCart", "Purchase"]


class EventTracker:
    """内部事件追踪器

    Generates internal tracking scripts that send events to Web Platform
    for AAE's own analytics system.

    Requirements: 9.1, 9.2, 9.3
    """

    # Web Platform event API endpoint
    EVENT_API_ENDPOINT = "/api/v1/landing-pages/events"

    def __init__(self, api_base_url: str = ""):
        """Initialize EventTracker.

        Args:
            api_base_url: Base URL for Web Platform API (e.g., "https://api.aae.com")
        """
        self.api_base_url = api_base_url or ""

    def generate_tracking_script(
        self,
        landing_page_id: str,
        campaign_id: str | None = None,
    ) -> str:
        """生成内部分析追踪脚本

        Generates JavaScript tracking script that sends events to Web Platform.

        追踪事件：
        - PageView: 页面访问
        - AddToCart: CTA 点击
        - Purchase: 购买完成

        Args:
            landing_page_id: Landing page ID
            campaign_id: Optional campaign ID for attribution

        Returns:
            JavaScript tracking code

        Requirements: 9.1, 9.2, 9.3
        """
        logger.info(
            "generating_tracking_script",
            landing_page_id=landing_page_id,
            campaign_id=campaign_id,
        )

        script = f"""
<!-- AAE Internal Tracking -->
<script>
(function() {{
    var AAE_TRACKING = {{
        apiUrl: '{self.api_base_url}{self.EVENT_API_ENDPOINT}',
        landingPageId: '{landing_page_id}',
        campaignId: '{campaign_id or ""}',
        sessionId: null,

        // Initialize session
        init: function() {{
            this.sessionId = this.getOrCreateSessionId();
            this.trackPageView();
            this.attachCTAListeners();
        }},

        // Get or create session ID
        getOrCreateSessionId: function() {{
            var sessionId = this.getCookie('aae_session_id');
            if (!sessionId) {{
                sessionId = 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                this.setCookie('aae_session_id', sessionId, 30); // 30 days
            }}
            return sessionId;
        }},

        // Track PageView event
        trackPageView: function() {{
            this.sendEvent('PageView', {{
                url: window.location.href,
                referrer: document.referrer,
                timestamp: new Date().toISOString()
            }});
        }},

        // Attach listeners to CTA buttons
        attachCTAListeners: function() {{
            var self = this;
            var ctaButtons = document.querySelectorAll('.cta-button, [data-cta="true"]');
            
            ctaButtons.forEach(function(btn) {{
                btn.addEventListener('click', function(e) {{
                    self.trackAddToCart({{
                        button_text: btn.textContent || btn.innerText,
                        button_id: btn.id || null,
                        timestamp: new Date().toISOString()
                    }});
                }});
            }});
        }},

        // Track AddToCart event (CTA click)
        trackAddToCart: function(data) {{
            this.sendEvent('AddToCart', data);
        }},

        // Track Purchase event
        trackPurchase: function(data) {{
            this.sendEvent('Purchase', data);
        }},

        // Send event to Web Platform
        sendEvent: function(eventType, eventData) {{
            var payload = {{
                event_type: eventType,
                landing_page_id: this.landingPageId,
                campaign_id: this.campaignId,
                session_id: this.sessionId,
                event_data: eventData,
                user_agent: navigator.userAgent,
                screen_resolution: window.screen.width + 'x' + window.screen.height,
                timestamp: new Date().toISOString()
            }};

            // Send via beacon API (non-blocking)
            if (navigator.sendBeacon) {{
                var blob = new Blob([JSON.stringify(payload)], {{ type: 'application/json' }});
                navigator.sendBeacon(this.apiUrl, blob);
            }} else {{
                // Fallback to fetch
                fetch(this.apiUrl, {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify(payload),
                    keepalive: true
                }}).catch(function(err) {{
                    console.error('AAE tracking error:', err);
                }});
            }}
        }},

        // Cookie utilities
        setCookie: function(name, value, days) {{
            var expires = '';
            if (days) {{
                var date = new Date();
                date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
                expires = '; expires=' + date.toUTCString();
            }}
            document.cookie = name + '=' + (value || '') + expires + '; path=/; SameSite=Lax';
        }},

        getCookie: function(name) {{
            var nameEQ = name + '=';
            var ca = document.cookie.split(';');
            for (var i = 0; i < ca.length; i++) {{
                var c = ca[i];
                while (c.charAt(0) === ' ') c = c.substring(1, c.length);
                if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
            }}
            return null;
        }}
    }};

    // Initialize tracking when DOM is ready
    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', function() {{
            AAE_TRACKING.init();
        }});
    }} else {{
        AAE_TRACKING.init();
    }}

    // Expose for manual purchase tracking
    window.AAE_TRACKING = AAE_TRACKING;
}})();
</script>
<!-- End AAE Internal Tracking -->
"""

        return script

    def generate_purchase_tracking_call(
        self,
        order_value: float,
        currency: str = "USD",
        order_id: str | None = None,
    ) -> str:
        """生成购买事件追踪调用

        Generates JavaScript code to manually trigger purchase tracking.
        This should be called on the order confirmation page.

        Args:
            order_value: Order total value
            currency: Currency code
            order_id: Optional order ID

        Returns:
            JavaScript code to trigger purchase event

        Requirements: 9.3
        """
        return f"""
<script>
if (window.AAE_TRACKING) {{
    AAE_TRACKING.trackPurchase({{
        value: {order_value},
        currency: '{currency}',
        order_id: '{order_id or ""}',
        timestamp: new Date().toISOString()
    }});
}}
</script>
"""

    def inject_tracking_script(
        self,
        html: str,
        landing_page_id: str,
        campaign_id: str | None = None,
    ) -> str:
        """注入内部追踪脚本到 HTML

        Injects internal tracking script into HTML.

        Args:
            html: Original HTML content
            landing_page_id: Landing page ID
            campaign_id: Optional campaign ID

        Returns:
            HTML with injected tracking script

        Requirements: 9.1, 9.2, 9.3
        """
        tracking_script = self.generate_tracking_script(landing_page_id, campaign_id)

        # Inject before </body> tag
        import re

        body_close_pattern = re.compile(r"</body>", re.IGNORECASE)
        match = body_close_pattern.search(html)

        if match:
            return html[: match.start()] + tracking_script + "\n" + html[match.start() :]

        # Fallback: append to HTML
        logger.warning("no_body_tag_found", action="appending_script")
        return html + "\n" + tracking_script
