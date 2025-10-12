"""FastAPI application for Hume DSPy Agent."""
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

    This endpoint receives Typeform webhook submissions directly from Typeform,
    transforms them to Lead objects, and qualifies them using DSPy.

    Args:
        request: Raw request to capture payload
        background_tasks: FastAPI background tasks

    Returns:
        Event confirmation with processing status
    """
    try:
        # Get raw payload
        raw_payload = await request.json()

        # Log incoming webhook for debugging
        print('\n' + '='*80)
        print("📥 Typeform Webhook Received")
        print('='*80)
        print(json.dumps(raw_payload, indent=2)[:500])  # First 500 chars
        print('='*80 + '\n')

        # Parse webhook payload
        try:
            webhook = TypeformWebhook(**raw_payload)
        except Exception as e:
            print(f"❌ Failed to parse Typeform webhook: {str(e)}")
            print(f"Raw payload: {json.dumps(raw_payload, indent=2)}")
            raise HTTPException(
                status_code=422,
                detail=f"Invalid Typeform webhook payload: {str(e)}"
            )

        # Transform to Lead using new transformer
        try:
            lead = transform_typeform_to_lead(webhook)
            print(f"✅ Transformed to Lead: {lead.get_full_name()} ({lead.email})")
        except Exception as e:
            print(f"❌ Failed to transform webhook to lead: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to transform webhook: {str(e)}"
            )

        # Create event for audit trail
        event = Event(
            id=str(uuid.uuid4()),
            event_type=EventType.TYPEFORM_SUBMISSION,
            source=EventSource.WEBHOOK,
            payload=raw_payload,
        )

        # Process in background
        background_tasks.add_task(process_lead, lead, event.id)

        return BaseResponse(
            success=True,
            message="Typeform submission received and queued for processing",
            data={
                "event_id": event.id,
                "lead_id": lead.id,
                "lead_name": lead.get_full_name(),
                "lead_email": lead.email,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error in webhook handler: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def process_lead(lead: Lead, event_id: str):
    """Background task to process and qualify lead.

    Args:
        lead: Lead to process
        event_id: Associated event ID
    """
    try:
        print(f"🔄 Processing lead: {lead.get_full_name()}")

        # Qualify lead with DSPy agent
        agent = InboundAgent()
        result = agent.forward(lead)

        # Update lead with qualification results
        lead.score = result.score
        lead.is_qualified = result.is_qualified
        lead.qualification_reason = result.reasoning
        lead.status = _determine_lead_status(result)

        print(f"✅ Lead qualified: {result.score}/100 ({result.tier.value})")
        print(f"   Status: {lead.status}")
        print(f"   Next actions: {len(result.next_actions)} recommended")

        # TODO: Save to Supabase
        # TODO: Create Close CRM lead if qualified
        # TODO: Send email/SMS if needed
        # TODO: Post to Slack if high-value

    except Exception as e:
        print(f"❌ Error processing lead {lead.id}: {str(e)}")
        import traceback
        traceback.print_exc()


def _determine_lead_status(result: QualificationResult) -> str:
    """Determine lead status from qualification result.

    Args:
        result: Qualification result

    Returns:
        Lead status string
    """
    if result.tier.value == "hot":
        return "qualified"
    elif result.tier.value == "warm":
        return "qualified"
    elif result.tier.value == "cold":
        return "nurture"
    else:
        return "unqualified"


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )
