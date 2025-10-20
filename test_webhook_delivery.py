#!/usr/bin/env python3
"""Test Typeform webhook delivery to Railway endpoint."""

import requests
import json
from datetime import datetime

# Railway URL
WEBHOOK_URL = "https://hume-dspy-agent-production.up.railway.app/webhooks/typeform"

# Sample Typeform webhook payload (realistic)
test_payload = {
    "event_id": "test_" + datetime.now().strftime("%Y%m%d_%H%M%S"),
    "event_type": "form_response",
    "form_response": {
        "form_id": "test_form",
        "token": "test_token_123",
        "landed_at": "2025-10-20T18:57:00Z",
        "submitted_at": "2025-10-20T18:57:30Z",
        "definition": {
            "id": "test_form",
            "title": "Test Lead Form",
            "fields": [
                {"id": "field1", "title": "First Name", "type": "short_text"},
                {"id": "field2", "title": "Last Name", "type": "short_text"},
                {"id": "field3", "title": "Email", "type": "email"},
                {"id": "field4", "title": "Company", "type": "short_text"},
                {"id": "field5", "title": "Phone", "type": "phone_number"}
            ]
        },
        "answers": [
            {
                "type": "text",
                "text": "Test",
                "field": {"id": "field1", "type": "short_text", "ref": "first_name"}
            },
            {
                "type": "text",
                "text": "Webhook",
                "field": {"id": "field2", "type": "short_text", "ref": "last_name"}
            },
            {
                "type": "email",
                "email": "test.webhook@example.com",
                "field": {"id": "field3", "type": "email", "ref": "email"}
            },
            {
                "type": "text",
                "text": "Test Company Inc",
                "field": {"id": "field4", "type": "short_text", "ref": "company"}
            },
            {
                "type": "phone_number",
                "phone_number": "+1234567890",
                "field": {"id": "field5", "type": "phone_number", "ref": "phone"}
            }
        ]
    }
}

print("=" * 80)
print("🧪 WEBHOOK DELIVERY TEST")
print("=" * 80)
print(f"Target URL: {WEBHOOK_URL}")
print(f"Payload size: {len(json.dumps(test_payload))} bytes")
print()

try:
    print("📤 Sending test webhook...")
    response = requests.post(
        WEBHOOK_URL,
        json=test_payload,
        headers={"Content-Type": "application/json"},
        timeout=30
    )
    
    print()
    print("=" * 80)
    print("📥 RESPONSE RECEIVED")
    print("=" * 80)
    print(f"Status Code: {response.status_code}")
    print(f"Response Time: {response.elapsed.total_seconds():.2f}s")
    print()
    
    if response.status_code == 200:
        print("✅ SUCCESS - Webhook delivered!")
        try:
            response_json = response.json()
            print()
            print("Response Body:")
            print(json.dumps(response_json, indent=2))
        except:
            print("Response Body (text):")
            print(response.text)
    else:
        print(f"❌ FAILED - Status {response.status_code}")
        print()
        print("Response Body:")
        print(response.text)
    
    print()
    print("=" * 80)
    print("🔍 CHECK RAILWAY LOGS FOR PROCESSING")
    print("=" * 80)
    print("Run: railway logs --lines 50")
    print()
    
except requests.exceptions.ConnectionError as e:
    print(f"❌ CONNECTION ERROR: {e}")
    print("   Railway server may be down or URL incorrect")
except requests.exceptions.Timeout:
    print("❌ TIMEOUT: Server didn't respond within 30 seconds")
except Exception as e:
    print(f"❌ ERROR: {type(e).__name__}: {e}")
