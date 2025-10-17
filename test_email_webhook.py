#!/usr/bin/env python3
"""Test Email + Webhook Submission Script.

This script:
1. Creates a test lead submission (simulates Typeform webhook)
2. Submits to the /typeform endpoint
3. System qualifies the lead
4. Sends email via GMass to buildoutinc@gmail.com

Usage:
    python test_email_webhook.py
"""

import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_ENDPOINT = os.getenv("API_ENDPOINT", "https://hume-dspy-agent-production.up.railway.app")
TYPEFORM_WEBHOOK_SECRET = os.getenv("TYPEFORM_WEBHOOK_SECRET", "test-secret")
TEST_EMAIL = "buildoutinc@gmail.com"

print("=" * 70)
print("🧪 Test Email + Webhook Submission")
print("=" * 70)
print()


def create_test_webhook_payload() -> dict:
    """Create a realistic Typeform webhook payload for testing."""
    
    # Create test lead that will qualify as HOT (to trigger email)
    payload = {
        "event_id": f"test_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "event_type": "form_response",
        "form_response": {
            "form_id": "test_form_001",
            "token": f"test_token_{datetime.utcnow().timestamp()}",
            "landed_at": datetime.utcnow().isoformat() + "Z",
            "submitted_at": datetime.utcnow().isoformat() + "Z",
            "definition": {
                "id": "test_form_001",
                "title": "Hume Health Partnership Interest Form (TEST)",
                "fields": []
            },
            "answers": [
                {
                    "type": "email",
                    "email": TEST_EMAIL,
                    "field": {
                        "id": "email_001",
                        "type": "email",
                        "ref": "email",
                        "title": "What's your email address?"
                    }
                },
                {
                    "type": "text",
                    "text": "Build Out",
                    "field": {
                        "id": "name_001",
                        "type": "short_text",
                        "ref": "first_name",
                        "title": "What's your first name?"
                    }
                },
                {
                    "type": "text",
                    "text": "Wellness Clinic",
                    "field": {
                        "id": "company_001",
                        "type": "short_text",
                        "ref": "company",
                        "title": "What's your company name?"
                    }
                },
                {
                    "type": "text",
                    "text": "We're a weight loss clinic managing 200+ patients remotely. Currently using InBody scales but struggling with data integration and patient adherence. Looking for a better solution for body composition tracking that integrates with our EMR and improves patient engagement.",
                    "field": {
                        "id": "description_001",
                        "type": "long_text",
                        "ref": "use_case",
                        "title": "Tell us about your practice and what you're looking for"
                    }
                },
                {
                    "type": "text",
                    "text": "200-300 patients",
                    "field": {
                        "id": "patients_001",
                        "type": "short_text",
                        "ref": "patient_volume",
                        "title": "How many patients do you serve?"
                    }
                },
                {
                    "type": "text",
                    "text": "Weight loss and chronic disease management",
                    "field": {
                        "id": "specialty_001",
                        "type": "short_text",
                        "ref": "specialty",
                        "title": "What's your specialty?"
                    }
                },
                {
                    "type": "boolean",
                    "boolean": True,
                    "field": {
                        "id": "booking_001",
                        "type": "yes_no",
                        "ref": "calendly_booked",
                        "title": "Would you like to schedule a call?"
                    }
                }
            ],
            "calculated": {
                "score": 0
            },
            "variables": []
        }
    }
    
    return payload


def submit_test_webhook(payload: dict, use_webhook_secret: bool = True):
    """Submit test webhook to the API.
    
    Args:
        payload: Typeform webhook payload
        use_webhook_secret: Whether to include webhook secret header
    """
    print("📤 Submitting test webhook...")
    print()
    print("**Test Lead Details:**")
    print(f"   Email: {TEST_EMAIL}")
    print(f"   Name: Build Out")
    print(f"   Company: Wellness Clinic")
    print(f"   Patients: 200-300")
    print(f"   Use Case: Weight loss clinic with 200+ patients")
    print(f"   Calendly Booked: Yes")
    print()
    print("**Expected Qualification:**")
    print(f"   Tier: HOT or SCORCHING (high score)")
    print(f"   Reason: Perfect ICP fit + Calendly booking")
    print(f"   Email: Will be sent via GMass")
    print()
    
    # Prepare headers
    headers = {
        "Content-Type": "application/json"
    }
    
    if use_webhook_secret:
        headers["Typeform-Signature"] = f"sha256={TYPEFORM_WEBHOOK_SECRET}"
    
    # Submit webhook
    try:
        response = requests.post(
            f"{API_ENDPOINT}/typeform",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        print(f"📡 Response Status: {response.status_code}")
        print()
        
        if response.status_code == 200:
            print("✅ Webhook accepted successfully!")
            print()
            print("**What happens next:**")
            print("   1. ✅ Raw event stored in Supabase")
            print("   2. ⏳ Background processing started")
            print("   3. ⏳ Lead qualification (DSPy agent)")
            print("   4. ⏳ Slack notification sent")
            print("   5. ⏳ Email sent via GMass")
            print()
            print("**Check:**")
            print(f"   📧 Email: Check {TEST_EMAIL} inbox (may take 30-60 seconds)")
            print(f"   💬 Slack: Check your #inbound-leads channel")
            print(f"   📊 GMass: Check https://www.gmass.co/app/campaigns")
            print(f"   🗄️ Supabase: Check 'leads' table")
            print()
            
            try:
                response_data = response.json()
                print("**API Response:**")
                print(json.dumps(response_data, indent=2))
            except:
                print("**API Response:**")
                print(response.text)
        
        elif response.status_code == 401:
            print("❌ Webhook signature verification failed")
            print("   Check TYPEFORM_WEBHOOK_SECRET environment variable")
            print()
            print(f"**Response:** {response.text}")
        
        else:
            print(f"❌ Webhook submission failed")
            print(f"**Response:** {response.text}")
        
        return response.status_code == 200
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {str(e)}")
        print()
        print("**Possible causes:**")
        print("   • API endpoint not accessible")
        print("   • Network connectivity issues")
        print("   • Railway service not running")
        return False


def main():
    """Run test email + webhook submission."""
    
    print("**Configuration:**")
    print(f"   API Endpoint: {API_ENDPOINT}")
    print(f"   Test Email: {TEST_EMAIL}")
    print(f"   Webhook Secret: {'✅ Set' if TYPEFORM_WEBHOOK_SECRET != 'test-secret' else '⚠️ Using default'}")
    print()
    
    # Confirm submission
    confirm = input("🚀 Submit test webhook? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("❌ Test cancelled by user")
        return
    
    print()
    
    # Create payload
    payload = create_test_webhook_payload()
    
    # Submit
    success = submit_test_webhook(payload, use_webhook_secret=True)
    
    print()
    print("=" * 70)
    if success:
        print("✅ TEST PASSED: Webhook submitted successfully")
        print()
        print("⏰ Wait 30-60 seconds for:")
        print("   • Email to arrive at buildoutinc@gmail.com")
        print("   • Slack notification in #inbound-leads")
        print("   • GMass campaign to appear in dashboard")
    else:
        print("❌ TEST FAILED: Webhook submission error")
        print()
        print("🔧 Troubleshooting:")
        print("   1. Check Railway logs for errors")
        print("   2. Verify API endpoint is correct")
        print("   3. Check TYPEFORM_WEBHOOK_SECRET matches")
        print("   4. Test with: curl -X GET {API_ENDPOINT}/")
    print("=" * 70)


if __name__ == "__main__":
    main()
