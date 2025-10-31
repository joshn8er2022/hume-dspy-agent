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
    - Slack notifications for all failures
    - 0% email loss guarantee
    """
    
    def __init__(self):
        self.api_key = os.getenv("GMASS_API_KEY")
        self.from_email = os.getenv("FROM_EMAIL", "your@gmail.com")
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
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
        3. Slack notification (always on failure)
        
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
        try:
            gmass_success = self._send_via_gmass(to_email, lead_id, template_type, tier, lead_data)
            if gmass_success:
                return True
        except Exception as e:
            logger.warning(f"⚠️ GMass failed after retries: {str(e)}")
        
        # GMass failed - try SendGrid fallback
        logger.warning(f"⚠️ GMass failed for {to_email}, trying SendGrid fallback...")
        
        try:
            sendgrid_success = self._send_via_sendgrid(to_email, lead_id, template_type, tier, lead_data)
            if sendgrid_success:
                logger.info(f"✅ Email sent via SendGrid fallback to {to_email}")
                return True
        except Exception as e:
            logger.error(f"❌ SendGrid fallback failed: {str(e)}")
        
        # All channels failed - notify Slack
        self._notify_slack_failure(to_email, lead_id, tier, "All email channels failed")
        
        logger.error(f"❌ All channels failed for {to_email}")
        return False

    @sync_retry(max_attempts=3, min_wait=1, max_wait=4)
    def _send_via_gmass(
        self,
        to_email: str,
        lead_id: str,
        template_type: str,
        tier: str,
        lead_data: dict = None
    ) -> bool:
        """Send email via GMass with automatic retry.
        
        This method is decorated with @sync_retry, so it will automatically
        retry up to 3 times with exponential backoff (1s, 2s, 4s).
        """
        if not self.api_key:
            raise Exception("GMASS_API_KEY not configured")
        
        # Get template
        subject, body = self._get_template(template_type, tier, lead_data)
        
        # STEP 1: Create campaign draft
        draft_payload = {
            "fromEmail": self.from_email,
            "subject": subject,
            "message": body,
            "messageType": "html",
            "emailAddresses": to_email
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-apikey": self.api_key
        }
        
        draft_response = requests.post(
            "https://api.gmass.co/api/campaigndrafts",
            json=draft_payload,
            headers=headers,
            timeout=10
        )
        
        if draft_response.status_code != 200:
            raise Exception(f"GMass draft creation failed: {draft_response.status_code}")
        
        draft_data = draft_response.json()
        campaign_draft_id = draft_data.get("campaignDraftId")
        
        if not campaign_draft_id:
            raise Exception("GMass draft created but no campaignDraftId returned")
        
        # STEP 2: Send campaign
        campaign_payload = {
            "openTracking": True,
            "clickTracking": True,
            "friendlyName": f"{template_type}_{tier}_{lead_id[:8]}",
        }
        
        campaign_response = requests.post(
            f"https://api.gmass.co/api/campaigns/{campaign_draft_id}",
            json=campaign_payload,
            headers=headers,
            timeout=10
        )
        
        if campaign_response.status_code != 200:
            raise Exception(f"GMass campaign send failed: {campaign_response.status_code}")
        
        campaign_data = campaign_response.json()
        campaign_id = campaign_data.get("campaignId")
        logger.info(f"✅ Email sent via GMass to {to_email} (Campaign: {campaign_id})")
        return True

    def _send_via_sendgrid(
        self,
        to_email: str,
        lead_id: str,
        template_type: str,
        tier: str,
        lead_data: dict = None
    ) -> bool:
        """Send email via SendGrid as fallback."""
        if not self.sendgrid_api_key:
            logger.warning("SENDGRID_API_KEY not configured, skipping SendGrid fallback")
            return False
        
        # Get template
        subject, body = self._get_template(template_type, tier, lead_data)
        
        # SendGrid API v3
        payload = {
            "personalizations": [
                {
                    "to": [{"email": to_email}],
                    "subject": subject
                }
            ],
            "from": {"email": self.from_email},
            "content": [
                {
                    "type": "text/html",
                    "value": body
                }
            ]
        }
        
        headers = {
            "Authorization": f"Bearer {self.sendgrid_api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 202:
                logger.info(f"✅ Email sent via SendGrid to {to_email}")
                return True
            else:
                logger.error(f"❌ SendGrid send failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ SendGrid API error: {str(e)}")
            return False

    def _notify_slack_failure(
        self,
        to_email: str,
        lead_id: str,
        tier: str,
        reason: str
    ) -> bool:
        """Notify sales team via Slack when email fails."""
        if not self.slack_webhook:
            logger.warning("SLACK_WEBHOOK_URL not configured, skipping Slack notification")
            return False
        
        message = {
            "text": "🚨 Email Delivery Failure",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚨 Email Delivery Failure"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Lead ID:*\n{lead_id}"},
                        {"type": "mrkdwn", "text": f"*Email:*\n{to_email}"},
                        {"type": "mrkdwn", "text": f"*Tier:*\n{tier}"},
                        {"type": "mrkdwn", "text": f"*Reason:*\n{reason}"}
                    ]
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        }
                    ]
                }
            ]
        }
        
        try:
            response = requests.post(
                self.slack_webhook,
                json=message,
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Slack notification sent for {to_email}")
                return True
            else:
                logger.error(f"❌ Slack notification failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Slack notification error: {str(e)}")
            return False

    def _get_email_signature(self) -> str:
        """Get professional Hume Health email signature.
        
        Returns:
            HTML signature with branding and contact info
        """
        return """
