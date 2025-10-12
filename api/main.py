"""FastAPI application for Hume DSPy Agent."""
import os
import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import uvicorn
import uuid
from datetime import datetime
import json

from models import (
    Lead,
    TypeformSubmission,
    TypeformWebhook,
    Event,
    EventType,
    EventSource,
    QualificationResult,
    BaseResponse,
)
from agents import InboundAgent
from core import settings, dspy_manager
from utils.typeform_transformer import transform_typeform_to_lead


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Initialize logger

# Initialize FastAPI
app = FastAPI(
    title="Hume DSPy Inbound Agent",
    description="Intelligent lead qualification using DSPy",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DSPy on startup
@app.on_event("startup")
async def startup_event():
    """Initialize DSPy on application startup."""
    dspy_manager.initialize()
    print(f"🚀 Hume DSPy Agent started on {settings.api_host}:{settings.api_port}")
    print(f"📊 Environment: {settings.environment}")
    print(f"🤖 LLM: {settings.llm_provider}/{settings.dspy_model}")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Hume DSPy Inbound Agent",
        "version": "1.0.0",
        "status": "operational",
        "llm_provider": settings.llm_provider,
        "model": settings.dspy_model,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/qualify", response_model=QualificationResult)
async def qualify_lead(lead: Lead):
    """Qualify a lead using DSPy agent.

    Args:
        lead: Lead object to qualify

    Returns:
        QualificationResult with score, reasoning, and next actions
    """
    try:
        agent = InboundAgent()
        result = agent.forward(lead)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhooks/typeform")
async def typeform_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Receive Typeform webhook and process lead.

    This endpoint:
    1. Verifies webhook signature for security
    2. Parses Typeform's nested payload structure
    3. Transforms to Lead model
    4. Qualifies lead using DSPy agent
    5. Executes recommended actions
    6. Sends notifications

    Args:
        request: Raw request to capture payload and headers
        background_tasks: FastAPI background tasks

    Returns:
        Event confirmation with processing status
    """
    import time
    from models.typeform import TypeformWebhookPayload
    from utils.typeform_transform import transform_typeform_to_lead
    from utils.security import verify_typeform_signature

    start_time = time.time()

    try:
        # Get raw body for signature verification
        body = await request.body()

        # Verify signature if secret is configured
        signature = request.headers.get("X-Typeform-Signature", "")
        typeform_secret = os.getenv("TYPEFORM_WEBHOOK_SECRET", "")

        if typeform_secret and not verify_typeform_signature(body, signature, typeform_secret):
            logger.warning(f"Invalid Typeform signature from {request.client.host}")
            raise HTTPException(
                status_code=401,
                detail="Invalid webhook signature"
            )

        # Parse JSON payload
        try:
            payload_dict = await request.json()
            payload = TypeformWebhookPayload(**payload_dict)
        except Exception as e:
            logger.error(f"Failed to parse Typeform payload: {e}")
            logger.error(f"Payload: {body.decode('utf-8')[:500]}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid Typeform payload: {str(e)}"
            )

        logger.info('\n' + '='*80)
        logger.info(f"📥 TYPEFORM WEBHOOK RECEIVED")
        logger.info(f"Event ID: {payload.event_id}")
        logger.info(f"Event Type: {payload.event_type}")
        logger.info(f"Form ID: {payload.form_response.form_id}")
        logger.info(f"Submission Token: {payload.form_response.token}")
        logger.info(f"Submitted At: {payload.form_response.submitted_at}")
        logger.info(f"Answers Count: {len(payload.form_response.answers)}")
        logger.info('='*80)

        # DEBUG: Show actual field IDs from Typeform
        logger.info('\n' + '='*80)
        logger.info('🔍 TYPEFORM FIELD MAPPING DEBUG')
        for answer in payload.form_response.answers:
            field_id = answer.field.id
            field_ref = answer.field.ref if hasattr(answer.field, 'ref') else 'N/A'
            field_type = answer.field.type
            answer_type = answer.type
            logger.info(f'  Field ID: {field_id} | Ref: {field_ref} | Type: {field_type}/{answer_type}')
        logger.info('='*80 + '\n')


        # Transform Typeform payload to Lead model
        try:
            lead = transform_typeform_to_lead(payload)
            logger.info(f"✅ Transformed to Lead: {lead.email}")
        except ValueError as e:
            logger.error(f"Failed to transform Typeform payload: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Missing required fields: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error transforming payload: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to process lead data"
            )

        # Qualify lead using DSPy agent
        logger.info(f"🤖 Qualifying lead with DSPy agent...")

        try:
            agent = InboundAgent()
            result = agent.forward(lead)

            processing_time = time.time() - start_time

            logger.info('\n' + '='*80)
            logger.info(f"✅ LEAD QUALIFIED - {result.tier}")
            logger.info(f"Score: {result.score}/100")
            logger.info(f"Business Fit: {result.business_fit_score}/50")
            logger.info(f"Engagement: {result.engagement_score}/50")
            logger.info(f"Processing Time: {processing_time:.2f}s")
            logger.info('='*80)

            # Send Slack notification
            try:
                slack_message = f"""🎯 *New Lead Qualified: {result.tier}*

*Contact:* {lead.first_name} {lead.last_name}
*Email:* {lead.email}
*Business:* {lead.business_name or 'N/A'}

*Score:* {result.score}/100
• Business Fit: {result.business_fit_score}/50
• Engagement: {result.engagement_score}/50

*Tier:* {result.tier}
*Next Actions:*
{chr(10).join('• ' + action for action in result.recommended_actions)}

*Reasoning:*
{result.reasoning}

_Processed in {processing_time:.2f}s_"""

                slack_response = requests.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={
                        "Authorization": f"Bearer {os.getenv('SLACK_USER_TOKEN')}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "channel": "ai-test",
                        "text": slack_message
                    }
                )

                if slack_response.json().get("ok"):
                    logger.info("✅ Slack notification sent")
                else:
                    logger.warning(f"Slack notification failed: {slack_response.json()}")

            except Exception as e:
                logger.error(f"Failed to send Slack notification: {e}")

            # Return success response
            return {
                "status": "success",
                "event_id": payload.event_id,
                "submission_token": payload.form_response.token,
                "lead_email": lead.email,
                "qualification": {
                    "tier": result.tier,
                    "score": result.score,
                    "business_fit": result.business_fit_score,
                    "engagement": result.engagement_score
                },
                "processing_time": round(processing_time, 2),
                "actions_recommended": len(result.recommended_actions)
            }

        except Exception as e:
            logger.error(f"Failed to qualify lead: {e}")
            logger.exception(e)
            raise HTTPException(
                status_code=500,
                detail=f"Lead qualification failed: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in webhook handler: {e}")
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )
