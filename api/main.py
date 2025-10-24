"""Event-Sourced Webhook System for Hume Lead Management.

Architecture: Event Sourcing + CQRS Pattern

Fast Path (< 50ms):
  Webhook → Store raw event → Return 200 OK

Slow Path (12-15s, background):
  Fetch raw event → Parse → Transform → Qualify → Save → Notify → Email

Key Principle: Webhook is a PURE LISTENER - never fails!
"""
from dotenv import load_dotenv
load_dotenv()  # Load .env file BEFORE any other imports


from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
import logging
import sys
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import json

# Configure logging FIRST
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ============================================================================
# PHOENIX OBSERVABILITY (MUST BE FIRST!)
# ============================================================================
# Initialize Phoenix tracing BEFORE any DSPy/agent code runs
# This gives us complete visibility into all LLM calls and agent behavior

from core.observability import setup_observability

logger.info("🔭 Initializing Phoenix observability...")
tracer_provider = setup_observability()
if tracer_provider:
    logger.info("✅ Phoenix tracing active - all DSPy calls will be traced")
    logger.info("   View traces at: https://app.phoenix.arize.com/")
else:
    logger.info("⚠️ Phoenix tracing disabled - set PHOENIX_API_KEY to enable")

# ============================================================================
# DSPY GLOBAL CONFIGURATION (CRITICAL!)
# ============================================================================
# This must happen AFTER Phoenix but BEFORE any agents are imported!

import dspy

try:
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        # Two-tier paid model system:
        # - Haiku 4.5: Fast, cheap for routine low-level agentic work (DEFAULT)
        # - Sonnet 4.5: Premium for complex high-level reasoning
        # Configure with Haiku 4.5 as default (most tasks are standard customer-facing)
        lm = dspy.LM(
            model="openrouter/anthropic/claude-haiku-4.5",
            api_key=openrouter_key,
            max_tokens=2000,
            temperature=0.7
        )
        dspy.configure(lm=lm)
        logger.info("✅ DSPy configured globally with Claude Haiku 4.5 via OpenRouter")
        logger.info("   Low-tier: claude-haiku-4.5 (default for standard tasks)")
        logger.info("   High-tier: claude-sonnet-4.5 (for complex reasoning)")
        logger.info("   Use core.model_selector for dynamic model selection")
    else:
        logger.error("❌ OPENROUTER_API_KEY not found - DSPy will not work!")
        logger.error("   Set OPENROUTER_API_KEY in Railway environment variables")
except Exception as e:
    logger.error(f"❌ Failed to configure DSPy: {e}")
    import traceback
    logger.error(traceback.format_exc())

app = FastAPI(
    title="Hume DSPy Agent - Event Sourced",
    description="Event sourcing webhook system with async processing",
    version="2.1.0"
)

# ============================================================================
# PHASE 0.6.1: AUTO-START PROACTIVE MONITORING
# ============================================================================

@app.on_event("startup")
async def start_background_tasks():
    """Start proactive monitoring on server startup (Phase 0.6.1).
    
    This enables the agent to:
    - Continuously monitor production logs
    - Detect anomalies and patterns
    - Generate fix proposals
    - Post to Slack for approval
    """
    import asyncio
    
    try:
        from monitoring.proactive_monitor import start_monitoring
        
        # Start monitoring in background (checks every 5 minutes)
        asyncio.create_task(start_monitoring(interval_seconds=300))
        logger.info("🔄 Proactive monitoring started (5-minute intervals)")
        logger.info("   Phase 0.6: Self-healing enabled with human approval")
    except Exception as e:
        logger.warning(f"⚠️ Proactive monitoring failed to start: {e}")
        logger.info("   System will continue without proactive monitoring")

# Include Slack bot router
from api.slack_bot import router as slack_router
app.include_router(slack_router)

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL") or "https://mvjqoojihjvohstnepfm.supabase.co"
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_KEY") or 
    os.getenv("SUPABASE_KEY") or 
    os.getenv("SUPABASE_ANON_KEY")
)

# Validate required configuration
if not SUPABASE_KEY:
    logger.error("❌ CRITICAL: SUPABASE_KEY not found in environment")
    logger.error("   Set one of: SUPABASE_SERVICE_KEY, SUPABASE_KEY, or SUPABASE_ANON_KEY")
    logger.error("   Application cannot start without Supabase credentials")
    raise ValueError("Supabase credentials required but not found in environment variables")