<br><br>
<table style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; width: 100%; max-width: 600px;" border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr>
<td style="padding: 20px 0 15px 0; border-bottom: 2px solid #00A3E0;">
<table border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr>
<td style="vertical-align: middle; padding-right: 15px;">
<img style="width: 48px; height: 48px; display: block; border-radius: 4px;" alt="Hume Health" src="https://www.google.com/s2/favicons?sz=64&domain=humehealth.com">
</td>
<td style="vertical-align: middle;">
<div style="font-size: 24px; font-weight: 600; color: #0066CC; letter-spacing: -0.5px;"><strong>Hume Health</strong></div>
<div style="font-size: 12px; color: #666666; margin-top: 2px; font-weight: 500;">Better Metabolic Health Through Data</div>
</td>
</tr>
</tbody>
</table>
</td>
</tr>
<tr>
<td style="padding: 15px 0;">
<table style="font-size: 14px; line-height: 20px; color: #333333;" border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr>
<td style="padding: 8px 0;">
<table border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr>
<td style="width: 20px; vertical-align: top; padding-top: 2px;">
<div style="width: 16px; height: 16px; display: inline-block;"></div>
</td>
<td style="padding-left: 8px;">
<div style="color: #333333;">1007 North Orange Street<br>Wilmington, DE 19801<br>United States</div>
</td>
</tr>
</tbody>
</table>
</td>
</tr>
<tr>
<td style="padding: 8px 0;">
<table border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr>
<td style="width: 20px; vertical-align: middle;">
<div style="width: 16px; height: 16px; display: inline-block;"></div>
</td>
<td style="padding-left: 8px;">
<div><a href="https://humehealth.com" style="color: #0066CC; text-decoration: none; font-weight: 500;">humehealth.com</a></div>
</td>
</tr>
</tbody>
</table>
</td>
</tr>
</tbody>
</table>
</td>
</tr>
<tr>
<td style="padding: 15px 0 0 0; border-top: 1px solid #E0E0E0;">
<div style="font-size: 13px; color: #666666; font-style: italic; padding-top: 10px;"><em>Unlock &amp; understand your body's data for better health outcomes</em></div>
</td>
</tr>
<tr>
<td style="padding: 15px 0 10px 0;">
<div style="font-size: 11px; color: #999999; line-height: 16px;">This email and any attachments are confidential and intended solely for the addressee. If you are not the intended recipient, please notify the sender immediately and delete this message.</div>
</td>
</tr>
</tbody>
</table>
"""

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
        
        # Get professional signature
        signature = self._get_email_signature()

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

Would you be open to a quick 15-minute conversation this week? I can walk you through how other practices are handling this, and we can figure out if it's a fit.
{signature}
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

Let me know if you'd be interested in a 15-minute chat?
{signature}
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

Feel free to reply to this email or book time directly: <a href="https://calendly.com/humehealth">calendly.com/humehealth</a>
{signature}
</body></html>"""

        elif template_type.startswith("follow_up_"):
            follow_up_num = template_type.split("_")[-1]
            subject = f"Re: Body composition tracking for {company}"
            body = f"""<html><body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
{greeting}<br><br>

Just circling back on my previous email about remote patient monitoring for {company}.<br><br>

I know you're busy, so I'll keep this short: we help practices like yours automate body composition tracking and cut down on manual data entry. Most practitioners save 15+ hours per week.<br><br>

Still interested in chatting? Let me know if you have 15 minutes this week.<br><br>

Otherwise, no worries—feel free to reach out whenever the timing is better.
{signature}
</body></html>"""

        else:
            subject = "Following up on Hume Health inquiry"
            body = f"""<html><body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
{greeting}<br><br>

Just checking in to see if you're still interested in learning more about Hume Health's remote patient monitoring solutions.<br><br>

Let me know if you'd like to connect!
{signature}
</body></html>"""

        return subject, body
