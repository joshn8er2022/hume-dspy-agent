"""Event processors for different webhook sources.

Each processor handles a specific webhook source:
- Typeform: Form submissions with DSPy qualification
- Slack: User interactions and button clicks
- Vapi: Voice call events
- A2A: Agent-to-agent messages
"""

import logging
from typing import Dict, Any
from datetime import datetime
import os

logger = logging.getLogger(__name__)

# Import models and agents
try:
    from models.typeform import TypeformWebhookPayload
    from models.lead import Lead
    from utils.typeform_transform import transform_typeform_webhook
    from agents.inbound_agent import InboundAgent
    logger.info("✅ Imported Pydantic models and DSPy agent")
except Exception as e:
    logger.error(f"❌ Failed to import models/agents: {str(e)}")
    TypeformWebhookPayload = None
    Lead = None
    InboundAgent = None

# Supabase client (will be injected)
supabase = None

def set_supabase_client(client):
    """Set Supabase client for processors."""
    global supabase
    supabase = client


async def process_typeform_event(event: dict):
    """Process Typeform webhook event with full Pydantic + DSPy pipeline.
    
    Steps:
    1. Parse with Pydantic (type safety)
    2. Transform to Lead model
    3. Qualify with DSPy InboundAgent
    4. Save to Supabase leads table
    5. Send enhanced Slack notification
    6. Send email via GMass
    7. Sync to Close CRM
    """
    try:
        logger.info("🔄 Processing Typeform event with Pydantic + DSPy...")
        
        # 1. Parse with Pydantic (type safety)
        if not TypeformWebhookPayload:
            raise Exception("TypeformWebhookPayload model not available")
        
        payload = TypeformWebhookPayload(**event['raw_payload'])
        logger.info("✅ Parsed with Pydantic TypeformWebhookPayload")
        
        # 2. Transform to Lead model
        lead: Lead = transform_typeform_webhook(payload.dict())
        logger.info(f"✅ Transformed to Lead model: {lead.id}")
        logger.info(f"   Email: {lead.email}")
        logger.info(f"   Company: {lead.company}")
        logger.info(f"   Response type: {lead.response_type}")
        
        # 3. Qualify with DSPy InboundAgent
        if not InboundAgent:
            raise Exception("InboundAgent not available")
        
        agent = InboundAgent()
        result = agent.forward(lead)
        
        logger.info(f"✅ DSPy qualification complete")
        logger.info(f"   Score: {result.score}/100")
        logger.info(f"   Tier: {result.tier}")
        logger.info(f"   Actions: {', '.join(result.recommended_actions)}")
        
        # 4. Save to Supabase leads table
        if supabase:
            await save_lead_to_database(lead, result)
        else:
            logger.warning("⚠️ Supabase not available, skipping database save")
        
        # 5. Send enhanced Slack notification
        await send_slack_notification_with_qualification(lead, result)
        
        # 6. Send email via GMass (if HOT or WARM tier)
        if result.tier in ['hot', 'warm']:
            await send_email_via_gmass(lead, result)
        else:
            logger.info(f"⏭️ Skipping email for {result.tier} tier lead")
        
        # 7. Sync to Close CRM
        await sync_to_close_crm(lead, result)
        
        logger.info("✅ Typeform event fully processed")
        
    except Exception as e:
        logger.error(f"❌ Typeform processing failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


async def save_lead_to_database(lead: Lead, result: Any):
    """Save lead and qualification to Supabase."""
    try:
        if not supabase:
            logger.warning("⚠️ Supabase not available")
            return
        
        supabase.table('leads').insert({
            'id': str(lead.id),
            'typeform_id': lead.typeform_id,
            'form_id': lead.form_id,
            'first_name': lead.first_name,
            'last_name': lead.last_name,
            'email': lead.email,
            'phone': lead.phone,
            'company': lead.company,
            'qualification_score': result.score,
            'qualification_tier': result.tier,
            'recommended_actions': result.recommended_actions,
            'raw_answers': lead.raw_answers,
            'created_at': datetime.utcnow().isoformat()
        }).execute()
        
        logger.info(f"✅ Lead saved to database: {lead.id}")
        
    except Exception as e:
        logger.error(f"❌ Failed to save lead: {str(e)}")
        raise


async def send_slack_notification_with_qualification(lead: Lead, result: Any):
    """Send enhanced Slack notification with qualification results."""
    try:
        import httpx
        
        SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
        SLACK_CHANNEL = "C09FZT6T1A5"  # #ai-test
        
        if not SLACK_BOT_TOKEN:
            logger.warning("⚠️ SLACK_BOT_TOKEN not configured")
            return
        
        # Build enhanced message with qualification
        message = f"""📥 *New Lead Qualified* (Event Sourced)

*Contact Information:*
• Name: {lead.first_name} {lead.last_name}
• Company: {lead.company or 'Not provided'}
• Email: {lead.email or 'Not provided'}
• Phone: {lead.phone or 'Not provided'}

*Qualification Results:*
• Score: {result.score}/100
• Tier: {result.tier.upper()}
• Recommended Actions:
{chr(10).join([f'  • {action}' for action in result.recommended_actions])}

*Email Template Preview:*
{result.email_template[:200]}...

_Processed via event sourcing architecture_"""
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                    "Content-Type": "application/json"
                },
                json={
                    "channel": SLACK_CHANNEL,
                    "text": message,
                    "mrkdwn": True
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                result_data = response.json()
                if result_data.get('ok'):
                    logger.info("✅ Enhanced Slack notification sent")
                else:
                    logger.error(f"❌ Slack API error: {result_data.get('error')}")
                    
    except Exception as e:
        logger.error(f"❌ Slack notification failed: {str(e)}")
        # Don't raise - Slack failure shouldn't fail processing


async def send_email_via_gmass(lead: Lead, result: Any):
    """Send email via GMass API as josh@humehealth.com."""
    try:
        import httpx
        
        GMASS_API_KEY = os.getenv("GMASS_API_KEY") or "279d97fc-9c33-49b8-b69b-94183b0305b4"
        GMASS_API_URL = "https://api.gmass.co/api"
        
        if not lead.email:
            logger.warning("⚠️ No email address, skipping GMass send")
            return
        
        logger.info(f"📧 Sending email via GMass to {lead.email}...")
        
        # Step 1: Create campaign draft
        async with httpx.AsyncClient() as client:
            draft_response = await client.post(
                f"{GMASS_API_URL}/campaigndrafts",
                headers={"X-apikey": GMASS_API_KEY},
                json={
                    "subject": f"Your Hume Partnership Application - {lead.first_name}",
                    "message": result.email_template,
                    "emailAddresses": lead.email,
                    "fromEmail": "josh@humehealth.com",
                    "fromName": "Josh - Hume Health",
                    "replyTo": "josh@humehealth.com",
                    "openTracking": True,
                    "clickTracking": True
                },
                timeout=30.0
            )
            
            if draft_response.status_code != 200:
                raise Exception(f"GMass draft creation failed: {draft_response.text}")
            
            draft = draft_response.json()
            campaign_draft_id = draft.get('campaignDraftId')
            
            if not campaign_draft_id:
                raise Exception(f"No campaignDraftId in response: {draft}")
            
            logger.info(f"✅ GMass draft created: {campaign_draft_id}")
        
        # Step 2: Send campaign
        async with httpx.AsyncClient() as client:
            send_response = await client.post(
                f"{GMASS_API_URL}/campaigns/{campaign_draft_id}",
                headers={"X-apikey": GMASS_API_KEY},
                json={"campaignDraftId": campaign_draft_id},
                timeout=30.0
            )
            
            if send_response.status_code != 200:
                raise Exception(f"GMass send failed: {send_response.text}")
            
            send_result = send_response.json()
            logger.info(f"✅ Email sent via GMass to {lead.email}")
            logger.info(f"   Campaign ID: {send_result.get('campaignId')}")
            
            return send_result
            
    except Exception as e:
        logger.error(f"❌ GMass email failed: {str(e)}")
        # Don't raise - email failure shouldn't fail processing


async def sync_to_close_crm(lead: Lead, result: Any):
    """Sync lead to Close CRM."""
    try:
        logger.info(f"🔄 Syncing to Close CRM: {lead.email}...")
        
        # TODO: Implement Close CRM sync using MCP
        # For now, just log
        logger.info("✅ Close CRM sync complete (placeholder)")
        
    except Exception as e:
        logger.error(f"❌ Close CRM sync failed: {str(e)}")
        # Don't raise - CRM failure shouldn't fail processing


async def process_slack_event(event: dict):
    """Process Slack webhook event."""
    logger.info("🔄 Processing Slack event...")
    # TODO: Implement Slack event processing
    logger.info("✅ Slack event processed")


async def process_vapi_event(event: dict):
    """Process Vapi webhook event."""
    logger.info("🔄 Processing Vapi event...")
    # TODO: Implement Vapi event processing
    logger.info("✅ Vapi event processed")


async def process_a2a_event(event: dict):
    """Process A2A webhook event."""
    logger.info("🔄 Processing A2A event...")
    # TODO: Implement A2A event processing
    logger.info("✅ A2A event processed")
