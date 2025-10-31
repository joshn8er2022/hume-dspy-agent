#!/usr/bin/env python3
"""Test AI-Driven Tier Determination.

Tests the new AI-driven tier classifier against hardcoded thresholds
to demonstrate improved context-awareness and "hidden gem" detection.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.lead import Lead, ResponseType
from agents.inbound_agent import InboundAgent
import dspy
from datetime import datetime

print("="*70)
print("🧪 AI-Driven Tier Determination Test")
print("="*70)

# Configure DSPy
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
if openrouter_api_key:
    lm = dspy.LM('openrouter/anthropic/claude-sonnet-4.5', api_key=openrouter_api_key)
    print("✅ DSPy configured with OpenRouter Sonnet 4.5")
else:
    print("❌ No OPENROUTER_API_KEY found")
    sys.exit(1)

with dspy.context(lm=lm):
    # Initialize InboundAgent
    agent = InboundAgent()

    # Test scenarios
    test_cases = [
        {
            "name": "Hidden Gem: Low score but Calendly booking",
            "lead_data": {
                "id": "test-1",
                "typeform_id": "token-1",
                "form_id": "form-1",
                "email": "doctor@clinic.com",
                "company": "Small Wellness Clinic",
                "first_name": "Dr. Sarah",
                "last_name": "Johnson",
                "raw_answers": {
                    "business_size": "Small business (1-5 employees)",
                    "patient_volume": "50-100 patients",
                    "calendly_url": "https://calendly.com/dr-sarah/30min",
                    "use_case": "We need better body composition tracking for our weight loss program"
                },
                "calendly_url": "https://calendly.com/dr-sarah/30min",
                "response_type": ResponseType.COMPLETE,
                "submitted_at": datetime.utcnow()
            },
            "expected_hardcoded": "WARM",  # Score ~65
            "expected_ai": "HOT or SCORCHING",  # Calendly = strong intent
        },
        {
            "name": "High score but no engagement",
            "lead_data": {
                "id": "test-2",
                "typeform_id": "token-2",
                "form_id": "form-1",
                "email": "info@bigclinic.com",
                "company": "Large Medical Center",
                "raw_answers": {
                    "business_size": "Large business (50+ employees)",
                    "patient_volume": "300+ patients",
                    "use_case": "Exploring options"
                },
                "response_type": ResponseType.PARTIAL,
                "submitted_at": None
            },
            "expected_hardcoded": "SCORCHING",  # Score ~92
            "expected_ai": "HOT",  # No Calendly, partial submission = lower intent
        },
        {
            "name": "Medium score with complete submission",
            "lead_data": {
                "id": "test-3",
                "typeform_id": "token-3",
                "form_id": "form-1",
                "email": "owner@gym.com",
                "company": "Fitness Studio",
                "raw_answers": {
                    "business_size": "Small business (1-5 employees)",
                    "patient_volume": "100-300 patients",
                    "use_case": "We want to add body composition analysis to our training programs. Currently using basic scales but clients want more detailed metrics."
                },
                "response_type": ResponseType.COMPLETE,
                "submitted_at": datetime.utcnow()
            },
            "expected_hardcoded": "WARM",  # Score ~70
            "expected_ai": "WARM or HOT",  # Complete + detailed use case = engaged
        }
    ]

    print("
" + "="*70)
    print("TEST RESULTS")
    print("="*70)

    for i, test_case in enumerate(test_cases, 1):
        print(f"
{i}. {test_case['name']}")
        print("-" * 70)

        # Create Lead object
        lead = Lead(**test_case['lead_data'])

        # Qualify the lead
        print("
🔄 Qualifying lead...")
        result = agent.forward(lead)

        print(f"
📊 Results:")
        print(f"   Score: {result.score}/100")
        print(f"   Tier: {result.tier}")
        print(f"   Expected (Hardcoded): {test_case['expected_hardcoded']}")
        print(f"   Expected (AI): {test_case['expected_ai']}")
        print(f"
💭 Reasoning:")
        print(f"   {result.reasoning[:300]}...")

        # Check if AI was used
        if os.getenv("USE_AI_TIER_DETERMINATION", "false").lower() == "true":
            print("
✅ AI tier determination was used")
        else:
            print("
⚠️  Hardcoded thresholds were used (set USE_AI_TIER_DETERMINATION=true to test AI)")

print("
" + "="*70)
print("TEST COMPLETE")
print("="*70)
print("
To test AI-driven tier determination:")
print("  export USE_AI_TIER_DETERMINATION=true")
print("  python test_ai_tier_determination.py")
