"""Email service for sending notifications and transactional emails."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EmailTemplate(str, Enum):
    """Email template types."""

    TOKEN_EXPIRED = "token_expired"
    AD_REJECTED = "ad_rejected"
    CREDIT_LOW = "credit_low"
    CREDIT_DEPLETED = "credit_depleted"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    REPORT_READY = "report_ready"
    CREATIVE_READY = "creative_ready"
    LANDING_PAGE_READY = "landing_page_ready"
    GENERAL_NOTIFICATION = "general_notification"


@dataclass
class EmailMessage:
    """Email message data class."""

    to_email: str
    to_name: str | None
    subject: str
    template: EmailTemplate
    template_data: dict[str, Any]
    from_email: str | None = None
    from_name: str | None = None


class EmailProvider(ABC):
    """Abstract base class for email providers."""

    @abstractmethod
    async def send_email(self, message: EmailMessage) -> bool:
        """Send an email message."""
        pass


class ConsoleEmailProvider(EmailProvider):
    """Console email provider for development/testing."""

    async def send_email(self, message: EmailMessage) -> bool:
        """Log email to console instead of sending."""
        logger.info(
            f"[EMAIL] To: {message.to_email} ({message.to_name})\n"
            f"Subject: {message.subject}\n"
            f"Template: {message.template.value}\n"
            f"Data: {message.template_data}"
        )
        return True


class SESEmailProvider(EmailProvider):
    """AWS SES email provider for production."""

    def __init__(self) -> None:
        """Initialize SES client."""
        # Lazy import to avoid dependency issues
        try:
            import boto3
            self.ses_client = boto3.client("ses")
        except ImportError:
            logger.warning("boto3 not installed, SES email provider unavailable")
            self.ses_client = None

    async def send_email(self, message: EmailMessage) -> bool:
        """Send email via AWS SES."""
        if not self.ses_client:
            logger.error("SES client not available")
            return False

        settings = get_settings()
        from_email = message.from_email or settings.email_from_address
        from_name = message.from_name or settings.email_from_name

        try:
            # Render template to HTML
            html_content = self._render_template(message.template, message.template_data)
            text_content = self._render_text_template(message.template, message.template_data)

            response = self.ses_client.send_email(
                Source=f"{from_name} <{from_email}>",
                Destination={
                    "ToAddresses": [message.to_email],
                },
                Message={
                    "Subject": {"Data": message.subject, "Charset": "UTF-8"},
                    "Body": {
                        "Text": {"Data": text_content, "Charset": "UTF-8"},
                        "Html": {"Data": html_content, "Charset": "UTF-8"},
                    },
                },
            )
            logger.info(f"Email sent successfully: {response['MessageId']}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def _render_template(self, template: EmailTemplate, data: dict[str, Any]) -> str:
        """Render HTML email template."""
        # Base template structure
        base_html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #4F46E5; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9fafb; padding: 30px; border: 1px solid #e5e7eb; }}
        .footer {{ background: #f3f4f6; padding: 15px; text-align: center; font-size: 12px; color: #6b7280; border-radius: 0 0 8px 8px; }}
        .button {{ display: inline-block; background: #4F46E5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 15px 0; }}
        .alert {{ background: #FEF2F2; border: 1px solid #FECACA; padding: 15px; border-radius: 6px; margin: 15px 0; }}
        .success {{ background: #F0FDF4; border: 1px solid #BBF7D0; padding: 15px; border-radius: 6px; margin: 15px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AAE - Automated Ad Engine</h1>
        </div>
        <div class="content">
            {content}
        </div>
        <div class="footer">
            <p>© 2024 AAE. All rights reserved.</p>
            <p>You received this email because you have an account with AAE.</p>
        </div>
    </div>
</body>
</html>
"""
        content = self._get_template_content(template, data)
        return base_html.format(content=content)

    def _get_template_content(self, template: EmailTemplate, data: dict[str, Any]) -> str:
        """Get template-specific content."""
        templates = {
            EmailTemplate.TOKEN_EXPIRED: """
                <div class="alert">
                    <h2>⚠️ Ad Account Authorization Expired</h2>
                    <p>Your <strong>{platform}</strong> ad account <strong>"{account_name}"</strong> authorization has expired.</p>
                    <p>Please re-authorize to continue managing your ads.</p>
                    <a href="{action_url}" class="button">Re-authorize Now</a>
                </div>
            """,
            EmailTemplate.AD_REJECTED: """
                <div class="alert">
                    <h2>🚫 Ad Rejected</h2>
                    <p>Your ad <strong>"{ad_name}"</strong> was rejected by <strong>{platform}</strong>.</p>
                    <p><strong>Reason:</strong> {rejection_reason}</p>
                    <a href="{action_url}" class="button">View Campaign</a>
                </div>
            """,
            EmailTemplate.CREDIT_LOW: """
                <div class="alert">
                    <h2>💳 Credit Balance Running Low</h2>
                    <p>Your credit balance is <strong>{current_balance} credits</strong>, which is below the warning threshold.</p>
                    <p>Consider recharging to avoid service interruption.</p>
                    <a href="{action_url}" class="button">Recharge Now</a>
                </div>
            """,
            EmailTemplate.CREDIT_DEPLETED: """
                <div class="alert">
                    <h2>🚨 Credit Balance Depleted</h2>
                    <p>Your credit balance has been depleted.</p>
                    <p>Please recharge to continue using AI features.</p>
                    <a href="{action_url}" class="button">Recharge Now</a>
                </div>
            """,
            EmailTemplate.PAYMENT_SUCCESS: """
                <div class="success">
                    <h2>✅ Payment Successful</h2>
                    <p>Your payment of <strong>¥{amount}</strong> was successful.</p>
                    <p><strong>{credits_added} credits</strong> have been added to your account.</p>
                    <a href="{action_url}" class="button">View Balance</a>
                </div>
            """,
            EmailTemplate.REPORT_READY: """
                <h2>📊 {report_type} Report Ready</h2>
                <p>Your {report_type} report for <strong>{report_date}</strong> is ready to view.</p>
                <a href="{action_url}" class="button">View Report</a>
            """,
            EmailTemplate.CREATIVE_READY: """
                <h2>🎨 Creatives Generated</h2>
                <p><strong>{creative_count}</strong> new creative(s) have been generated and are ready for review.</p>
                <a href="{action_url}" class="button">View Creatives</a>
            """,
            EmailTemplate.LANDING_PAGE_READY: """
                <h2>📄 Landing Page Ready</h2>
                <p>Your landing page <strong>"{landing_page_name}"</strong> has been generated and is ready for review.</p>
                <a href="{action_url}" class="button">View Landing Page</a>
            """,
            EmailTemplate.GENERAL_NOTIFICATION: """
                <h2>{title}</h2>
                <p>{message}</p>
                {action_button}
            """,
        }

        template_str = templates.get(template, templates[EmailTemplate.GENERAL_NOTIFICATION])

        # Add action button for general notifications
        if template == EmailTemplate.GENERAL_NOTIFICATION:
            action_button = ""
            if data.get("action_url") and data.get("action_text"):
                action_button = f'<a href="{data["action_url"]}" class="button">{data["action_text"]}</a>'
            data["action_button"] = action_button

        try:
            return template_str.format(**data)
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}")
            return f"<p>{data.get('message', 'You have a new notification.')}</p>"

    def _render_text_template(self, template: EmailTemplate, data: dict[str, Any]) -> str:
        """Render plain text email template."""
        title = data.get("title", "Notification")
        message = data.get("message", "You have a new notification.")
        action_url = data.get("action_url", "")

        text = f"{title}\n\n{message}"
        if action_url:
            text += f"\n\nView more: {action_url}"

        return text


