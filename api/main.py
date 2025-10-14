"""Event-Sourced Webhook System for Hume Lead Management.

Architecture: Event Sourcing + CQRS Pattern

Fast Path (< 50ms):
  Webhook → Store raw event → Return 200 OK

Slow Path (12-15s, background):
  Fetch raw event → Parse → Transform → Qualify → Save → Notify → Email

Key Principle: Webhook is a PURE LISTENER - never fails!
"""

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
import logging
import sys
import os
import uuid
from datetime import datetime
from typing import Dict, Any
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
    version="2.1.0"
)

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL") or "https://mvjqoojihjvohstnepfm.supabase.co"
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_KEY") or 
    os.getenv("SUPABASE_KEY") or 
    os.getenv("SUPABASE_ANON_KEY") or
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im12anFvb2ppaGp2b2hzdG5lcGZtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjAwNDkxNDksImV4cCI6MjA3NTYyNTE0OX0.5nPOgq5E4Sgscu-lWh_2zRmNK7ZfEZ3L6UQHcD7e9-c"
)

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
            'source': source,
            'raw_payload': raw_payload,
            'headers': headers,
            'received_at': datetime.utcnow().isoformat(),
            'processing_status': 'pending'
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


@app.post("/")
@app.post("/webhooks/typeform")
@app.post("/webhooks/{source}")
async def universal_webhook_receiver(
    request: Request,
    background_tasks: BackgroundTasks,
    source: str = "typeform"
):
    """Universal webhook receiver."""
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
        if supabase and event:
            retry_count = event.get('retry_count', 0) + 1 if event else 0
            supabase.table('raw_events').update({
                'processing_status': 'failed',
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
