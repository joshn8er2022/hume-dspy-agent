#!/usr/bin/env python3
"""
Run all Typeform test scenarios and validate results.
This script automates form submission and validation for HOT, WARM, and COLD scenarios.
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import Dict, Any, List
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from test_typeform_puppeteer_automated import TypeformPuppeteerTester


async def validate_all_scenarios(test_emails: Dict[str, str]) -> Dict[str, Any]:
    """Validate all submitted scenarios."""
    print(f"\n{'='*70}")
    print("🔍 VALIDATING ALL SUBMISSIONS")
    print(f"{'='*70}\n")
    
    results = {}
    
    for scenario, email in test_emails.items():
        print(f"\n{'#'*70}")
        print(f"Validating {scenario.upper()} scenario...")
        print(f"{'#'*70}\n")
        
        tester = TypeformPuppeteerTester(scenario)
        tester.test_email = email
        
        validation = await tester.validate_webhook_response(wait_seconds=35)
        tester.print_results(validation)
        results[scenario] = {
            "email": email,
            "validation": validation
        }
        
        # Wait between validations
        if scenario != list(test_emails.keys())[-1]:
            print("\n⏳ Waiting 5 seconds before next validation...\n")
            await asyncio.sleep(5)
    
    return results


def print_final_summary(results: Dict[str, Any]):
    """Print final summary of all tests."""
    print(f"\n{'='*70}")
    print("📊 FINAL TEST SUMMARY")
    print(f"{'='*70}\n")
    
    for scenario, data in results.items():
        validation = data["validation"]
        email = data["email"]
        
        status = "✅ PASS" if (
            validation.get("lead_saved") and 
            validation.get("qualification_complete")
        ) else "❌ FAIL"
        
        print(f"{scenario.upper():<10} {status}")
        print(f"  Email: {email}")
        if validation.get("tier"):
            print(f"  Tier: {validation['tier']}, Score: {validation.get('score', 'N/A')}")
        if validation.get("errors"):
            print(f"  Errors: {len(validation['errors'])}")
        print()
    
    # Overall status
    all_passed = all(
        r["validation"].get("lead_saved") and 
        r["validation"].get("qualification_complete")
        for r in results.values()
    )
    
    print(f"{'='*70}")
    if all_passed:
        print("✅ ALL TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED - Review details above")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🧪 AUTOMATED TYPEFORM TESTING - ALL SCENARIOS")
    print("="*70)
    print("\nThis script will:")
    print("1. Guide you through submitting 3 test scenarios")
    print("2. Validate webhook processing for each")
    print("3. Report results")
    print("\n" + "="*70 + "\n")
    
    # Generate test emails for each scenario
    timestamp = int(datetime.utcnow().timestamp())
    test_emails = {
        "hot": f"test.automated.hot.{timestamp}@example.com",
        "warm": f"test.automated.warm.{timestamp + 1}@example.com",
        "cold": f"test.automated.cold.{timestamp + 2}@example.com"
    }
    
    print("📝 Test Emails Generated:")
    for scenario, email in test_emails.items():
        print(f"  {scenario.upper():<10} {email}")
    
    print("\n" + "="*70)
    print("STEP 1: Form Submission")
    print("="*70)
    print("\nPlease submit the form 3 times using these emails:")
    print("\n1. HOT Scenario:")
    print(f"   Email: {test_emails['hot']}")
    print("   Patient Volume: 301+ patients (Option C)")
    print("   Business Size: Large corporation (Option C)")
    print("   Name: Sarah Johnson")
    print("   Company: Wellness Medical Center")
    
    print("\n2. WARM Scenario:")
    print(f"   Email: {test_emails['warm']}")
    print("   Patient Volume: 51-300 patients (Option B)")
    print("   Business Size: Medium-sized business (Option B)")
    print("   Name: Michael Chen")
    print("   Company: Family Health Clinic")
    
    print("\n3. COLD Scenario:")
    print(f"   Email: {test_emails['cold']}")
    print("   Patient Volume: 1-50 patients (Option A)")
    print("   Business Size: Small business (Option A)")
    print("   Name: David Williams")
    print("   Company: Independent Practice")
    
    input("\n⏸️  Press ENTER after you've submitted all 3 forms to start validation...")
    
    # Validate all scenarios
    results = asyncio.run(validate_all_scenarios(test_emails))
    
    # Print final summary
    print_final_summary(results)
    
    print("✅ Testing complete! Check the results above.")