# Initialize Supabase client
supabase = None
try:
    from supabase import create_client, Client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info(f"✅ Supabase client initialized")
    logger.info(f"   URL: {SUPABASE_URL}")
except Exception as e:
    logger.error(f"❌ Failed to initialize Supabase: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())

# Initialize global FollowUpAgent (singleton to prevent duplicate email sequences)
follow_up_agent = None
try:
    from agents.follow_up_agent import FollowUpAgent
    follow_up_agent = FollowUpAgent()
    logger.info("✅ Global Follow-Up Agent initialized (singleton)")
except Exception as e:
    logger.error(f"❌ Failed to initialize Follow-Up Agent: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())

# Import processors and inject Supabase client
try:
    from api.processors import (
        process_typeform_event,
        process_slack_event,
        process_vapi_event,
        process_a2a_event,
        set_supabase_client
    )
    set_supabase_client(supabase)
    logger.info("✅ Processors imported and configured")
except Exception as e:
    logger.error(f"❌ Failed to import processors: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())


# ============================================================================
# FAST PATH: Webhook Reception (< 50ms)
# ============================================================================

async def store_raw_event(
    source: str,
    raw_payload: Dict[Any, Any],
    headers: Dict[str, str]
) -> str:
    """Store raw webhook event to Supabase."""
    event_id = str(uuid.uuid4())
    
    try:
        if not supabase:
            # Fallback: Store to file
            os.makedirs('/tmp/raw_events', exist_ok=True)
            with open(f'/tmp/raw_events/{event_id}.json', 'w') as f:
                json.dump({
                    'id': event_id,
                    'source': source,
                    'raw_payload': raw_payload,
                    'headers': headers,
                    'received_at': datetime.utcnow().isoformat()
                }, f, indent=2)
            logger.info(f"✅ Raw event stored to file: {event_id}")
            return event_id
        
        supabase.table('raw_events').insert({
            'id': event_id,
            'event_type': raw_payload.get('event_type', 'webhook'),
            'source': source,
            'raw_payload': raw_payload,
            'headers': headers,
            'received_at': datetime.utcnow().isoformat(),
            'status': 'pending'
        }).execute()
        
        logger.info(f"✅ Raw event stored to Supabase: {event_id}")
        return event_id
        
    except Exception as e:
        logger.error(f"❌ Failed to store raw event: {str(e)}")
        # Fallback: Store to file
        os.makedirs('/tmp/raw_events', exist_ok=True)
        with open(f'/tmp/raw_events/{event_id}.json', 'w') as f:
            json.dump({
                'id': event_id,
                'source': source,
                'raw_payload': raw_payload,
                'headers': headers,
                'received_at': datetime.utcnow().isoformat(),
                'error': str(e)
            }, f, indent=2)
        logger.info(f"✅ Raw event stored to file (fallback): {event_id}")
        return event_id


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "2.1.0-full-pipeline",
        "supabase": "connected" if supabase else "disconnected"
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Hume DSPy Agent API",
        "version": "2.1.0-full-pipeline",
        "status": "operational",
        "endpoints": {
            "health": "GET /health",
            "typeform_webhook": "POST /webhooks/typeform",
            "vapi_webhook": "POST /webhooks/vapi",
            "a2a_introspection": "POST /a2a/introspect",
            "slack_events": "POST /slack/events"
        },
        "documentation": "See /docs for API documentation"
    }


@app.post("/")
async def root_post_handler(request: Request):
    """
    Catch-all for incorrect webhook URLs.
    
    Common mistake: Typeform webhook configured as just the domain
    without the /webhooks/typeform path.
    """
    logger.warning("❌ POST to root path (/) - likely misconfigured webhook URL")
    logger.warning("   Typeform webhooks should POST to: /webhooks/typeform")
    logger.warning("   VAPI webhooks should POST to: /webhooks/vapi")
    
    return JSONResponse(
        status_code=400,
        content={
            "error": "Wrong endpoint",
            "message": "You're posting to the root path. Did you mean /webhooks/typeform?",
            "correct_urls": {
                "typeform": f"{request.base_url}webhooks/typeform",
                "vapi": f"{request.base_url}webhooks/vapi"
            },
            "hint": "Update your webhook URL in Typeform/VAPI to include the full path"
        }
    )


# ============================================================================
# A2A INTROSPECTION API
# ============================================================================

async def verify_a2a_token(authorization: Optional[str] = Header(None)) -> bool:
    """Verify A2A authentication token."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header format. Use: Bearer <token>")

    token = authorization.replace("Bearer ", "")
    expected_token = os.getenv("A2A_API_KEY")

    if not expected_token:
        logger.warning("⚠️ A2A_API_KEY not set - allowing all requests (INSECURE!)")
        return True

    if token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid A2A API key")

    return True


@app.post("/a2a/introspect")
async def a2a_introspection(
    request: Request,
    authorized: bool = Depends(verify_a2a_token)
):
    """A2A introspection endpoint for agent-to-agent communication.

    Authentication: Requires Bearer token in Authorization header.
    Set A2A_API_KEY environment variable to enable authentication.

    This endpoint allows external agents (like Claude Code) to query the
    autonomous agents about their internal state, reasoning, and decisions.

    Example queries:
    - Show follow-up state: {"agent_type": "follow_up", "query_type": "show_state", "lead_id": "abc-123"}
    - Explain qualification: {"agent_type": "qualification", "query_type": "explain_score", "lead_id": "abc-123"}
    - Test qualification: {"agent_type": "qualification", "query_type": "test_qualification", "test_data": {...}}
    """
    try:
        from agents.introspection import get_introspection_service, IntrospectionRequest

        # Parse request
        payload = await request.json()
        introspection_request = IntrospectionRequest(**payload)

        # Get introspection service
        service = get_introspection_service()

        # Handle query
        response = service.handle_query(introspection_request)

        return response.model_dump()

    except Exception as e:
        logger.error(f"❌ A2A introspection failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )



# ============================================================================
# ============================================================================

@app.get("/.well-known/agent.json")
async def agent_card():
    """FastA2A agent card endpoint - provides agent metadata."""
    return {
        "name": "Hume DSPy Agent",
        "description": "ABM-powered lead engagement system with multi-agent orchestration",
        "version": "2.1.0-full-pipeline",
        "capabilities": [
            "conversation",
            "research", 
            "qualification",
            "account_orchestration",
            "follow_up_automation"
        ],
        "endpoints": {
            "a2a": "/a2a",
            "introspection": "/a2a/introspect"
        },
        "agents": [
            "StrategyAgent",
            "AccountOrchestrator",
            "ResearchAgent",
            "FollowUpAgent",
            "InboundAgent"
        ]
    }

@app.post("/a2a")
async def a2a_conversation(request: Request):
    """FastA2A conversational endpoint - handles agent-to-agent chat."""
    try:
        payload = await request.json()
        message_content = payload.get("message", "")

        if not message_content:
            return JSONResponse(
                status_code=400,
                content={"error": "No message provided"}
            )

        logger.info(f"📨 A2A Message received: {message_content[:100]}...")

        # Import StrategyAgent for conversational processing
        from agents.strategy_agent import StrategyAgent

        # Initialize StrategyAgent (singleton pattern)
        if not hasattr(app.state, 'strategy_agent'):
            app.state.strategy_agent = StrategyAgent()

        strategy_agent = app.state.strategy_agent

        # Process message through StrategyAgent
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            strategy_agent.forward,
            message_content
        )

        logger.info(f"✅ A2A Response generated: {str(response)[:100]}...")

        return JSONResponse(content={
            "status": "success",
            "response": str(response),
            "agent": "StrategyAgent"
        })

    except Exception as e:
        logger.error(f"❌ A2A conversation failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": str(e)}
        )



# ============================================================================
# ============================================================================


# ============================================================================
# Inter-Agent Communication Endpoints (A2A Protocol)
# ============================================================================

@app.post("/agents/inbound/a2a")
async def inbound_agent_a2a(request: Request):
    """A2A endpoint for InboundAgent - lead qualification."""
    try:
        payload = await request.json()
        message_content = payload.get("message", "")
        
        if not message_content:
            return JSONResponse(
                status_code=400,
                content={"error": "No message provided"}
            )
            
        logger.info(f"📨 InboundAgent A2A Message: {message_content[:100]}...")
        
        # Import and initialize InboundAgent
        from agents.inbound_agent import InboundAgent
        
        if not hasattr(app.state, 'inbound_agent'):
            app.state.inbound_agent = InboundAgent()
            
        inbound_agent = app.state.inbound_agent
        
        # Process message
        response = await inbound_agent.respond(message_content)
        
        logger.info(f"✅ InboundAgent A2A Response: {str(response)[:100]}...")
        
        return JSONResponse(content={
            "status": "success",
            "response": str(response),
            "agent": "InboundAgent"
        })
        
    except Exception as e:
        logger.error(f"❌ InboundAgent A2A failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": str(e)}
        )


@app.post("/agents/research/a2a")
async def research_agent_a2a(request: Request):
    """A2A endpoint for ResearchAgent - deep lead research."""
    try:
        payload = await request.json()
        message_content = payload.get("message", "")
        
        if not message_content:
            return JSONResponse(
                status_code=400,
                content={"error": "No message provided"}
            )
            
        logger.info(f"📨 ResearchAgent A2A Message: {message_content[:100]}...")
        
        # Import and initialize ResearchAgent
        from agents.research_agent import ResearchAgent
        
        if not hasattr(app.state, 'research_agent'):
            app.state.research_agent = ResearchAgent()
            
        research_agent = app.state.research_agent
        
        # Process message
        response = await research_agent.respond(message_content)
        
        logger.info(f"✅ ResearchAgent A2A Response: {str(response)[:100]}...")
        
        return JSONResponse(content={
            "status": "success",
            "response": str(response),
            "agent": "ResearchAgent"
        })
        
    except Exception as e:
        logger.error(f"❌ ResearchAgent A2A failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": str(e)}
        )


@app.post("/agents/followup/a2a")
async def followup_agent_a2a(request: Request):
    """A2A endpoint for FollowUpAgent - lead journey management."""
    try:
        payload = await request.json()
        message_content = payload.get("message", "")
        
        if not message_content:
            return JSONResponse(
                status_code=400,
                content={"error": "No message provided"}
            )
            
        logger.info(f"📨 FollowUpAgent A2A Message: {message_content[:100]}...")
        
        # Import and initialize FollowUpAgent
        from agents.follow_up_agent import FollowUpAgent
        
        if not hasattr(app.state, 'followup_agent'):
            app.state.followup_agent = FollowUpAgent()
            
        followup_agent = app.state.followup_agent
        
        # Process message
        response = await followup_agent.respond(message_content)
        
        logger.info(f"✅ FollowUpAgent A2A Response: {str(response)[:100]}...")
        
        return JSONResponse(content={
            "status": "success",
            "response": str(response),
            "agent": "FollowUpAgent"
        })
        
    except Exception as e:
        logger.error(f"❌ FollowUpAgent A2A failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": str(e)}
        )

# FastA2A Protocol Endpoints
# ============================================================================

@app.post("/webhooks/typeform")
async def typeform_webhook_receiver(
    request: Request,
    background_tasks: BackgroundTasks
):
    """Typeform webhook receiver - SINGLE ROUTE to prevent duplicates."""
    source = "typeform"
    start_time = datetime.utcnow()
    
    try:
        logger.info("="*80)
        logger.info(f"📥 WEBHOOK RECEIVED: {source}")
        logger.info(f"   Path: {request.url.path}")
        
        # Get raw body
        raw_body = await request.body()
        headers = dict(request.headers)
        logger.info(f"   Body size: {len(raw_body)} bytes")
        
        # Parse JSON
        try:
            payload = await request.json()
        except Exception as e:
            logger.error(f"❌ Invalid JSON: {str(e)}")
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "Invalid JSON"}
            )
        
        # ============================================================================
        # DEDUPLICATION: Check if this Typeform event was already processed
        # ============================================================================
        typeform_event_id = payload.get('event_id')
        
        if typeform_event_id and supabase:
            try:
                # Check if this event_id already exists in raw_events
                existing = supabase.table('raw_events').select('id, received_at, status').eq('source', source).filter('raw_payload->>event_id', 'eq', typeform_event_id).execute()
                
                if existing.data:
                    # This is a duplicate webhook delivery from Typeform
                    first_event = existing.data[0]
                    logger.warning(f"⚠️  DUPLICATE WEBHOOK DETECTED")
                    logger.warning(f"   Typeform event_id: {typeform_event_id}")
                    logger.warning(f"   First received: {first_event['received_at']}")
                    logger.warning(f"   Status: {first_event['status']}")
                    logger.warning(f"   Returning 200 OK (idempotent)")
                    
                    return {
                        "ok": True,
                        "duplicate": True,
                        "event_id": first_event['id'],
                        "message": "Duplicate webhook ignored (already processed)",
                        "first_received_at": first_event['received_at']
                    }
            except Exception as e:
                # If deduplication check fails, log but continue processing
                # Better to process twice than lose an event
                logger.error(f"⚠️  Deduplication check failed: {str(e)}")
                logger.error(f"   Continuing with processing...")
        
        # Store raw event
        event_id = await store_raw_event(source, payload, headers)
        
        # Queue for async processing
        background_tasks.add_task(process_event_async, event_id, source)
        
        # Calculate response time
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        logger.info(f"✅ Webhook acknowledged in {response_time:.0f}ms")
        logger.info(f"   Event ID: {event_id}")
        logger.info("="*80)
        
        return {
            "ok": True,
            "event_id": event_id,
            "message": "Webhook received, processing in background",
            "response_time_ms": response_time
        }
        
    except Exception as e:
        logger.error(f"❌ Webhook reception failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(e)}
        )


@app.post("/webhooks/vapi")
async def vapi_webhook_receiver(
    request: Request,
    background_tasks: BackgroundTasks
):
    """VAPI webhook receiver - SINGLE ROUTE to prevent duplicates."""
    source = "vapi"
    start_time = datetime.utcnow()
    
    try:
        logger.info("="*80)
        logger.info(f"📥 WEBHOOK RECEIVED: {source}")
        logger.info(f"   Path: {request.url.path}")
        
        # Get raw body
        raw_body = await request.body()
        headers = dict(request.headers)
        logger.info(f"   Body size: {len(raw_body)} bytes")
        
        # Parse JSON
        try:
            payload = await request.json()
        except Exception as e:
            logger.error(f"❌ Invalid JSON: {str(e)}")
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "Invalid JSON"}
            )
        
        # Store raw event
        event_id = await store_raw_event(source, payload, headers)
        
        # Queue for async processing
        background_tasks.add_task(process_event_async, event_id, source)
        
        # Calculate response time
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        logger.info(f"✅ Webhook acknowledged in {response_time:.0f}ms")
        logger.info(f"   Event ID: {event_id}")
        logger.info("="*80)
        
        return {
            "ok": True,
            "event_id": event_id,
            "message": "Webhook received, processing in background",
            "response_time_ms": response_time
        }
        
    except Exception as e:
        logger.error(f"❌ Webhook reception failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(e)}
        )


# ============================================================================
# SLOW PATH: Async Event Processing
# ============================================================================

async def process_event_async(event_id: str, source: str):
    """Process event asynchronously."""
    event = None
    try:
        logger.info("")
        logger.info("="*80)
        logger.info(f"🔄 ASYNC PROCESSING STARTED: {event_id}")
        logger.info(f"   Source: {source}")
        
        # Fetch raw event
        if supabase:
            # Update status
            supabase.table('raw_events').update({
                'status': 'processing'
            }).eq('id', event_id).execute()
            
            # Fetch event
            result = supabase.table('raw_events').select('*').eq('id', event_id).execute()
            if not result.data:
                raise Exception(f"Event not found: {event_id}")
            event = result.data[0]
        else:
            # Fallback: Read from file
            with open(f'/tmp/raw_events/{event_id}.json', 'r') as f:
                event = json.load(f)
        
        # Route to appropriate processor
        if source == 'typeform':
            await process_typeform_event(event)
        elif source == 'slack':
            await process_slack_event(event)
        elif source == 'vapi':
            await process_vapi_event(event)
        elif source == 'a2a':
            await process_a2a_event(event)
        else:
            logger.warning(f"⚠️ Unknown source: {source}")
        
        # Update status to 'completed'
        if supabase:
            supabase.table('raw_events').update({
                'status': 'completed',
                'processed_at': datetime.utcnow().isoformat()
            }).eq('id', event_id).execute()
        
        logger.info(f"✅ ASYNC PROCESSING COMPLETED: {event_id}")
        logger.info("="*80)
        
    except Exception as e:
        logger.error(f"❌ Event processing failed: {event_id}")
        logger.error(f"   Error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Update status to 'failed'
        if supabase and event:
            retry_count = event.get('retry_count', 0) + 1 if event else 0
            supabase.table('raw_events').update({
                'status': 'failed',
                'processing_error': str(e),
                'retry_count': retry_count
            }).eq('id', event_id).execute()
            
            # Retry logic
            if retry_count < 3:
                logger.info(f"🔄 Retrying: {event_id} (attempt {retry_count + 1}/3)")
                await process_event_async(event_id, source)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
