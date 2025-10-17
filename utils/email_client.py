"""Email client for sending outreach and follow-ups via GMass."""

import os
import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailClient:
    """Client for sending emails via GMass Chrome Extension API.

    GMass uses your personal Gmail account for sending, which is perfect
    for B2B outreach as emails come from your actual inbox.
    """

    def __init__(self):
        self.api_key = os.getenv("GMASS_API_KEY")
        self.from_email = os.getenv("FROM_EMAIL", "your@gmail.com")

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
        """Send an email via GMass using the correct two-step API process.

        GMass API Process:
        1. Create draft: POST /api/campaigndrafts → get campaignDraftId
        2. Send campaign: POST /api/campaigns/{campaignDraftId}

        GMass sends emails through your Gmail account, which improves deliverability
        and makes the emails appear more personal (not from a corporate domain).

        Args:
            to_email: Recipient email
            lead_id: Lead ID for tracking
            template_type: Type of email (initial_outreach, follow_up_1, etc.)
            tier: Lead tier (HOT, WARM, COLD)
            lead_data: Optional lead data for personalization (first_name, company)

        Returns:
            True if sent successfully
        """
        if not self.api_key:
            logger.warning("GMASS_API_KEY not configured, skipping email send")
            return False

        # Get template based on type and tier
        subject, body = self._get_template(template_type, tier, lead_data)

        try:
            # STEP 1: Create campaign draft
            # Docs: https://www.gmass.co/api
            draft_payload = {
                "fromEmail": self.from_email,
                "subject": subject,
                "message": body,
                "messageType": "html",  # HTML with auto-generated plain text
                "emailAddresses": to_email
            }

            headers = {
                "Content-Type": "application/json",
                "X-apikey": self.api_key  # GMass uses X-apikey header per API spec
            }

            # Create draft
            draft_response = requests.post(
                "https://api.gmass.co/api/campaigndrafts",
                json=draft_payload,
                headers=headers,
                timeout=10
            )

            if draft_response.status_code != 200:
                logger.error(f"❌ GMass draft creation failed: {draft_response.status_code} - {draft_response.text}")
                return False

            draft_data = draft_response.json()
            campaign_draft_id = draft_data.get("campaignDraftId")

            if not campaign_draft_id:
                logger.error("❌ GMass draft created but no campaignDraftId returned")
                logger.error(f"   Response: {draft_data}")
                return False

            logger.info(f"✅ GMass draft created: {campaign_draft_id}")

            # STEP 2: Send campaign
            campaign_payload = {
                "openTracking": True,
                "clickTracking": True,
                "friendlyName": f"{template_type}_{tier}_{lead_id[:8]}",
                # Omit sendTime to send immediately
            }

            campaign_response = requests.post(
                f"https://api.gmass.co/api/campaigns/{campaign_draft_id}",
                json=campaign_payload,
                headers=headers,
                timeout=10
            )

            if campaign_response.status_code == 200:
                campaign_data = campaign_response.json()
                campaign_id = campaign_data.get("campaignId")
                logger.info(f"✅ Email sent via GMass to {to_email}")
                logger.info(f"   Campaign ID: {campaign_id}")
                logger.info(f"   Template: {template_type}, Tier: {tier}")
                return True
            else:
                logger.error(f"❌ GMass campaign send failed: {campaign_response.status_code} - {campaign_response.text}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ GMass API request error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Email send error: {str(e)}")
            return False

    def _get_template(self, template_type: str, tier: str, lead_data: dict = None) -> tuple[str, str]:
        """Get email template based on type and tier.

        Templates follow Hume Health brand voice: conversational consultant,
        not robotic AI or pushy salesperson. Focus on practitioner pain points.

        Returns:
            Tuple of (subject, body)
        """
        lead_data = lead_data or {}
        company = lead_data.get("company", "your practice")
        first_name = lead_data.get("first_name", "")

        # Personalize greeting
        greeting = f"Hi {first_name}," if first_name else "Hi there,"

        if template_type == "initial_outreach":
            # Tier-based urgency and approach
            if tier == "HOT":
                subject = "Body composition tracking for your practice"
                body = f"""<html><body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
{greeting}<br><br>

Thanks for reaching out about remote patient monitoring for {company}. Based on what you shared, it sounds like you're dealing with the classic challenge of manual data collection eating up your time.<br><br>

We work with a lot of practices in similar situations, and the common thread is always the same: practitioners want to focus on patients, not spreadsheets.<br><br>

<strong>Here's what we typically see work well:</strong><br>
• Body Pod for clinical-grade body composition (98% accuracy, but more importantly: daily-use tracking so you can spot trends, not just snapshots)<br>
• Hume Connect platform to automatically pull everything into one view—saves our practitioners about 15+ hours per week on data analysis<br><br>

Not trying to sell you anything yet—just want to understand your specific workflow and see if this makes sense for {company}.<br><br>

Would you be open to a quick 15-minute conversation this week? I can walk you through how other practices are handling this, and we can figure out if it's a fit.<br><br>

Best,<br>
Hume Health Team<br>
<a href="mailto:{self.from_email}">{self.from_email}</a>
</body></html>"""

            elif tier == "WARM":
                subject = "Quick question about patient data tracking"
                body = f"""<html><body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
{greeting}<br><br>

I saw your inquiry about body composition tracking for {company}. Sounds like you might be in the same boat as a lot of practices we talk to—spending too much time manually tracking patient metrics.<br><br>

We've built a remote patient monitoring platform (Hume Connect) that integrates with clinical-grade hardware (Body Pod) to automate a lot of that. The key benefit isn't just accuracy—it's the daily engagement piece that improves patient adherence.<br><br>

<strong>Quick snapshot:</strong><br>
• Body Pod: 98% accurate BIA scale for daily body comp tracking<br>
• Hume Connect: HIPAA-compliant dashboard that auto-syncs patient data (saves ~15 hours/week for most practitioners)<br>
• Focus on trends, not single-point measurements (which is what actually drives patient outcomes)<br><br>

Not sure if this aligns with your needs, but happy to hop on a quick call to discuss your specific workflow.<br><br>

Let me know if you'd be interested in a 15-minute chat?<br><br>

Best,<br>
Hume Health Team<br>
<a href="mailto:{self.from_email}">{self.from_email}</a>
</body></html>"""

            else:  # COLD or UNQUALIFIED
                subject = "Following up on your Hume Health inquiry"
                body = f"""<html><body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
{greeting}<br><br>

Thanks for your interest in Hume Health's body composition tracking solutions.<br><br>

We specialize in helping healthcare practitioners with remote patient monitoring—specifically for practices that need daily body composition data (not just one-off measurements).<br><br>

<strong>Our typical fit:</strong><br>
• Weight loss clinics, diabetes management, functional medicine practices<br>
• 50+ patients who need regular monitoring<br>
• Practitioners looking to save time on data collection and improve patient adherence<br><br>

If that sounds like your practice, I'd be happy to set up a brief call to discuss how we can help.<br><br>

Feel free to reply to this email or book time directly: <a href="https://calendly.com/humehealth">calendly.com/humehealth</a><br><br>

Best,<br>
Hume Health Team<br>
<a href="mailto:{self.from_email}">{self.from_email}</a>
</body></html>"""

        elif template_type.startswith("follow_up_"):
            follow_up_num = template_type.split("_")[-1]
            subject = f"Re: Body composition tracking for {company}"
            body = f"""<html><body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
{greeting}<br><br>

Just circling back on my previous email about remote patient monitoring for {company}.<br><br>

I know you're busy, so I'll keep this short: we help practices like yours automate body composition tracking and cut down on manual data entry. Most practitioners save 15+ hours per week.<br><br>

Still interested in chatting? Let me know if you have 15 minutes this week.<br><br>

Otherwise, no worries—feel free to reach out whenever the timing is better.<br><br>

Best,<br>
Hume Health Team<br>
<a href="mailto:{self.from_email}">{self.from_email}</a>
</body></html>"""

        else:
            subject = "Following up on Hume Health inquiry"
            body = f"""<html><body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
{greeting}<br><br>

Just checking in to see if you're still interested in learning more about Hume Health's remote patient monitoring solutions.<br><br>

Let me know if you'd like to connect!<br><br>

Best,<br>
Hume Health Team
</body></html>"""

        return subject, body
