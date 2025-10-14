"""Event processors for different webhook sources.

Simplified version - no Pydantic/DSPy yet, just get Slack working.
"""

import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# Supabase client (injected)
supabase = None

def set_supabase_client(client):
    """Set Supabase client for processors."""
    global supabase
    supabase = client


async def process_typeform_event(event: dict):
    """Process Typeform webhook event - SIMPLIFIED.
    
    Just send to Slack for now.
    Will add Pydantic + DSPy after Slack works.
    """
    try:
        logger.info("🔄 Processing Typeform event (simplified)...")
        
        # Send to Slack
        await send_slack_notification_simple(event['raw_payload'])
        
        logger.info("✅ Typeform event processed")
        
    except Exception as e:
        logger.error(f"❌ Typeform processing failed: {str(e)}")
        raise


async def send_slack_notification_simple(data: dict):
    """Send Typeform data to Slack - SIMPLIFIED."""
    try:
        import httpx
        
        SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
        SLACK_CHANNEL = "C09FZT6T1A5"  # #ai-test
        
        if not SLACK_BOT_TOKEN:
            logger.warning("⚠️ SLACK_BOT_TOKEN not configured")
            return
        
        # Extract key info
        event_type = data.get('event_type', 'unknown')
        form_response = data.get('form_response', {})
        form_id = form_response.get('form_id', 'unknown')
        answers = form_response.get('answers', [])
        
        # Build summary (first 10 fields)
        answer_text = ""
        for i, answer in enumerate(answers[:10]):
            field = answer.get('field', {})
            field_ref = field.get('ref', f"field_{i}")
            
            # Get answer value
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
        
        # Build message
        message = f"""📥 *New Typeform Webhook* (Event Sourced)

*Event Type:* {event_type}
*Form ID:* {form_id}
*Timestamp:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
*Total Fields:* {len(answers)}
*Storage:* {'Supabase' if supabase else 'File fallback'}

*Answers (first 10):*
{answer_text}

_Processed asynchronously in background_"""
        
        # Send to Slack
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
                else:
                    logger.error(f"❌ Slack API error: {result.get('error')}")
                    logger.error(f"   Response: {result}")
            else:
                logger.error(f"❌ Slack HTTP error: {response.status_code}")
                logger.error(f"   Response: {response.text}")
                
    except Exception as e:
        logger.error(f"❌ Slack notification failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


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
