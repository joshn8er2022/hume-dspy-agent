"""Event-Sourced Webhook System for Hume Lead Management.

Architecture: Event Sourcing + CQRS Pattern

Fast Path (< 50ms):
  Webhook → Store raw event → Return 200 OK

Slow Path (12-15s, background):
  Fetch raw event → Parse → Transform → Qualify → Save → Notify

Key Principle: Webhook is a PURE LISTENER - never fails!
"""

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
import logging
import sys
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Hume DSPy Agent - Event Sourced",
    description="Event sourcing webhook system with async processing",
    version="2.0.1"
)

# Supabase configuration
# Try multiple environment variable names for flexibility
SUPABASE_URL = os.getenv("SUPABASE_URL") or "https://mvjqoojihjvohstnepfm.supabase.co"
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_KEY") or 
    os.getenv("SUPABASE_KEY") or 
    os.getenv("SUPABASE_ANON_KEY") or
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im12anFvb2ppaGp2b2hzdG5lcGZtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjAwNDkxNDksImV4cCI6MjA3NTYyNTE0OX0.5nPOgq5E4Sgscu-lWh_2zRmNK7ZfEZ3L6UQHcD7e9-c"
)
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = "C09FZT6T1A5"  # #ai-test

# Initialize Supabase client
supabase = None
try:
    from supabase import create_client, Client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info(f"✅ Supabase client initialized")
    logger.info(f"   URL: {SUPABASE_URL}")
    logger.info(f"   Key: {SUPABASE_KEY[:20]}...")
except Exception as e:
    logger.error(f"❌ Failed to initialize Supabase: {str(e)}")
    logger.error(f"   SUPABASE_URL: {SUPABASE_URL}")
    logger.error(f"   SUPABASE_KEY: {'set' if SUPABASE_KEY else 'not set'}")
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
    """Store raw webhook event to Supabase (immutable event log).
    
    This is FAST - just insert and return.
    No parsing, no transformation, no processing.
    
    Returns:
        event_id: UUID of stored event
    """
    event_id = str(uuid.uuid4())
    
    try:
        if not supabase:
            logger.warning("⚠️ Supabase not available, storing to file instead")
            # Fallback: Store to file if Supabase unavailable
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
            'source': source,
            'raw_payload': raw_payload,
            'headers': headers,
            'received_at': datetime.utcnow().isoformat(),
            'processing_status': 'pending'
        }).execute()
        
        logger.info(f"✅ Raw event stored to Supabase: {event_id} (source: {source})")
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
        "version": "2.0.1-event-sourced",
        "supabase": "connected" if supabase else "disconnected (using file fallback)",
        "supabase_url": SUPABASE_URL if supabase else None
    }


@app.post("/")
@app.post("/webhooks/typeform")
@app.post("/webhooks/{source}")
async def universal_webhook_receiver(
    request: Request,
    background_tasks: BackgroundTasks,
    source: str = "typeform"
):
    """Universal webhook receiver - works for ALL webhook sources.
    
    This is a PURE LISTENER:
    1. Receive webhook
    2. Store raw data (< 50ms)
    3. Return 200 OK immediately
    4. Process asynchronously in background
    """
    start_time = datetime.utcnow()
    
    try:
        logger.info("="*80)
        logger.info(f"📥 WEBHOOK RECEIVED: {source}")
        logger.info(f"   Path: {request.url.path}")
        logger.info(f"   Method: {request.method}")
        logger.info(f"   Client: {request.headers.get('user-agent', 'unknown')}")
        
        # Get raw body and headers
        raw_body = await request.body()
        headers = dict(request.headers)
        
        logger.info(f"   Body size: {len(raw_body)} bytes")
        
        # Parse JSON (minimal validation)
        try:
            payload = await request.json()
        except Exception as e:
            logger.error(f"❌ Invalid JSON from {source}: {str(e)}")
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "Invalid JSON"}
            )
        
        # Store raw event (FAST - just insert or file write)
        event_id = await store_raw_event(source, payload, headers)
        
        # Queue for async processing (happens AFTER response sent)
        background_tasks.add_task(process_event_async, event_id, source)
        
        # Calculate response time
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Return 200 OK IMMEDIATELY
        logger.info(f"✅ Webhook acknowledged in {response_time:.0f}ms")
        logger.info(f"   Event ID: {event_id}")
        logger.info(f"   Status: Queued for async processing")
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
# SLOW PATH: Async Event Processing (12-15s, background)
# ============================================================================

async def process_event_async(event_id: str, source: str):
    """Process event asynchronously."""
    try:
    event = None  # Initialize before try block
        logger.info("")
        logger.info("="*80)
        logger.info(f"🔄 ASYNC PROCESSING STARTED: {event_id}")
        logger.info(f"   Source: {source}")
        
        # Fetch raw event
        if supabase:
            # Update status
            supabase.table('raw_events').update({
                'processing_status': 'processing'
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
                'processing_status': 'completed',
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
        if supabase:
            retry_count = event.get('retry_count', 0) + 1
            supabase.table('raw_events').update({
                'processing_status': 'failed',
                'processing_error': str(e),
                'retry_count': retry_count
            }).eq('id', event_id).execute()
            
            # Retry logic
            if retry_count < 3:
                logger.info(f"🔄 Retrying: {event_id} (attempt {retry_count + 1}/3)")
                await process_event_async(event_id, source)


# ============================================================================
# EVENT PROCESSORS
# ============================================================================

async def process_typeform_event(event: dict):
    """Process Typeform webhook event."""
    try:
        logger.info("🔄 Processing Typeform event...")
        
        # Send to Slack
        await send_slack_notification_simple(event['raw_payload'])
        
        logger.info("✅ Typeform event processed")
        
    except Exception as e:
        logger.error(f"❌ Typeform processing failed: {str(e)}")
        raise


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


# ============================================================================
# SLACK NOTIFICATION
# ============================================================================

async def send_slack_notification_simple(data: dict):
    """Send Typeform data to Slack."""
    try:
        if not SLACK_BOT_TOKEN:
            logger.warning("SLACK_BOT_TOKEN not configured")
            return
        
        import httpx
        
        event_type = data.get('event_type', 'unknown')
        form_response = data.get('form_response', {})
        form_id = form_response.get('form_id', 'unknown')
        answers = form_response.get('answers', [])
        
        # Build summary
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
        
        message_text = f"""📥 *New Typeform Webhook* (Event Sourced)

*Event Type:* {event_type}
*Form ID:* {form_id}
*Timestamp:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
*Total Fields:* {len(answers)}
*Storage:* {'Supabase' if supabase else 'File fallback'}

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
                    "text": message_text,
                    "mrkdwn": True
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    logger.info("✅ Slack notification sent")
                else:
                    logger.error(f"❌ Slack API error: {result.get('error')}")
                    
    except Exception as e:
        logger.error(f"❌ Slack notification failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
