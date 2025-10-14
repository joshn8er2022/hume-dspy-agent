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
    return {"status": "healthy", "version": "simplified-v2"}

@app.post("/")
@app.post("/webhooks/typeform")
async def typeform_webhook(request: Request):
    """SIMPLEST POSSIBLE webhook - accepts at ROOT or /webhooks/typeform.
    
    Typeform is sending to ROOT path, so we accept both.
    """
    try:
        # Log request details
        logger.info("="*80)
        logger.info(f"📥 WEBHOOK RECEIVED at {request.url.path}")
        logger.info(f"   Method: {request.method}")
        logger.info(f"   Headers: {dict(request.headers)}")
        
        # Get the raw body
        body = await request.body()
        logger.info(f"   Body size: {len(body)} bytes")
        
        # Try to parse as JSON
        try:
            data = await request.json()
            logger.info(f"✅ JSON parsed successfully")
            logger.info(f"   Keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
            
            # Log first 500 chars of data for debugging
            import json
            data_str = json.dumps(data, indent=2)
            logger.info(f"   Data preview: {data_str[:500]}...")
            
        except Exception as e:
            logger.error(f"❌ JSON parse failed: {str(e)}")
            logger.error(f"   Raw body: {body[:500]}")
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "Invalid JSON"}
            )
        
        # Return success
        logger.info("✅ Webhook processed successfully")
        logger.info("="*80)
        return {"ok": True, "message": "Webhook received"}
        
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
