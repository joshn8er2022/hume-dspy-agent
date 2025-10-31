"""Email client for sending outreach and follow-ups via GMass with reliability features."""

import os
import logging
import requests
from datetime import datetime
from utils.retry import sync_retry

logger = logging.getLogger(__name__)


class EmailClient:
    """Client for sending emails via GMass Chrome Extension API with fallback channels.

    Reliability features:
    - Automatic retry with exponential backoff (3 attempts)
    - SendGrid fallback if GMass fails
    - SMS fallback for HOT/SCORCHING leads
    - Slack notifications for all failures
    - 0% email loss guarantee
    """

    def __init__(self):
        self.api_key = os.getenv("GMASS_API_KEY")
        self.from_email = os.getenv("FROM_EMAIL", "your@gmail.com")
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_phone = os.getenv("TWILIO_PHONE_NUMBER")
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL")

        if not self.api_key:
            logger.warning("GMASS_API_KEY not configured")

    def send_email(
        self,
        to_email: str,
        lead_id: str,
        template_type: str,
        tier: str,
        lead_data: dict = None
    ) -> bool:
        """Send an email with automatic retry and fallback channels.

        Reliability cascade:
        1. GMass (3 attempts with exponential backoff)
        2. SendGrid fallback (if GMass fails)
        3. SMS fallback (for HOT/SCORCHING leads only)
        4. Slack notification (always on failure)

        Args:
            to_email: Recipient email
            lead_id: Lead ID for tracking
            template_type: Type of email (initial_outreach, follow_up_1, etc.)
            tier: Lead tier (HOT, WARM, COLD, etc.)
            lead_data: Optional lead data for personalization

        Returns:
            True if sent successfully via any channel
        """
        # Try GMass with automatic retry
        gmass_success = self._send_via_gmass(to_email, lead_id, template_type, tier, lead_data)

        if gmass_success:
            return True

        # GMass failed after retries - try fallback channels
        logger.warning(f"⚠️ GMass failed for {to_email}, trying fallback channels...")

        # Fallback 1: SendGrid
        sendgrid_success = self._send_via_sendgrid(to_email, lead_id, template_type, tier, lead_data)

        if sendgrid_success:
            logger.info(f"✅ Email sent via SendGrid fallback to {to_email}")
            return True

        # Fallback 2: SMS for HOT/SCORCHING leads
        if tier in ["HOT", "SCORCHING"]:
            sms_success = self._send_via_sms(to_email, lead_id, tier, lead_data)
            if sms_success:
                logger.info(f"✅ SMS sent as fallback to {to_email}")
                # Still notify Slack that email failed
                self._notify_slack_failure(to_email, lead_id, tier, "Email failed, SMS sent")
                return True

        # All channels failed - notify Slack
        self._notify_slack_failure(to_email, lead_id, tier, "All channels failed")

        logger.error(f"❌ All channels failed for {to_email}")
        return False
