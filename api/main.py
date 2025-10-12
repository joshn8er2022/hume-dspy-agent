"""FastAPI application for Hume DSPy Agent.

Provides REST API endpoints for:
- Lead qualification
- Typeform webhook processing
- Health checks
"""

import os
import logging
import time
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import requests

from models import Lead, QualificationResult
from agents.inbound_agent import InboundAgent
from utils.typeform_transform import transform_typeform_webhook

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Hume DSPy Agent",
    description="AI-powered lead qualification system using DSPy",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# STARTUP & HEALTH
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info('=' * 80)
    logger.info('🚀 HUME DSPY AGENT STARTING')
    logger.info('=' * 80)

    # Log configuration
    llm_provider = os.getenv('LLM_PROVIDER', 'openai')
    logger.info(f'LLM Provider: {llm_provider}')
    logger.info(f"Environment: {os.getenv('RAILWAY_ENVIRONMENT', 'local')}")

    # Initialize DSPy
    try:
        import dspy
        if llm_provider == 'openai':
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set")
            lm = dspy.LM('openai/gpt-4o', api_key=api_key)
        elif llm_provider == 'anthropic':
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")
            lm = dspy.LM('anthropic/claude-3-5-sonnet-20241022', api_key=api_key)
        else:
            raise ValueError(f"Unknown LLM provider: {llm_provider}")

        dspy.configure(lm=lm)
        logger.info(f'✅ DSPy configured with {llm_provider}')
    except Exception as e:
        logger.error(f'❌ DSPy initialization failed: {e}')
        raise

    logger.info('=' * 80)
    logger.info('✅ Application startup complete')
    logger.info('=' * 80)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "hume-dspy-agent",
        "version": "2.0.0"
    }


# ============================================================================
# TYPEFORM WEBHOOK (FORM-AGNOSTIC)
# ============================================================================

@app.post("/webhooks/typeform")
async def typeform_webhook(request: Request):
    """Receive and process Typeform webhook submissions.

    This endpoint is FORM-AGNOSTIC and works with ANY Typeform structure.
    No hardcoded field mappings required.

    Flow:
    1. Receive webhook payload
    2. Transform dynamically into Lead object
    3. Qualify lead using DSPy agent
    4. Send Slack notification
    5. Return results
    """
    try:
        # Get webhook payload
        webhook_data = await request.json()

        logger.info('')
        logger.info('=' * 80)
        logger.info('📥 TYPEFORM WEBHOOK RECEIVED')
        logger.info('=' * 80)

        # Log form info
        form_id = webhook_data.get('form_id', 'unknown')
        event_type = webhook_data.get('event_type', 'unknown')
        logger.info(f'Form ID: {form_id}')
        logger.info(f'Event Type: {event_type}')

        # Transform webhook into Lead (DYNAMIC - works with any form)
        logger.info('')
        logger.info('🔄 Transforming webhook data...')
        lead = transform_typeform_webhook(webhook_data)

        logger.info(f'✅ Lead created: {lead.id}')
        logger.info(f'   Type: {lead.response_type}')
        logger.info(f"   Email: {lead.email or 'Not provided'}")
        logger.info(f"   Phone: {lead.phone or 'Not provided'}")
        logger.info(f'   Fields extracted: {len(lead.raw_answers)}')

        # Qualify lead using DSPy agent
        logger.info('')
        logger.info('🤖 Qualifying lead with DSPy agent...')
        start_time = time.time()

        agent = InboundAgent()
        result = agent.qualify_lead(lead)

        qualification_time = time.time() - start_time
        logger.info(f'✅ Qualification complete in {qualification_time:.2f}s')
        logger.info(f'   Tier: {result.tier}')
        logger.info(f'   Score: {result.overall_score}/100')
        logger.info(f'   Actions: {len(result.recommended_actions)}')

        # Send Slack notification
        logger.info('')
        logger.info('📢 Sending Slack notification...')
        try:
            slack_message = format_slack_notification(lead, result)
            slack_token = os.getenv('SLACK_USER_TOKEN') or os.getenv('SLACK_BOT_TOKEN')

            if slack_token:
                slack_response = requests.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={
                        "Authorization": f"Bearer {slack_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "channel": "#ai-test",
                        "text": slack_message,
                        "unfurl_links": False
                    }
                )
                if slack_response.status_code == 200:
                    logger.info('✅ Slack notification sent')
                else:
                    logger.warning(f'⚠️ Slack notification failed: {slack_response.status_code}')
            else:
                logger.warning('⚠️ No Slack token configured')
        except Exception as e:
            logger.error(f'❌ Slack error: {e}')

        # Return success response
        return {
            "status": "success",
            "lead_id": lead.id,
            "tier": result.tier,
            "score": result.overall_score,
            "response_type": lead.response_type,
            "fields_extracted": len(lead.raw_answers),
            "qualification_time": f"{qualification_time:.2f}s"
        }

    except Exception as e:
        logger.error('')
        logger.error(f'❌ WEBHOOK ERROR: {e}')
        logger.exception('Full traceback:')
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DIRECT QUALIFICATION ENDPOINT
# ============================================================================

@app.post("/qualify")
async def qualify_lead_endpoint(lead: Lead):
    """Qualify a lead directly via API.

    Args:
        lead: Lead object to qualify

    Returns:
        Qualification result
    """
    try:
        logger.info('')
        logger.info(f'📋 Qualifying lead: {lead.id}')

        agent = InboundAgent()
        result = agent.qualify_lead(lead)

        logger.info('✅ Qualification complete')
        logger.info(f'   Tier: {result.tier}')
        logger.info(f'   Score: {result.overall_score}/100')

        return result.model_dump()

    except Exception as e:
        logger.error(f'❌ Qualification error: {e}')
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_slack_notification(lead: Lead, result: QualificationResult) -> str:
    """Format Slack notification message.

    Args:
        lead: Lead object
        result: Qualification result

    Returns:
        Formatted Slack message
    """
    # Determine emoji based on tier
    tier_emoji = {
        "hot": "🔥",
        "warm": "⭐",
        "cold": "❄️",
        "unqualified": "⛔"
    }
    emoji = tier_emoji.get(result.tier.lower(), "📋")

    # Build message
    message = f"{emoji} *New Lead Qualified: {result.tier.upper()}*\n\n"

    # Contact info
    if lead.first_name or lead.last_name:
        name = f"{lead.first_name or ''} {lead.last_name or ''}".strip()
        message += f"*Name:* {name}\n"
    if lead.email:
        message += f"*Email:* {lead.email}\n"
    if lead.phone:
        message += f"*Phone:* {lead.phone}\n"
    if lead.company:
        message += f"*Company:* {lead.company}\n"

    # Qualification details
    message += f"\n*Score:* {result.overall_score}/100\n"
    message += f"*Response Type:* {lead.response_type}\n"
    message += f"*Fields Captured:* {len(lead.raw_answers)}\n"

    # Business fit score (safely access)
    if hasattr(result, 'criteria') and result.criteria:
        message += f"*Business Fit:* {result.criteria.business_fit_score}/100\n"
        message += f"*Engagement:* {result.criteria.engagement_score}/100\n"

    # Recommended actions
    if result.recommended_actions:
        message += "\n*Recommended Actions:*\n"
        for action in result.recommended_actions[:3]:  # Top 3 actions
            message += f"• {action}\n"

    # Email template preview
    if result.email_template:
        preview = result.email_template[:200]
        message += f"\n*Email Template Preview:*\n```{preview}...```\n"

    return message
