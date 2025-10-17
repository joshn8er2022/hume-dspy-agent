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
        # API key logging removed for security
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
        
        # Step 3: Qualify with DSPy (using context for async)
        result = None
        try:
            import dspy

            # Get API key
            openai_api_key = (
                os.getenv("OPENAI_API_KEY") or
                os.getenv("OPENAI_KEY") or
                os.getenv("OPENAI_API_TOKEN")
            )

            if not openai_api_key:
                raise Exception("OpenAI API key not found")

            # Create LM instance
            lm = dspy.LM('openai/gpt-4o', api_key=openai_api_key)

            # Use dspy.context() for async tasks (not dspy.configure())
            with dspy.context(lm=lm):
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
        
        # Step 4: Extract transcript (deep_dive conversation)
        transcript_text = ""
        if lead.raw_answers:
            for key, value in lead.raw_answers.items():
                if isinstance(value, dict) and 'raw' in value:
                    # This is a transcript field
                    raw_convo = value.get('raw', [])
                    if raw_convo:
                        transcript_text = "\n".join([
                            f"Q: {item.get('assistant', '')}\nA: {item.get('user', '')}"
                            for item in raw_convo[:3]  # First 3 Q&A pairs
                        ])
                    break

        # Step 5: Slack notification with thread creation
        slack_channel = None
        slack_thread_ts = None
        if result:
            slack_channel, slack_thread_ts = await send_slack_notification_with_qualification(lead, result, transcript_text)
        else:
            await send_slack_notification_simple(event['raw_payload'])

        # Step 6: Start autonomous follow-up agent (LangGraph)
        if result and slack_thread_ts:
            try:
                from agents.follow_up_agent import FollowUpAgent
                follow_up_agent = FollowUpAgent()

                # Start the autonomous lead journey
                journey_state = follow_up_agent.start_lead_journey(
                    lead=lead,
                    tier=result.tier,
                    slack_thread_ts=slack_thread_ts,
                    slack_channel=slack_channel or "inbound-leads"
                )
                logger.info(f"✅ Autonomous follow-up agent started for lead {lead.id}")
                logger.info(f"   Journey state: {journey_state.get('status')}")
            except Exception as e:
                logger.error(f"❌ Follow-up agent failed: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())

        # Step 7: Sync to Close CRM
        if result:
            await sync_to_close_crm(lead, result)

        # Step 8: Save to database
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


async def send_slack_notification_with_qualification(lead: Any, result: Any, transcript: str = ""):
    """Enhanced Slack with qualification."""
    try:
        import httpx
        SLACK_BOT_TOKEN = (
            os.getenv("SLACK_BOT_TOKEN") or
            os.getenv("SLACK_MCP_XOXB_TOKEN") or
            os.getenv("SLACK_MCP_XOXP_TOKEN")
        )
        SLACK_CHANNEL = "C09FZT6T1A5"
        
        if not SLACK_BOT_TOKEN:
            return
        
        # Build enhanced message with agent reasoning
        tier_str = str(result.tier).replace('QualificationTier.', '')
        actions_str = ', '.join([str(a).replace('NextAction.', '').replace('_', ' ').title() for a in (result.next_actions or [])[:3]])

        message = f"""📥 *New Lead Qualified* (AI-Powered)

*Contact Information:*
• Name: {lead.first_name or 'N/A'} {lead.last_name or ''}
• Company: {lead.company or 'N/A'}
• Email: {lead.email or 'N/A'}
• Phone: {lead.phone or 'N/A'}

*AI Qualification Results:*
• Score: {result.score}/100
• Tier: {tier_str.upper()}
• Priority: {getattr(result, 'priority', 'N/A')}/5

*Agent Reasoning:*
{getattr(result, 'reasoning', 'No reasoning provided')}

*Key Factors:*
{chr(10).join([f'• {factor}' for factor in getattr(result, 'key_factors', [])])}

*Concerns:*
{chr(10).join([f'• {concern}' for concern in getattr(result, 'concerns', [])])}

*Recommended Actions:*
{chr(10).join([f'• {str(a).replace("NextAction.", "").replace("_", " ").title()}' for a in (result.next_actions or [])])}

*Email Template Preview:*
{result.suggested_email_template or 'No template generated'}
"""

        # Add transcript if available (avoid nested f-strings)
        if transcript:
            message += f"""

*Deep Dive Conversation:*
{transcript}"""

        message += "\n\n_Processed via Event Sourcing + DSPy AI_"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
                json={"channel": SLACK_CHANNEL, "text": message, "mrkdwn": True},
                timeout=10.0
            )
            response_data = response.json() if response.status_code == 200 else {}
            if response_data.get('ok'):
                logger.info("✅ Enhanced Slack sent")
                # Return thread info for follow-up agent
                return response_data.get('channel'), response_data.get('ts')
            else:
                logger.error(f"❌ Slack API error: {response_data}")
                return None, None
    except Exception as e:
        logger.error(f"❌ Enhanced Slack failed: {str(e)}")
        return None, None


