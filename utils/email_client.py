"""Email client for sending outreach and follow-ups."""

import os
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailClient:
    """Client for sending emails via GMass API."""

    def __init__(self):
        self.api_key = os.getenv("GMASS_API_KEY")
        self.api_base = "https://api.gmass.co/api"
        self.from_email = os.getenv("FROM_EMAIL", "hello@yourcompany.com")

    def send_email(
        self,
        to_email: str,
        lead_id: str,
        template_type: str,
        tier: str
    ) -> bool:
        """Send an email via GMass.

        Args:
            to_email: Recipient email
            lead_id: Lead ID for tracking
            template_type: Type of email (initial_outreach, follow_up_1, etc.)
            tier: Lead tier

        Returns:
            True if sent successfully
        """
        if not self.api_key:
            logger.warning("GMASS_API_KEY not configured, skipping email send")
            return False

        # Get template based on type
        subject, body = self._get_template(template_type, tier)

        try:
            # GMass API call (simplified - adjust to actual GMass API)
            payload = {
                "apiKey": self.api_key,
                "from": self.from_email,
                "to": to_email,
                "subject": subject,
                "body": body,
                "trackOpens": True,
                "trackClicks": True,
                "customHeaders": {
                    "X-Lead-ID": lead_id,
                    "X-Template-Type": template_type
                }
            }

            response = requests.post(
                f"{self.api_base}/campaigns",
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                logger.info(f"Email sent successfully to {to_email} (template: {template_type})")
                return True
            else:
                logger.error(f"GMass API error: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Email send error: {str(e)}")
            return False

    def _get_template(self, template_type: str, tier: str) -> tuple[str, str]:
        """Get email template based on type and tier.

        Returns:
            Tuple of (subject, body)
        """
        # These should ideally come from a database or DSPy generation
        # For now, simple templates based on type

        if template_type == "initial_outreach":
            subject = "Quick question about your body composition tracking"
            body = f"""Hi there,

I noticed you're interested in body composition tracking for your practice.

I'd love to learn more about your current workflow and see if we can help.

Would you be open to a quick 15-minute chat this week?

Best,
Your Name
"""

        elif template_type.startswith("follow_up_"):
            follow_up_num = template_type.split("_")[-1]
            subject = f"Re: Body composition tracking (follow-up #{follow_up_num})"
            body = f"""Hi again,

Just wanted to follow up on my previous email about body composition tracking.

I'd still love to connect and learn about your needs.

Let me know if you have 15 minutes for a quick call?

Best,
Your Name
"""

        else:
            subject = "Following up"
            body = "Just checking in..."

        return subject, body
