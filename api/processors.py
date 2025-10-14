"""Event processors for different webhook sources.

Incremental approach:
1. Simple Slack notification (working)
2. Add Pydantic parsing (next)
3. Add DSPy qualification (after Pydantic works)
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Supabase client (injected)
supabase = None

def set_supabase_client(client):
    """Set Supabase client for processors."""
    global supabase
    supabase = client


async def process_typeform_event(event: dict):
    """Process Typeform webhook event with Pydantic + DSPy.
    
    Steps:
    1. Parse with Pydantic (type safety)
    2. Transform to Lead model
    3. Qualify with DSPy InboundAgent
    4. Send enhanced Slack notification
    5. Save to database
    """
    try:
        logger.info("🔄 Processing Typeform event with Pydantic + DSPy...")
        
        # Step 1: Parse with Pydantic
        try:
            from models.typeform import TypeformWebhookPayload
            payload = TypeformWebhookPayload(**event['raw_payload'])
            logger.info("✅ Parsed with Pydantic TypeformWebhookPayload")
        except Exception as e:
            logger.error(f"❌ Pydantic parsing failed: {str(e)}")
            # Fallback: Send simple Slack notification
            await send_slack_notification_simple(event['raw_payload'])
            raise
        
        # Step 2: Transform to Lead model
        try:
            from models.lead import Lead
            from utils.typeform_transform import transform_typeform_webhook
            lead: Lead = transform_typeform_webhook(payload.dict())
            logger.info(f"✅ Transformed to Lead model: {lead.id}")
            logger.info(f"   Email: {lead.email}")
            logger.info(f"   Company: {lead.company}")
        except Exception as e:
            logger.error(f"❌ Lead transformation failed: {str(e)}")
            # Fallback: Send simple Slack notification
            await send_slack_notification_simple(event['raw_payload'])
            raise
        
        # Step 3: Qualify with DSPy InboundAgent
        try:
            # Import DSPy agent with proper error handling
            import sys
            import os
            
            # Add project root to path if needed
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            
            from agents.inbound_agent import InboundAgent
            
            agent = InboundAgent()
            result = agent.forward(lead)
            
            logger.info(f"✅ DSPy qualification complete")
            logger.info(f"   Score: {result.score}/100")
            logger.info(f"   Tier: {result.tier}")
            logger.info(f"   Actions: {', '.join(result.recommended_actions)}")
        except Exception as e:
            logger.error(f"❌ DSPy qualification failed: {str(e)}")
            logger.error(f"   Error type: {type(e).__name__}")
            import traceback
            logger.error(traceback.format_exc())
            # Fallback: Send simple Slack notification
            await send_slack_notification_simple(event['raw_payload'])
            raise
        
        # Step 4: Send enhanced Slack notification
        await send_slack_notification_with_qualification(lead, result)
        
        # Step 5: Save to database
        if supabase:
            await save_lead_to_database(lead, result)
        
        logger.info("✅ Typeform event fully processed")
        
    except Exception as e:
        logger.error(f"❌ Typeform processing failed: {str(e)}")
        # Don't raise - we already sent fallback Slack notification


async def save_lead_to_database(lead: Any, result: Any):
    """Save lead and qualification to Supabase."""
    try:
        if not supabase:
            logger.warning("⚠️ Supabase not available")
            return
        
        supabase.table('leads').insert({
            'id': str(lead.id),
            'typeform_id': lead.typeform_id,
            'form_id': getattr(lead, 'form_id', 'unknown'),
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
        # Don't raise - database failure shouldn't fail processing


async def send_slack_notification_with_qualification(lead: Any, result: Any):
    """Send enhanced Slack notification with qualification results."""
    try:
        import httpx
        
        SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
        SLACK_CHANNEL = "C09FZT6T1A5"  # #ai-test
        
        if not SLACK_BOT_TOKEN:
            logger.warning("⚠️ SLACK_BOT_TOKEN not configured")
            return
        
        # Build enhanced message
        message = f"""📥 *New Lead Qualified* (Event Sourced + DSPy)

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

_Processed via event sourcing + DSPy qualification_"""
        
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
        logger.error(f"❌ Enhanced Slack notification failed: {str(e)}")
        # Fallback to simple notification
        await send_slack_notification_simple(event.get('raw_payload', {}))


async def send_slack_notification_simple(data: dict):
    """Send simple Slack notification (fallback)."""
    try:
        import httpx
        
        SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
        SLACK_CHANNEL = "C09FZT6T1A5"
        
        if not SLACK_BOT_TOKEN:
            return
        
        event_type = data.get('event_type', 'unknown')
        form_response = data.get('form_response', {})
        form_id = form_response.get('form_id', 'unknown')
        answers = form_response.get('answers', [])
        
        answer_text = ""
        for i, answer in enumerate(answers[:10]):
            field = answer.get('field', {})
            field_ref = field.get('ref', f"field_{i}")
            
            if answer.get('type') == 'text':
                value = answer.get('text', 'N/A')
            elif answer.get('type') == 'email':
                value = answer.get('email', 'N/A')
            elif answer.get('type') == 'phone_number':
                value = answer.get('phone_number', 'N/A')
            elif answer.get('type') == 'choice':
                value = answer.get('choice', {}).get('label', 'N/A')
            elif answer.get('type') == 'number':
                value = str(answer.get('number', 'N/A'))
            else:
                value = str(answer.get(answer.get('type', 'text'), 'N/A'))
            
            answer_text += f"*{field_ref}:* {value}\n"
        
        if len(answers) > 10:
            answer_text += f"\n_... and {len(answers) - 10} more fields_"
        
        message = f"""📥 *New Typeform Webhook* (Event Sourced)

*Event Type:* {event_type}
*Form ID:* {form_id}
*Timestamp:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
*Total Fields:* {len(answers)}

*Answers (first 10):*
{answer_text}

_Processed asynchronously in background_"""
        
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
                result = response.json()
                if result.get('ok'):
                    logger.info("✅ Slack notification sent successfully")
                    
    except Exception as e:
        logger.error(f"❌ Slack notification failed: {str(e)}")


async def process_slack_event(event: dict):
    """Process Slack webhook event."""
    logger.info("🔄 Processing Slack event...")
    logger.info("✅ Slack event processed")


async def process_vapi_event(event: dict):
    """Process Vapi webhook event."""
    logger.info("🔄 Processing Vapi event...")
    logger.info("✅ Vapi event processed")


async def process_a2a_event(event: dict):
    """Process A2A webhook event."""
    logger.info("🔄 Processing A2A event...")
    logger.info("✅ A2A event processed")
