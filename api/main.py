from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging
import sys
import os
import httpx
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Hume DSPy Agent - SIMPLIFIED")

# Slack configuration
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = "C09FZT6T1A5"  # #ai-test channel

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "simplified-v4-slack-fixed"}

async def send_slack_notification(data: dict):
    """Send Typeform data to Slack #ai-test channel."""
    try:
        if not SLACK_BOT_TOKEN:
            logger.warning("SLACK_BOT_TOKEN not configured, skipping notification")
            return
        
        # Format the data nicely for Slack
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Extract key info
        event_type = data.get('event_type', 'unknown')
        form_response = data.get('form_response', {})
        form_id = form_response.get('form_id', 'unknown')
        
        # Extract answers
        answers = form_response.get('answers', [])
        
        # Build answer summary (first 10 fields)
        answer_text = ""
        for i, answer in enumerate(answers[:10]):
            field = answer.get('field', {})
            field_ref = field.get('ref', f"field_{i}")
            
            # Get answer value based on type
            if answer.get('type') == 'text':
                value = answer.get('text', 'N/A')
            elif answer.get('type') == 'email':
                value = answer.get('email', 'N/A')
            elif answer.get('type') == 'phone_number':
                value = answer.get('phone_number', 'N/A')
            elif answer.get('type') == 'choice':
                choice = answer.get('choice', {})
                value = choice.get('label', 'N/A')
            elif answer.get('type') == 'number':
                value = str(answer.get('number', 'N/A'))
            else:
                value = str(answer.get(answer.get('type', 'text'), 'N/A'))
            
            answer_text += f"*{field_ref}:* {value}\n"
        
        if len(answers) > 10:
            answer_text += f"\n_... and {len(answers) - 10} more fields_"
        
        # Build Slack message (simple text, no complex blocks)
        message_text = f"""📥 *New Typeform Webhook Received*

*Event Type:* {event_type}
*Form ID:* {form_id}
*Timestamp:* {timestamp}
*Total Fields:* {len(answers)}

*Answers (first 10):*
{answer_text}

_Full data logged to Railway_"""
        
        # Send to Slack (simple message, no blocks)
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
                    logger.info("✅ Slack notification sent successfully")
                else:
                    logger.error(f"❌ Slack API error: {result.get('error')}")
            else:
                logger.error(f"❌ Slack HTTP error: {response.status_code}")
                
    except Exception as e:
        logger.error(f"❌ Failed to send Slack notification: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

@app.post("/")
@app.post("/webhooks/typeform")
async def typeform_webhook(request: Request):
    """Webhook endpoint - receives Typeform data and sends to Slack."""
    try:
        # Log request details
        logger.info("="*80)
        logger.info(f"📥 WEBHOOK RECEIVED at {request.url.path}")
        logger.info(f"   Method: {request.method}")
        logger.info(f"   Client: {request.headers.get('user-agent', 'unknown')}")
        
        # Get the raw body
        body = await request.body()
        logger.info(f"   Body size: {len(body)} bytes")
        
        # Parse JSON
        try:
            data = await request.json()
            logger.info(f"✅ JSON parsed successfully")
            logger.info(f"   Keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
            
            # Log full data to Railway logs
            logger.info("")
            logger.info("FULL TYPEFORM DATA:")
            logger.info(json.dumps(data, indent=2))
            logger.info("")
            
        except Exception as e:
            logger.error(f"❌ JSON parse failed: {str(e)}")
            logger.error(f"   Raw body: {body[:500]}")
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "Invalid JSON"}
            )
        
        # Send to Slack
        logger.info("📤 Sending to Slack #ai-test...")
        await send_slack_notification(data)
        
        # Return success
        logger.info("✅ Webhook processed successfully")
        logger.info("="*80)
        return {"ok": True, "message": "Webhook received and sent to Slack"}
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(e)}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
