#!/usr/bin/env python3
"""
Validate Typeform submissions without interactive input.
Can validate specific test emails or find recent test submissions.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from test_typeform_puppeteer_automated import TypeformPuppeteerTester


async def find_recent_test_submissions() -> Dict[str, str]:
    """Find recent test submissions in database."""
    try:
        from supabase import create_client
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            print("⚠️  Supabase credentials not configured")
            return {}
        
        supabase = create_client(supabase_url, supabase_key)
        
        # Find leads with test emails from last hour
        result = supabase.table('leads').select('email, tier, qualification_score, created_at').ilike('email', 'test.automated.%').order('created_at', desc=True).limit(10).execute()
        
        if result.data:
            print(f"\n📧 Found {len(result.data)} recent test submissions:\n")
            emails_by_scenario = {}
            
            for lead in result.data:
                email = lead.get('email', '')
                tier = lead.get('tier', '').lower()
                
                # Try to determine scenario from email or tier
                if 'hot' in email.lower() or tier == 'hot':
                    scenario = 'hot'
                elif 'warm' in email.lower() or tier == 'warm':
                    scenario = 'warm'
                elif 'cold' in email.lower() or tier == 'cold':
                    scenario = 'cold'
                else:
                    continue
                
                if scenario not in emails_by_scenario:
                    emails_by_scenario[scenario] = email
                    print(f"  {scenario.upper():<8} {email}")
                    print(f"           Tier: {tier}, Score: {lead.get('qualification_score', 'N/A')}\n")
            
            return emails_by_scenario
        else:
            print("⚠️  No recent test submissions found in database")
            return {}
            
    except Exception as e:
        print(f"❌ Error finding submissions: {e}")
        return {}


async def validate_scenario(scenario: str, email: Optional[str] = None) -> Dict[str, Any]:
    """Validate a single scenario."""
    tester = TypeformPuppeteerTester(scenario)
    
    if email:
        tester.test_email = email
        print(f"\n{'='*70}")
        print(f"🔍 Validating {scenario.upper()} scenario")
        print(f"   Email: {email}")
        print(f"{'='*70}\n")
    else:
        print(f"\n{'='*70}")
        print(f"⚠️  No email provided for {scenario.upper()} scenario")
        print(f"   Expected email: {tester.test_email}")
        print(f"{'='*70}\n")
        print("💡 Submit the form with the email above, then run validation again")
        return {"error": "No email provided"}
    
    validation = await tester.validate_webhook_response(wait_seconds=30)
    tester.print_results(validation)
    
    return validation


async def validate_all_scenarios(test_emails: Optional[Dict[str, str]] = None):
    """Validate all three scenarios."""
    if not test_emails:
        print("\n🔍 Searching for recent test submissions...")
        test_emails = await find_recent_test_submissions()
    
    if not test_emails:
        print("\n❌ No test emails found.")
        print("\n📝 To validate submissions:")
        print("   1. Submit forms with emails like: test.automated.hot.{timestamp}@example.com")
        print("   2. Run this script again to find and validate them")
        print("\n   Or provide emails directly:")
        print("   python validate_typeform_submissions.py --hot <email> --warm <email> --cold <email>")
        return {}
    
    print(f"\n{'='*70}")
    print("🔍 VALIDATING ALL SUBMISSIONS")
    print(f"{'='*70}\n")
    
    results = {}
    
    for scenario in ["hot", "warm", "cold"]:
        email = test_emails.get(scenario)
        if email:
            validation = await validate_scenario(scenario, email)
            results[scenario] = {
                "email": email,
                "validation": validation
            }
            
            if scenario != "cold":
                print("\n⏳ Waiting 3 seconds...\n")
                await asyncio.sleep(3)
        else:
            print(f"\n⚠️  Skipping {scenario.upper()} - no email found")
    
    return results


def print_summary(results: Dict[str, Any]):
    """Print validation summary."""
    if not results:
        return
    
    print(f"\n{'='*70}")
    print("📊 VALIDATION SUMMARY")
    print(f"{'='*70}\n")
    
    for scenario, data in results.items():
        validation = data.get("validation", {})
        email = data.get("email", "N/A")
        
        if "error" in validation:
            status = "⚠️  SKIPPED"
        elif validation.get("lead_saved") and validation.get("qualification_complete"):
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        
        print(f"{scenario.upper():<8} {status}")
        print(f"  Email: {email}")
        if validation.get("tier"):
            print(f"  Tier: {validation.get('tier')}, Score: {validation.get('score', 'N/A')}")
        if validation.get("errors"):
            for error in validation["errors"]:
                print(f"  ⚠️  {error}")
        print()
    
    passed = sum(
        1 for r in results.values()
        if r.get("validation", {}).get("lead_saved") and 
           r.get("validation", {}).get("qualification_complete")
    )
    total = len(results)
    
    print(f"{'='*70}")
    print(f"Results: {passed}/{total} scenarios passed")
    print(f"{'='*70}\n")


async def main():
    """Main execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate Typeform submissions")
    parser.add_argument("--hot", help="Email for HOT scenario")
    parser.add_argument("--warm", help="Email for WARM scenario")
    parser.add_argument("--cold", help="Email for COLD scenario")
    parser.add_argument("--find", action="store_true", help="Find recent test submissions in database")
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("🧪 TYPEFORM SUBMISSION VALIDATION")
    print("="*70)
    
    test_emails = {}
    
    if args.hot or args.warm or args.cold:
        if args.hot:
            test_emails["hot"] = args.hot
        if args.warm:
            test_emails["warm"] = args.warm
        if args.cold:
            test_emails["cold"] = args.cold
    elif args.find:
        # Will search in validate_all_scenarios
        test_emails = None
    else:
        # Default: try to find recent submissions
        test_emails = None
    
    results = await validate_all_scenarios(test_emails)
    
    if results:
        print_summary(results)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

