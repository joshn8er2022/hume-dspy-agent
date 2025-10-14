"""Event processors with Pydantic + DSPy.

DSPy Configuration:
- Must call dspy.configure(lm=...) before using InboundAgent
- Uses OpenAI GPT-4o by default
- Falls back to simple Slack if DSPy unavailable
"""

import logging
import os
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# Supabase client
supabase = None

def set_supabase_client(client):
    global supabase
    supabase = client

# DSPy configuration (lazy initialization)
dspy_configured = False


def configure_dspy():
    """Configure DSPy with OpenAI LM."""
    global dspy_configured

    if dspy_configured:
        return True

    try:
        import dspy

        # Try multiple environment variable names
        openai_api_key = (
            os.getenv("OPENAI_API_KEY") or
            os.getenv("OPENAI_KEY") or
            os.getenv("OPENAI_API_TOKEN") or
            os.getenv("openai_api_key") or
            os.getenv("OPENAI")
        )

        if not openai_api_key:
            logger.error("❌ OpenAI API key not found in environment")
            logger.error("   Tried: OPENAI_API_KEY, OPENAI_KEY, OPENAI_API_TOKEN, openai_api_key, OPENAI")
            logger.error("   Available env vars: " + ", ".join([k for k in os.environ.keys() if 'OPENAI' in k.upper()]))
            return False

        # Configure DSPy with OpenAI LM
        lm = dspy.LM('openai/gpt-4o', api_key=openai_api_key)
        dspy.configure(lm=lm)

        logger.info("✅ DSPy configured with OpenAI GPT-4o")
        logger.info(f"   API key: {openai_api_key[:10]}...")
        dspy_configured = True
        return True

    except Exception as e:
        logger.error(f"❌ DSPy configuration failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def process_typeform_event(event: dict):
    """Process Typeform event with Pydantic + DSPy."""
    try:
        logger.info("🔄 Processing Typeform event with Pydantic + DSPy...")
        
        # Step 1: Parse with Pydantic
        try:
            from models.typeform import TypeformWebhookPayload
            payload = TypeformWebhookPayload(**event['raw_payload'])
            logger.info("✅ Parsed with Pydantic")
        except Exception as e:
            logger.error(f"❌ Pydantic failed: {str(e)}")
            await send_slack_notification_simple(event['raw_payload'])
            return
        
        # Step 2: Transform to Lead
        try:
            from models.lead import Lead
            from utils.typeform_transform import transform_typeform_webhook
            lead: Lead = transform_typeform_webhook(payload.dict())
            logger.info(f"✅ Lead model: {lead.id}")
            logger.info(f"   Email: {lead.email}")
            logger.info(f"   Company: {lead.company}")
        except Exception as e:
            logger.error(f"❌ Lead transform failed: {str(e)}")
            await send_slack_notification_simple(event['raw_payload'])
            return
        
        # Step 3: Qualify with DSPy
        result = None
        try:
            # Configure DSPy if not already configured
            if not configure_dspy():
                raise Exception("DSPy configuration failed")
            
            from agents.inbound_agent import InboundAgent
            agent = InboundAgent()
            result = agent.forward(lead)
            
            logger.info(f"✅ DSPy qualification complete")
            logger.info(f"   Score: {result.score}/100")
            logger.info(f"   Tier: {result.tier}")
        except Exception as e:
            logger.error(f"❌ DSPy failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            # Continue without qualification
        
        # Step 4: Slack notification
        if result:
            await send_slack_notification_with_qualification(lead, result)
        else:
            await send_slack_notification_simple(event['raw_payload'])
        
        # Step 5: Save to database
        if result and supabase:
            await save_lead_to_database(lead, result)
        
        logger.info("✅ Typeform event processed")
        
    except Exception as e:
        logger.error(f"❌ Processing failed: {str(e)}")


async def save_lead_to_database(lead: Any, result: Any):
    """Save lead to Supabase."""
    try:
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
            'recommended_actions': result.next_actions,
            'raw_answers': lead.raw_answers
        }).execute()
        logger.info(f"✅ Lead saved: {lead.id}")
    except Exception as e:
        logger.error(f"❌ Save failed: {str(e)}")


async def send_slack_notification_with_qualification(lead: Any, result: Any):
    """Enhanced Slack with qualification."""
    try:
        import httpx
        SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
        SLACK_CHANNEL = "C09FZT6T1A5"
        
        if not SLACK_BOT_TOKEN:
            return
        
        message = f"""📥 *New Lead Qualified*

*Contact:*
• {lead.first_name} {lead.last_name}
• {lead.company or 'N/A'}
• {lead.email or 'N/A'}
• {lead.phone or 'N/A'}

*Qualification:*
• Score: {result.score}/100
• Tier: {result.tier.upper()}
• Actions: {', '.join(result.next_actions[:3])}

*Email Preview:*
{result.suggested_email_template[:150]}..."""
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
                json={"channel": SLACK_CHANNEL, "text": message, "mrkdwn": True},
                timeout=10.0
            )
            if response.status_code == 200 and response.json().get('ok'):
                logger.info("✅ Enhanced Slack sent")
    except Exception as e:
        logger.error(f"❌ Enhanced Slack failed: {str(e)}")


async def send_slack_notification_simple(data: dict):
    """Simple Slack (fallback)."""
    try:
        import httpx
        SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
        SLACK_CHANNEL = "C09FZT6T1A5"
        
        if not SLACK_BOT_TOKEN:
            return
        
        form_response = data.get('form_response', {})
        answers = form_response.get('answers', [])
        
        answer_text = ""
        for i, answer in enumerate(answers[:10]):
            field = answer.get('field', {})
            field_ref = field.get('ref', f"field_{i}")
            value = answer.get('text') or answer.get('email') or answer.get('phone_number') or str(answer.get('choice', {}).get('label', 'N/A'))
            answer_text += f"*{field_ref}:* {value}\n"
        
        message = f"""📥 *New Typeform Webhook*

*Total Fields:* {len(answers)}

*First 10:*
{answer_text}"""
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
                json={"channel": SLACK_CHANNEL, "text": message, "mrkdwn": True},
                timeout=10.0
            )
            if response.status_code == 200 and response.json().get('ok'):
                logger.info("✅ Simple Slack sent")
    except Exception as e:
        logger.error(f"❌ Simple Slack failed: {str(e)}")


async def process_slack_event(event: dict):
    logger.info("🔄 Processing Slack event...")
    logger.info("✅ Slack event processed")

async def process_vapi_event(event: dict):
    logger.info("🔄 Processing Vapi event...")
    logger.info("✅ Vapi event processed")

async def process_a2a_event(event: dict):
    logger.info("🔄 Processing A2A event...")
    logger.info("✅ A2A event processed")
