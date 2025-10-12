"""FastAPI application for Hume DSPy Agent."""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import uvicorn
import uuid
from datetime import datetime

from models import (
    Lead,
    TypeformSubmission,
    Event,
    EventType,
    EventSource,
    QualificationResult,
    BaseResponse,
)
from agents import InboundAgent
from core import settings, dspy_manager

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
    submission: TypeformSubmission,
    background_tasks: BackgroundTasks,
):
    """Receive Typeform webhook and process lead.

    This endpoint receives Typeform submissions from N8N,
    converts them to Lead objects, and qualifies them.

    Args:
        submission: Typeform submission data
        background_tasks: FastAPI background tasks

    Returns:
        Event confirmation with processing status
    """
    try:
        # Create event for audit trail
        event = Event(
            id=str(uuid.uuid4()),
            event_type=EventType.TYPEFORM_SUBMISSION,
            source=EventSource.WEBHOOK,
            payload=submission.model_dump(),
        )

        # Convert Typeform submission to Lead
        lead = _typeform_to_lead(submission)

        # Process in background
        background_tasks.add_task(process_lead, lead, event.id)

        return BaseResponse(
            success=True,
            message="Typeform submission received and queued for processing",
            data={
                "event_id": event.id,
                "lead_id": lead.id,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def process_lead(lead: Lead, event_id: str):
    """Background task to process and qualify lead.

    Args:
        lead: Lead to process
        event_id: Associated event ID
    """
    try:
        # Qualify lead with DSPy agent
        agent = InboundAgent()
        result = agent.forward(lead)

        # Update lead with qualification results
        lead.score = result.score
        lead.is_qualified = result.is_qualified
        lead.qualification_reason = result.reasoning
        lead.status = _determine_lead_status(result)

        # TODO: Save to Supabase
        # TODO: Create Close CRM lead if qualified
        # TODO: Send email/SMS if needed
        # TODO: Post to Slack if high-value

        print(f"✅ Lead {lead.id} qualified: {result.score}/100 ({result.tier.value})")

    except Exception as e:
        print(f"❌ Error processing lead {lead.id}: {str(e)}")


def _typeform_to_lead(submission: TypeformSubmission) -> Lead:
    """Convert Typeform submission to Lead object.

    Args:
        submission: Typeform submission

    Returns:
        Lead object
    """
    # Parse dates
    typeform_start = None
    typeform_submit = None

    if submission.start_date:
        try:
            typeform_start = datetime.fromisoformat(submission.start_date.replace(" ", "T"))
        except:
            pass

    if submission.submit_date:
        try:
            typeform_submit = datetime.fromisoformat(submission.submit_date.replace(" ", "T"))
        except:
            pass

    # Create lead
    lead = Lead(
        id=str(uuid.uuid4()),
        typeform_id=submission.submission_id,
        first_name=submission.first_name.strip(),
        last_name=submission.last_name.strip(),
        email=submission.email,
        phone=submission.phone_number,
        company=submission.company,
        business_size=submission.business_size,
        patient_volume=submission.patient_volume,
        response_type=submission.response_type,
        partnership_interest=submission.partnership_interest,
        body_comp_tracking=submission.body_comp_tracking,
        ai_summary=submission.summary,
        calendly_link=submission.calendly_link,
        calendly_booked=bool(submission.calendly_link),
        typeform_start_date=typeform_start,
        typeform_submit_date=typeform_submit,
        network_id=submission.network_id,
        tags=submission.tags.split(",") if submission.tags else [],
    )

    return lead


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
