#!/usr/bin/env python3
"""
Production Bug Fix Verification Script

Tests that both critical bugs are fixed in the live Railway deployment:
1. analyze_pipeline() returns real Supabase data (not mock)
2. recommend_outbound_targets() returns real recommendations (not fake companies)
"""

import requests
import json
from typing import Dict, Any

BASE_URL = "https://hume-dspy-agent-production.up.railway.app"

# Known bad patterns that should NOT appear
MOCK_DATA_PATTERNS = [
    "Example Corp",
    "Mock Company",
    "Test Inc",
    "Acme Corp",
    "TechCo",
    "DataInc",
    "Sample Inc",
    "Placeholder Company"
]


def verify_analyze_pipeline_fix() -> bool:
    """Verify Bug #1 is fixed: analyze_pipeline returns real data"""
    print("\n" + "=" * 60)
    print("🔍 BUG FIX #1: analyze_pipeline()")
    print("=" * 60)
    print("Testing: Strategy Agent queries real Supabase data...")

    try:
        response = requests.post(
            f"{BASE_URL}/api/strategy/analyze-pipeline",
            json={"days": 7},
            timeout=30
        )

        if response.status_code != 200:
            print(f"❌ FAILED: HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False

        data = response.json()
        response_text = json.dumps(data)

        # Check for mock data
        has_mock_data = any(pattern in response_text for pattern in MOCK_DATA_PATTERNS)
        if has_mock_data:
            print("❌ FAILED: Response contains mock data patterns")
            for pattern in MOCK_DATA_PATTERNS:
                if pattern in response_text:
                    print(f"   Found: '{pattern}'")
            return False

        # Verify structure
        required_fields = ['total_leads', 'by_tier', 'conversion_rate', 'insights']
        missing_fields = [f for f in required_fields if f not in data]
        if missing_fields:
            print(f"❌ FAILED: Missing fields: {missing_fields}")
            return False

        # Check for TODOs
        if 'TODO' in response_text or 'FIXME' in response_text:
            print("❌ FAILED: Response contains TODO/FIXME markers")
            return False

        # Success
        print("✅ PASSED: analyze_pipeline() returns real data")
        print(f"   Total leads: {data.get('total_leads', 0)}")
        print(f"   Conversion rate: {data.get('conversion_rate', 0):.1%}")
        print(f"   Insights count: {len(data.get('insights', []))}")

        return True

    except requests.Timeout:
        print("❌ FAILED: Request timeout (30s)")
        return False
    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__}: {e}")
        return False


def verify_recommend_targets_fix() -> bool:
    """Verify Bug #2 is fixed: recommend_targets analyzes real patterns"""
    print("\n" + "=" * 60)
    print("🔍 BUG FIX #2: recommend_outbound_targets()")
    print("=" * 60)
    print("Testing: Strategy Agent uses real pattern analysis...")

    try:
        response = requests.post(
            f"{BASE_URL}/api/strategy/recommend-targets",
            json={"segment": "all", "min_size": 0, "limit": 5},
            timeout=30
        )

        if response.status_code != 200:
            print(f"❌ FAILED: HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False

        data = response.json()
        response_text = json.dumps(data)

        # Check for fake companies
        has_fake_companies = any(pattern in response_text for pattern in MOCK_DATA_PATTERNS)
        if has_fake_companies:
            print("❌ FAILED: Response contains fake company names")
            for pattern in MOCK_DATA_PATTERNS:
                if pattern in response_text:
                    print(f"   Found: '{pattern}'")
            return False

        # Check for TODOs
        if 'TODO' in response_text or 'FIXME' in response_text:
            print("❌ FAILED: Response contains TODO/FIXME markers")
            return False

        # Verify it's a list
        if not isinstance(data, list):
            print(f"❌ FAILED: Expected list, got {type(data).__name__}")
            return False

        # Success
        print("✅ PASSED: recommend_outbound_targets() uses real analysis")
        print(f"   Recommendations returned: {len(data)}")
        if data:
            print(f"   Sample: {data[0].get('company_name', 'N/A') if isinstance(data[0], dict) else data[0]}")

        return True

    except requests.Timeout:
        print("❌ FAILED: Request timeout (30s)")
        return False
    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__}: {e}")
        return False


def verify_health_check() -> bool:
    """Verify basic health endpoint"""
    print("\n" + "=" * 60)
    print("🏥 HEALTH CHECK")
    print("=" * 60)

    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)

        if response.status_code != 200:
            print(f"❌ FAILED: HTTP {response.status_code}")
            return False

        data = response.json()

        if data.get('status') != 'healthy':
            print(f"❌ FAILED: Status is '{data.get('status')}'")
            return False

        print("✅ PASSED: Application is healthy")
        print(f"   Status: {data.get('status')}")
        print(f"   Version: {data.get('version')}")
        print(f"   Supabase: {data.get('supabase')}")

        return True

    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__}: {e}")
        return False


def main():
    """Run all verification tests"""
    print("\n" + "=" * 60)
    print("  PRODUCTION BUG FIX VERIFICATION")
    print("  Deployment: Railway (calm-stillness)")
    print("  URL: " + BASE_URL)
    print("=" * 60)

    results = {
        "Health Check": verify_health_check(),
        "Bug Fix #1 (analyze_pipeline)": verify_analyze_pipeline_fix(),
        "Bug Fix #2 (recommend_targets)": verify_recommend_targets_fix()
    }

    # Summary
    print("\n" + "=" * 60)
    print("  VERIFICATION SUMMARY")
    print("=" * 60)

    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}  {test_name}")

    print("\n" + "-" * 60)
    print(f"Result: {passed}/{total} tests passed")
    print("=" * 60)

    if passed == total:
        print("\n🎉 ALL VERIFICATIONS PASSED!")
        print("Both critical bugs are fixed in production.")
        return 0
    else:
        print("\n⚠️  SOME VERIFICATIONS FAILED")
        print("Check the output above for details.")
        return 1


if __name__ == "__main__":
    exit(main())
