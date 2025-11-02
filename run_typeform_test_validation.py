#!/usr/bin/env python3
"""
Typeform Testing: Run all 3 scenarios and validate results.

This script:
1. Generates unique test emails for HOT/WARM/COLD scenarios
2. Provides clear submission instructions
3. Waits for you to submit all 3 forms manually
4. Validates webhook processing for each submission
5. Reports comprehensive results

Usage:
    python run_typeform_test_validation.py
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_typeform_puppeteer_automated import TypeformPuppeteerTester


def print_submission_instructions(test_emails: dict):
    """Print clear instructions for manual form submission."""
    print("\n" + "="*70)
    print("📝 SUBMISSION INSTRUCTIONS")
    print("="*70)
    print("\nSubmit the Typeform 3 times using these test data:\n")
    
    scenarios = {
        "hot": {
            "email": test_emails["hot"],
            "name": "Sarah Johnson",
            "company": "Wellness Medical Center",
            "patient_volume": "Option C: 301+ patients",
            "business_size": "Option C: Large corporation (20+ employees)",
            "description": "Large medical center with 500+ patients, need EMR integration"
        },
        "warm": {
            "email": test_emails["warm"],
            "name": "Michael Chen",
            "company": "Family Health Clinic",
            "patient_volume": "Option B: 51-300 patients",
            "business_size": "Option B: Medium-sized business (6-20 employees)",
            "description": "Growing clinic with 150 patients, evaluating options"
        },
        "cold": {
            "email": test_emails["cold"],
            "name": "David Williams",
            "company": "Independent Practice",
            "patient_volume": "Option A: 1-50 patients",
            "business_size": "Option A: Small business (1-5 employees)",
            "description": "Just starting out, exploring body composition tracking"
        }
    }
    
    for i, (scenario, data) in enumerate(scenarios.items(), 1):
        print(f"\n{i}. {scenario.upper()} Scenario:")
        print(f"   {'─'*65}")
        print(f"   Email:      {data['email']}")
        print(f"   Name:       {data['name']}")
        print(f"   Company:    {data['company']}")
        print(f"   Patient Vol: {data['patient_volume']}")
        print(f"   Business:   {data['business_size']}")
        print(f"   Use Case:   {data['description']}")
    
    print("\n" + "="*70)
    print("🌐 Typeform URL:")
    print("="*70)
    print("https://form.typeform.com/to/F7whHyXK#affiliate=xxxxx&wholesale_retail=xxxxx&professional=xxxxx")
    print("\n" + "="*70 + "\n")


async def validate_all_submissions(test_emails: dict):
    """Validate all three submissions."""
    print("\n" + "="*70)
    print("🔍 VALIDATING SUBMISSIONS")
    print("="*70 + "\n")
    
    results = {}
    
    for scenario, email in test_emails.items():
        print(f"\n{'#'*70}")
        print(f"Validating {scenario.upper()} scenario")
        print(f"{'#'*70}")
        print(f"Test Email: {email}\n")
        
        tester = TypeformPuppeteerTester(scenario)
        tester.test_email = email
        
        validation = await tester.validate_webhook_response(wait_seconds=35)
        tester.print_results(validation)
        
        results[scenario] = {
            "email": email,
            "validation": validation
        }
        
        # Wait between validations (except last one)
        if scenario != list(test_emails.keys())[-1]:
            print("\n⏳ Waiting 5 seconds before next validation...\n")
            await asyncio.sleep(5)
    
    return results


def print_final_summary(results: dict):
    """Print comprehensive final summary."""
    print("\n" + "="*70)
    print("📊 FINAL TEST SUMMARY")
    print("="*70 + "\n")
    
    summary_table = []
    
    for scenario, data in results.items():
        validation = data["validation"]
        email = data["email"]
        
        status_icon = "✅ PASS" if (
            validation.get("lead_saved") and 
            validation.get("qualification_complete")
        ) else "❌ FAIL"
        
        summary_table.append({
            "scenario": scenario.upper(),
            "status": status_icon,
            "email": email,
            "tier": validation.get("tier", "N/A"),
            "score": validation.get("score", "N/A"),
            "slack": "✅" if validation.get("slack_notification") else "❌",
            "errors": len(validation.get("errors", []))
        })
    
    # Print table
    print(f"{'Scenario':<12} {'Status':<10} {'Tier':<12} {'Score':<8} {'Slack':<8} {'Errors':<8}")
    print("─" * 70)
    for row in summary_table:
        print(f"{row['scenario']:<12} {row['status']:<10} {row['tier']:<12} {row['score']:<8} {row['slack']:<8} {row['errors']:<8}")
    
    print("\n" + "="*70)
    print("DETAILED RESULTS")
    print("="*70 + "\n")
    
    for row in summary_table:
        print(f"\n{row['scenario']} Scenario:")
        print(f"  Email: {row['email']}")
        print(f"  Status: {row['status']}")
        print(f"  Tier: {row['tier']}")
        print(f"  Score: {row['score']}")
        print(f"  Slack Notification: {row['slack']}")
        if row['errors'] > 0:
            print(f"  ⚠️  {row['errors']} error(s) - check details above")
    
    # Overall status
    all_passed = all(
        r["validation"].get("lead_saved") and 
        r["validation"].get("qualification_complete")
        for r in results.values()
    )
    
    print("\n" + "="*70)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        print("\nAll submissions were processed successfully:")
        print("  ✅ Leads saved to database")
        print("  ✅ Qualification completed")
        print("  ✅ Tiers and scores assigned")
    else:
        print("⚠️  SOME TESTS FAILED")
        print("\nReview the detailed results above to identify issues.")
        print("Common issues:")
        print("  • Webhook not received (check Railway logs)")
        print("  • Processing timeout (increase wait time)")
        print("  • Database connection issues")
    print("="*70 + "\n")


async def main():
    """Main execution flow."""
    print("\n" + "="*70)
    print("🧪 TYPEFORM TESTING - ALL SCENARIOS")
    print("="*70)
    print("\nThis script will:")
    print("  1. Generate unique test emails for 3 scenarios")
    print("  2. Guide you through manual form submission")
    print("  3. Validate webhook processing for each submission")
    print("  4. Report comprehensive results")
    print("\n" + "="*70)
    
    # Generate unique test emails
    timestamp = int(datetime.utcnow().timestamp())
    test_emails = {
        "hot": f"test.automated.hot.{timestamp}@example.com",
        "warm": f"test.automated.warm.{timestamp + 1}@example.com",
        "cold": f"test.automated.cold.{timestamp + 2}@example.com"
    }
    
    print("\n📧 Generated Test Emails:")
    for scenario, email in test_emails.items():
        print(f"  {scenario.upper():<8} {email}")
    
    # Print submission instructions
    print_submission_instructions(test_emails)
    
    # Wait for user to submit forms
    print("⏸️  Please submit all 3 forms using the data above.")
    print("   Open the Typeform URL in your browser and fill it 3 times.\n")
    input("   Press ENTER when you've submitted all 3 forms to start validation...")
    
    # Validate all submissions
    results = await validate_all_submissions(test_emails)
    
    # Print final summary
    print_final_summary(results)
    
    print("✅ Testing complete!\n")
    
    # Save results to file
    results_file = f"typeform_test_results_{timestamp}.json"
    import json
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": datetime.utcnow().isoformat(),
            "test_emails": test_emails,
            "results": {
                k: {
                    "email": v["email"],
                    "tier": v["validation"].get("tier"),
                    "score": v["validation"].get("score"),
                    "lead_saved": v["validation"].get("lead_saved"),
                    "qualification_complete": v["validation"].get("qualification_complete"),
                    "slack_notification": v["validation"].get("slack_notification"),
                    "errors": v["validation"].get("errors", [])
                }
                for k, v in results.items()
            }
        }, f, indent=2)
    
    print(f"📄 Results saved to: {results_file}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

