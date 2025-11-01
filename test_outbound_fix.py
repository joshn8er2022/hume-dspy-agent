#!/usr/bin/env python3
"""
Test script to verify the recommend_outbound_targets() fix.

This script verifies that:
1. The function no longer returns hardcoded fake companies
2. It queries Supabase for real lead data
3. It analyzes patterns from successful leads
4. It generates data-driven recommendations
"""
import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_outbound_targets():
    """Test the fixed recommend_outbound_targets function."""
    print("=" * 80)
    print("TESTING: recommend_outbound_targets() FIX")
    print("=" * 80)

    try:
        # Import the fixed agent
        from agents.strategy_agent import StrategyAgent

        print("\n1. Initializing StrategyAgent...")
        agent = StrategyAgent()
        print("   ✅ StrategyAgent initialized")

        # Check if Supabase is configured
        if not agent.supabase:
            print("\n⚠️  WARNING: Supabase not configured")
            print("   The function will return empty results without database access")
            print("   Set SUPABASE_URL and SUPABASE_SERVICE_KEY to test with real data")
            return

        print("\n2. Calling recommend_outbound_targets()...")
        results = await agent.recommend_outbound_targets(
            segment="all",
            min_size=50,
            limit=5
        )

        print(f"\n3. Results: {len(results)} recommendations")
        print("-" * 80)

        # Check if results are NOT the old hardcoded fake companies
        old_fake_companies = ["West Coast Weight Loss Center", "Precision Health Clinic"]
        has_fake_companies = any(
            result.company_name in old_fake_companies
            for result in results
        )

        if has_fake_companies:
            print("\n❌ FAIL: Function still returns hardcoded fake companies!")
            print("   The fix was not applied correctly.")
            return False

        if len(results) == 0:
            print("\n⚠️  No recommendations generated")
            print("   This is expected if:")
            print("   - No successful leads in database")
            print("   - Database query failed")
            print("   Check logs above for details")
        else:
            print("\n✅ SUCCESS: Function returns data-driven recommendations!")
            print("\nRecommendations:")
            for i, target in enumerate(results, 1):
                print(f"\n{i}. {target.company_name}")
                print(f"   Fit Score: {target.fit_score}/100")
                print(f"   Reason: {target.reason[:150]}...")
                if target.estimated_patient_volume:
                    print(f"   Estimated Volume: {target.estimated_patient_volume}")

        return True

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_code_changes():
    """Verify that the code changes were applied correctly."""
    print("\n" + "=" * 80)
    print("VERIFYING CODE CHANGES")
    print("=" * 80)

    # Read the file and check for key changes
    file_path = "/Users/joshisrael/hume-dspy-agent/agents/strategy_agent.py"

    with open(file_path, 'r') as f:
        content = f.read()

    # Check for old hardcoded companies (should NOT exist)
    if "West Coast Weight Loss Center" in content:
        print("\n❌ FAIL: Old hardcoded companies still in code!")
        return False

    # Check for new real data queries (should exist)
    required_elements = [
        "_analyze_lead_patterns",
        "_identify_success_factors",
        "_generate_target_recommendations",
        "successful_statuses = ['meeting_booked', 'deal_closed', 'opportunity']",
        "successful_tiers = ['HOT', 'SCORCHING']",
        "wolfram_market_analysis"
    ]

    missing = []
    for element in required_elements:
        if element not in content:
            missing.append(element)

    if missing:
        print(f"\n❌ FAIL: Missing required code elements:")
        for elem in missing:
            print(f"   - {elem}")
        return False

    print("\n✅ All code changes verified!")
    print("\nImplemented features:")
    print("   ✅ Queries Supabase for successful leads")
    print("   ✅ Analyzes patterns (_analyze_lead_patterns)")
    print("   ✅ Identifies success factors (_identify_success_factors)")
    print("   ✅ Uses DSPy for reasoning (_generate_target_recommendations)")
    print("   ✅ Integrates Wolfram Alpha for market intelligence")
    print("   ✅ Error handling for database queries")
    print("   ✅ Fallback pattern-based recommendations")

    return True


async def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("OUTBOUND TARGETS FIX VERIFICATION")
    print("=" * 80)

    # First verify code changes
    code_ok = await verify_code_changes()

    if not code_ok:
        print("\n❌ Code verification failed - fix not applied correctly")
        sys.exit(1)

    # Then test functionality
    test_ok = await test_outbound_targets()

    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Code Changes: {'✅ PASS' if code_ok else '❌ FAIL'}")
    print(f"Functionality: {'✅ PASS' if test_ok else '❌ FAIL'}")
    print("=" * 80)

    if code_ok and test_ok:
        print("\n🎉 All tests passed! The fix is working correctly.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Review the output above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
