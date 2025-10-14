from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Hume DSPy Agent - SIMPLIFIED")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "simplified-v1"}

@app.post("/webhooks/typeform")
async def typeform_webhook(request: Request):
    """SIMPLEST POSSIBLE webhook - just receive and acknowledge.
    
    No qualification, no Slack, no database - just receive and return OK.
    This is for TESTING to ensure webhook reception works.
    """
    try:
        # Get the raw body
        body = await request.body()
        logger.info(f"📥 Webhook received: {len(body)} bytes")
        
        # Try to parse as JSON
        try:
            data = await request.json()
            logger.info(f"✅ JSON parsed successfully")
            logger.info(f"   Keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
        except Exception as e:
            logger.error(f"❌ JSON parse failed: {str(e)}")
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "Invalid JSON"}
            )
        
        # Return success
        logger.info("✅ Webhook processed successfully")
        return {"ok": True, "message": "Webhook received"}
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(e)}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
