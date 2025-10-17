"""Debug lead scoring using A2A introspection locally.

This script allows us to test qualification scoring on specific leads
and see the agent's reasoning in detail.
"""

import os
import sys
import json
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Setup path
sys.path.insert(0, os.path.dirname(__file__))

from agents.introspection import get_introspection_service, IntrospectionRequest

def analyze_lead(lead_id: str):
    """Analyze a lead's qualification scoring."""

    print(f"\n{'='*70}")
    print(f"A2A INTROSPECTION: Lead {lead_id}")
    print(f"{'='*70}\n")

    # Create introspection request
    request = IntrospectionRequest(
        agent_type="qualification",
        query_type="explain_score",
        lead_id=lead_id
    )

    # Get introspection service and query
    print("🔍 Initializing introspection service...")
    service = get_introspection_service()

    print("🧠 Running qualification analysis...\n")
    response = service.handle_query(request)

    if not response.success:
        print(f"❌ ERROR: {response.error}")
        return

    data = response.data
    breakdown = data['breakdown']

    print(f"{'='*70}")
    print(f"QUALIFICATION RESULTS")
    print(f"{'='*70}")
    print(f"Lead ID: {data['lead_id']}")
    print(f"Score: {breakdown['total_score']}/100")
    print(f"Tier: {breakdown['tier'].upper()}")
    print(f"Qualified: {breakdown['is_qualified']}")
    print(f"Processing Time: {breakdown['processing_time_ms']}ms")

    print(f"\n{'='*70}")
    print(f"SCORE BREAKDOWN")
    print(f"{'='*70}")
    for criterion, score in breakdown['criteria'].items():
        max_score = {
            'business_size': 20,
            'patient_volume': 20,
            'industry_fit': 15,
            'response_completeness': 15,
            'calendly_booking': 10,
            'response_quality': 10,
            'company_data': 10
        }.get(criterion, 100)
        print(f"{criterion.replace('_', ' ').title():.<40} {score:>3}/{max_score}")

    print(f"\n{'='*70}")
    print(f"AGENT REASONING")
    print(f"{'='*70}")
    print(breakdown['reasoning'])

    print(f"\n{'='*70}")
    print(f"KEY FACTORS")
    print(f"{'='*70}")
    for factor in breakdown['key_factors']:
        print(f"  ✅ {factor}")

    print(f"\n{'='*70}")
    print(f"CONCERNS")
    print(f"{'='*70}")
    for concern in breakdown['concerns']:
        print(f"  ⚠️  {concern}")

    print(f"\n{'='*70}")
    print(f"MISSING FIELDS (Could Improve Score)")
    print(f"{'='*70}")
    for field in breakdown['missing_fields']:
        print(f"  📝 {field}")

    print(f"\n{'='*70}")
    print(f"RAW LEAD DATA")
    print(f"{'='*70}")
    print(json.dumps(data['raw_answers'], indent=2))

    print(f"\n{'='*70}")
    print(f"RECOMMENDED ACTIONS")
    print(f"{'='*70}")
    for action in data['next_actions']:
        print(f"  🎯 {action}")

    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_lead_scoring.py <lead_id>")
        print("\nRecent lead IDs:")
        print("  88 Tactical: 6912d0c5-443b-440e-8a49-5fca7ebc7167")
        print("  PayPal: e382caf0-df80-47c1-9b2e-ef018f0a6f35")
        print("  Fit Finest: 27ce6dc7-8448-4b30-add2-c0c85f71f6ff")
        sys.exit(1)

    lead_id = sys.argv[1]
    analyze_lead(lead_id)