class EmailService:
    """Email service for sending notifications."""

    def __init__(self, provider: EmailProvider | None = None) -> None:
        """Initialize email service with provider."""
        settings = get_settings()

        if provider:
            self.provider = provider
        elif settings.email_provider == "ses":
            self.provider = SESEmailProvider()
        else:
            # Default to console provider for development
            self.provider = ConsoleEmailProvider()

    async def send_notification_email(
        self,
        to_email: str,
        to_name: str | None,
        subject: str,
        template: EmailTemplate,
        template_data: dict[str, Any],
    ) -> bool:
        """Send a notification email."""
        message = EmailMessage(
            to_email=to_email,
            to_name=to_name,
            subject=subject,
            template=template,
            template_data=template_data,
        )
        return await self.provider.send_email(message)

    async def send_token_expired_email(
        self,
        to_email: str,
        to_name: str | None,
        platform: str,
        account_name: str,
        action_url: str,
    ) -> bool:
        """Send token expired notification email."""
        return await self.send_notification_email(
            to_email=to_email,
            to_name=to_name,
            subject=f"[Action Required] {platform.title()} Ad Account Authorization Expired",
            template=EmailTemplate.TOKEN_EXPIRED,
            template_data={
                "platform": platform.title(),
                "account_name": account_name,
                "action_url": action_url,
            },
        )

    async def send_credit_low_email(
        self,
        to_email: str,
        to_name: str | None,
        current_balance: str,
        action_url: str,
    ) -> bool:
        """Send credit low notification email."""
        return await self.send_notification_email(
            to_email=to_email,
            to_name=to_name,
            subject="[Warning] Your Credit Balance is Running Low",
            template=EmailTemplate.CREDIT_LOW,
            template_data={
                "current_balance": current_balance,
                "action_url": action_url,
            },
        )

    async def send_credit_depleted_email(
        self,
        to_email: str,
        to_name: str | None,
        action_url: str,
    ) -> bool:
        """Send credit depleted notification email."""
        return await self.send_notification_email(
            to_email=to_email,
            to_name=to_name,
            subject="[Urgent] Your Credit Balance Has Been Depleted",
            template=EmailTemplate.CREDIT_DEPLETED,
            template_data={
                "action_url": action_url,
            },
        )

    async def send_payment_success_email(
        self,
        to_email: str,
        to_name: str | None,
        amount: str,
        credits_added: str,
        action_url: str,
    ) -> bool:
        """Send payment success notification email."""
        return await self.send_notification_email(
            to_email=to_email,
            to_name=to_name,
            subject="Payment Successful - Credits Added",
            template=EmailTemplate.PAYMENT_SUCCESS,
            template_data={
                "amount": amount,
                "credits_added": credits_added,
                "action_url": action_url,
            },
        )

    async def send_ad_rejected_email(
        self,
        to_email: str,
        to_name: str | None,
        platform: str,
        ad_name: str,
        rejection_reason: str,
        action_url: str,
    ) -> bool:
        """Send ad rejected notification email."""
        return await self.send_notification_email(
            to_email=to_email,
            to_name=to_name,
            subject=f"[Action Required] Ad Rejected on {platform.title()}",
            template=EmailTemplate.AD_REJECTED,
            template_data={
                "platform": platform.title(),
                "ad_name": ad_name,
                "rejection_reason": rejection_reason,
                "action_url": action_url,
            },
        )
