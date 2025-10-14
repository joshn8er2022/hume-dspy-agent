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
    return {"status": "healthy", "version": "simplified-v3-slack"}

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
        form_id = data.get('form_id', 'unknown')
        
        # Build Slack message
        message_blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📥 New Typeform Webhook Received",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Event Type:*\n{event_type}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Form ID:*\n{form_id}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Timestamp:*\n{timestamp}"
                    }
                ]
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Complete Typeform Data:*"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"```{json.dumps(data, indent=2)}```"
                }
            }
        ]
        
        # Send to Slack
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                    "Content-Type": "application/json"
                },
                json={
                    "channel": SLACK_CHANNEL,
                    "blocks": message_blocks,
                    "text": f"New Typeform webhook received: {event_type}"
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
