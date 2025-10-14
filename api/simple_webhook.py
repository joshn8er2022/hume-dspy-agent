from fastapi import FastAPI, Request
import logging

logger = logging.getLogger(__name__)

app = FastAPI()

@app.post("/webhooks/typeform")
async def typeform_webhook(request: Request):
    """SIMPLEST POSSIBLE webhook - just receive and acknowledge."""
    try:
        # Get the data
        data = await request.json()
        
        # Log it
        logger.info(f"✅ Webhook received: {len(str(data))} bytes")
        
        # Return success
        return {"ok": True}
        
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
