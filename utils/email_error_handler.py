"""
Robust email error handling for GMass integration.
"""
import requests
import logging
from typing import Dict, Any, Optional
from config.settings import settings

logger = logging.getLogger(__name__)

def send_email_via_gmass(email_data: Dict[str, Any]) -> Dict[str, Any]:
    """Send email via GMass with comprehensive error handling."""
    
    if not settings.GMASS_API_KEY:
        logger.error("❌ GMass API key not configured")
        return {"success": False, "error": "GMass API key missing"}
    
    try:
        # Validate required fields
        required_fields = ['to', 'subject', 'body']
        missing_fields = [field for field in required_fields if not email_data.get(field)]
        
        if missing_fields:
            logger.error(f"❌ Missing required fields: {missing_fields}")
            return {"success": False, "error": f"Missing fields: {missing_fields}"}
        
        # Prepare request
        headers = {
            "Authorization": f"Bearer {settings.GMASS_API_KEY}",
            "Content-Type": "application/json"
        }
        
        url = f"{settings.GMASS_BASE_URL}/api/v1/emails"
        
        logger.info(f"📧 Sending email via GMass to {email_data['to']}")
        
        response = requests.post(
            url,
            headers=headers,
            json=email_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✅ Email sent successfully: {email_data['to']}")
            return {
                "success": True, 
                "response_id": result.get('id'),
                "message_id": result.get('messageId'),
                "response_data": result
            }
        else:
            error_msg = f"GMass API error: {response.status_code} - {response.text}"
            logger.error(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
            
    except Exception as e:
        error_msg = f"GMass error: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {"success": False, "error": error_msg}

def validate_email_delivery(email_result: Dict[str, Any], expected_to: str) -> bool:
    """Validate email delivery success."""
    
    if not email_result.get("success"):
        logger.error(f"❌ Email delivery failed for {expected_to}: {email_result.get('error')}")
        return False
    
    logger.info(f"✅ Email validation passed for {expected_to}")
    return True