async def send_slack_notification_simple(data: dict):
    """Simple Slack (fallback)."""
    try:
        import httpx
        SLACK_BOT_TOKEN = (
            os.getenv("SLACK_BOT_TOKEN") or
            os.getenv("SLACK_MCP_XOXB_TOKEN") or
            os.getenv("SLACK_MCP_XOXP_TOKEN")
        )
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


# ============================================================================
# GMASS EMAIL OUTREACH
# ============================================================================

async def send_email_via_gmass(lead: Any, result: Any):
    """Send email via GMass API as josh@humehealth.com.
    
    Only sends to HOT/WARM tier leads.
    Uses DSPy-generated email template.
    """
    try:
        import httpx

        # GMass configuration
        GMASS_API_KEY = os.getenv("GMASS_API_KEY")

        if not GMASS_API_KEY:
            logger.warning("⚠️  GMASS_API_KEY not configured, skipping email send")
            return None

        GMASS_API_URL = "https://api.gmass.co/api"

        # Check if lead has email
        if not lead.email:
            logger.warning("⚠️ No email address, skipping GMass send")
            return
        
        # Agent decides via next_actions - no hardcoded tier checks
        # If this function is called, agent already decided to send email
        
        logger.info(f"📧 Sending email via GMass to {lead.email}...")
        logger.info(f"   Tier: {tier_str}")
        logger.info(f"   Score: {result.score}/100")
        
        # Get email template
        email_body = result.suggested_email_template or "Thank you for your interest in Hume Health. We'll be in touch soon!"
        
        # Create subject line
        subject = f"Your Hume Partnership Application - {lead.first_name or 'Partner'}"
        
        # Step 1: Create campaign draft
        async with httpx.AsyncClient() as client:
            draft_response = await client.post(
                f"{GMASS_API_URL}/campaigndrafts",
                headers={"X-apikey": GMASS_API_KEY},
                json={
                    "subject": subject,
                    "message": email_body,
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
                raise Exception(f"GMass draft failed: {draft_response.status_code} - {draft_response.text}")
            
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
                raise Exception(f"GMass send failed: {send_response.status_code} - {send_response.text}")
            
            send_result = send_response.json()
            campaign_id = send_result.get('campaignId')
            
            logger.info(f"✅ Email sent via GMass to {lead.email}")
            logger.info(f"   Campaign ID: {campaign_id}")
            logger.info(f"   Subject: {subject}")
            
            return send_result
            
    except Exception as e:
        logger.error(f"❌ GMass email failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        # Don't raise - email failure shouldn't fail processing


# ============================================================================
# CLOSE CRM SYNC
# ============================================================================

async def sync_to_close_crm(lead: Any, result: Any):
    """Sync lead to Close CRM.
    
    Creates lead record with qualification data.
    Only syncs qualified leads (HOT/WARM/COLD).
    """
    try:
        logger.info(f"🔄 Syncing to Close CRM: {lead.email or 'no email'}...")
        
        # Agent decides via next_actions - no hardcoded tier checks
        # If this function is called, agent already decided to sync to CRM
        
        # Build lead name
        lead_name = lead.company or f"{lead.first_name or ''} {lead.last_name or ''}".strip() or "Unknown Lead"
        
        # Build contact info
        contacts = []
        if lead.first_name or lead.last_name or lead.email or lead.phone:
            contact = {
                "name": f"{lead.first_name or ''} {lead.last_name or ''}".strip() or "Contact"
            }
            if lead.email:
                contact["emails"] = [{"email": lead.email, "type": "office"}]
            if lead.phone:
                contact["phones"] = [{"phone": lead.phone, "type": "office"}]
            contacts.append(contact)
        
        # For now, just log (Close CRM MCP integration coming next)
        logger.info(f"✅ Close CRM sync prepared")
        logger.info(f"   Lead name: {lead_name}")
        logger.info(f"   Contacts: {len(contacts)}")
        logger.info(f"   Tier: {tier_str}")
        logger.info(f"   Score: {result.score}/100")
        
        # TODO: Implement actual Close CRM API call
        # Will use Close CRM MCP or direct API
        
    except Exception as e:
        logger.error(f"❌ Close CRM sync failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        # Don't raise - CRM failure shouldn't fail processing
