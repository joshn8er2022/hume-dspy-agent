#!/usr/bin/env python3
"""Test GMass API integration with correct two-step process.

This script tests the fixed GMass implementation:
1. Create campaign draft
2. Send campaign immediately

Usage:
    python test_gmass.py
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_gmass_integration():
    """Test GMass email sending with the corrected API."""
    from utils.email_client import EmailClient
    
    # Check for API key
    api_key = os.getenv("GMASS_API_KEY")
    from_email = os.getenv("FROM_EMAIL", "josh@humehealth.com")
    
    if not api_key:
        logger.error("❌ GMASS_API_KEY not set in environment")
        logger.info("   Set it with: export GMASS_API_KEY='your-api-key'")
        return False
    
    logger.info(f"✅ GMASS_API_KEY found: {api_key[:10]}...")
    logger.info(f"✅ FROM_EMAIL: {from_email}")
    
    # Initialize email client
    email_client = EmailClient()
    
    # Test data
    test_email = input("\nEnter test email address (or press Enter to skip actual send): ").strip()
    
    if not test_email:
        logger.info("⚠️ No email provided, skipping actual send test")
        logger.info("✅ GMass client initialized successfully")
        return True
    
    # Confirm send
    confirm = input(f"\n⚠️ Send test email to {test_email}? (yes/no): ").strip().lower()
    if confirm != "yes":
        logger.info("Test cancelled by user")
        return True
    
    # Test lead data
    lead_data = {
        "first_name": "Test",
        "last_name": "User",
        "company": "Test Clinic",
        "email": test_email
    }
    
    logger.info(f"\n📧 Sending test email to {test_email}...")
    
    # Send test email
    success = email_client.send_email(
        to_email=test_email,
        lead_id="test-12345678",
        template_type="initial_outreach",
        tier="HOT",
        lead_data=lead_data
    )
    
    if success:
        logger.info("\n✅ TEST PASSED: Email sent successfully via GMass!")
        logger.info("   Check your Gmail account for:")
        logger.info("   1. Email in Sent folder")
        logger.info("   2. GMass campaign in GMass dashboard")
        logger.info("   3. Email delivered to test recipient")
        return True
    else:
        logger.error("\n❌ TEST FAILED: Email send failed")
        logger.error("   Check logs above for error details")
        return False


def main():
    """Run GMass integration test."""
    logger.info("=" * 70)
    logger.info("GMass API Integration Test")
    logger.info("=" * 70)
    logger.info("")
    logger.info("This test verifies the corrected GMass API implementation:")
    logger.info("  1. POST /api/campaigndrafts → Create draft")
    logger.info("  2. POST /api/campaigns/{draftId} → Send campaign")
    logger.info("")
    
    try:
        success = test_gmass_integration()
        
        logger.info("\n" + "=" * 70)
        if success:
            logger.info("✅ GMass integration test PASSED")
        else:
            logger.info("❌ GMass integration test FAILED")
        logger.info("=" * 70)
        
        sys.exit(0 if success else 1)
    
    except Exception as e:
        logger.error(f"\n❌ Test error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
