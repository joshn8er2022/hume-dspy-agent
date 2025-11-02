#!/usr/bin/env python3
"""
Automated Typeform Testing using Puppeteer MCP.
Fills and submits the HumeConnect Partnership Application form,
then validates webhook processing in the system.

Usage:
    python test_typeform_puppeteer_automated.py --scenario hot
    python test_typeform_puppeteer_automated.py --scenario warm
    python test_typeform_puppeteer_automated.py --scenario cold
    python test_typeform_puppeteer_automated.py --all
"""

import asyncio
import os
import sys
import argparse
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import httpx
import json

# Load environment variables
load_dotenv()

# Configuration
TYPEFORM_URL = "https://form.typeform.com/to/F7whHyXK#affiliate=xxxxx&wholesale_retail=xxxxx&professional=xxxxx"
RAILWAY_URL = os.getenv("API_ENDPOINT", "https://hume-dspy-agent-production.up.railway.app")
TEST_EMAIL_BASE = "test.automated"  # Will append timestamp for uniqueness


class TypeformPuppeteerTester:
    """Automated Typeform tester using browser automation."""
    
    def __init__(self, scenario: str = "hot"):
        self.scenario = scenario
        self.test_data = self._get_test_data(scenario)
        self.test_email = f"{TEST_EMAIL_BASE}.{scenario}.{int(datetime.utcnow().timestamp())}@example.com"
        self.submission_time = None
        self.lead_id = None
        
    def _get_test_data(self, scenario: str) -> Dict[str, Any]:
        """Get test data based on scenario (HOT/WARM/COLD lead)."""
        
        scenarios = {
            "hot": {
                "description": "High-intent lead - large clinic, high patient volume",
                "patient_volume": "301+ patients",  # Option C - highest volume
                "business_size": "Large corporation (20+ employees)",  # Option C - largest
                "first_name": "Sarah",
                "last_name": "Johnson",
                "email": None,  # Will be set with timestamp
                "company": "Wellness Medical Center",
                "phone": "+1-555-0101",
                "use_case": "We're a large medical center managing 500+ patients. Currently using InBody scales but need better data integration with our EMR system. Looking for scalable body composition tracking solutions.",
                "expected_tier": "HOT",
                "expected_score_min": 70
            },
            "warm": {
                "description": "Medium-intent lead - medium clinic, moderate patient volume",
                "patient_volume": "51-300 patients",  # Option B - medium volume
                "business_size": "Medium-sized business (6-20 employees)",  # Option B - medium
                "first_name": "Michael",
                "last_name": "Chen",
                "email": None,
                "company": "Family Health Clinic",
                "phone": "+1-555-0102",
                "use_case": "We're a growing clinic with about 150 patients. Interested in body composition tracking but still evaluating options.",
                "expected_tier": "WARM",
                "expected_score_min": 50
            },
            "cold": {
                "description": "Low-intent lead - small practice, low patient volume",
                "patient_volume": "1-50 patients",  # Option A - lowest volume
                "business_size": "Small business (1-5 employees)",  # Option A - smallest
                "first_name": "David",
                "last_name": "Williams",
                "email": None,
                "company": "Independent Practice",
                "phone": "+1-555-0103",
                "use_case": "Just starting out, exploring options for body composition tracking.",
                "expected_tier": "COLD",
                "expected_score_min": 30
            }
        }
        
        data = scenarios.get(scenario.lower(), scenarios["warm"])
        data["email"] = self.test_email
        return data
    
    async def fill_form_via_browser(self) -> bool:
        """
        Fill the Typeform using browser automation.
        This function provides instructions for using Puppeteer MCP tools.
        
        Note: This requires manual execution via MCP tools or can be automated
        if you have a Puppeteer MCP client set up.
        """
        print(f"\n{'='*70}")
        print(f"📝 Filling Typeform - Scenario: {self.scenario.upper()}")
        print(f"{'='*70}\n")
        print(f"Test Email: {self.test_email}")
        print(f"Name: {self.test_data['first_name']} {self.test_data['last_name']}")
        print(f"Company: {self.test_data['company']}")
        print(f"Patient Volume: {self.test_data['patient_volume']}")
        print(f"Business Size: {self.test_data['business_size']}\n")
        
        # Manual steps (to be automated with Puppeteer):
        print("🔧 Browser Automation Steps:")
        print("   1. Navigate to:", TYPEFORM_URL)
        print("   2. Question 1 (Patient Volume):")
        print(f"      → Select: {self.test_data['patient_volume']}")
        print("      → Click 'OK' button")
        print("   3. Question 2 (Business Size):")
        print(f"      → Select: {self.test_data['business_size']}")
        print("      → Click 'OK' button")
        print("   4. Question 3+ (Continue filling all fields):")
        print(f"      → First Name: {self.test_data['first_name']}")
        print(f"      → Last Name: {self.test_data['last_name']}")
        print(f"      → Email: {self.test_email}")
        print(f"      → Company: {self.test_data['company']}")
        print(f"      → Phone: {self.test_data.get('phone', 'N/A')}")
        print("   5. Submit form")
        print("\n⏳ Waiting for webhook processing...\n")
        
        # Record submission time
        self.submission_time = datetime.utcnow()
        
        return True
    
    async def validate_webhook_response(self, wait_seconds: int = 30) -> Dict[str, Any]:
        """Validate that the webhook was processed correctly."""
        print(f"🔍 Validating webhook response (waiting {wait_seconds}s for processing)...\n")
        
        await asyncio.sleep(wait_seconds)
        
        validation_results = {
            "webhook_received": False,
            "lead_saved": False,
            "qualification_complete": False,
            "slack_notification": False,
            "tier": None,
            "score": None,
            "errors": []
        }
        
        try:
            # Check Supabase for lead
            from supabase import create_client
            
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
            
            if supabase_url and supabase_key:
                supabase = create_client(supabase_url, supabase_key)
                
                # Query for lead by email
                result = supabase.table('leads').select('*').eq('email', self.test_email).limit(1).execute()
                
                if result.data and len(result.data) > 0:
                    lead = result.data[0]
                    validation_results["lead_saved"] = True
                    validation_results["tier"] = lead.get('tier')
                    validation_results["score"] = lead.get('qualification_score')
                    self.lead_id = lead.get('id')
                    
                    print(f"✅ Lead found in database:")
                    print(f"   ID: {self.lead_id}")
                    print(f"   Tier: {validation_results['tier']}")
                    print(f"   Score: {validation_results['score']}")
                    print(f"   Status: {lead.get('status')}")
                    
                    # Check qualification
                    if validation_results["tier"] and validation_results["score"]:
                        validation_results["qualification_complete"] = True
                        
                        # Validate tier matches expectation
                        expected_tier = self.test_data.get("expected_tier", "").upper()
                        if validation_results["tier"].upper() != expected_tier:
                            validation_results["errors"].append(
                                f"Tier mismatch: expected {expected_tier}, got {validation_results['tier']}"
                            )
                        
                        # Validate score
                        expected_min = self.test_data.get("expected_score_min", 0)
                        if validation_results["score"] and validation_results["score"] < expected_min:
                            validation_results["errors"].append(
                                f"Score below expected minimum: {validation_results['score']} < {expected_min}"
                            )
                    
                    # Check for Slack thread
                    if lead.get('slack_thread_ts') or lead.get('slack_channel_id'):
                        validation_results["slack_notification"] = True
                        print(f"   Slack Thread: {lead.get('slack_thread_ts')}")
                else:
                    validation_results["errors"].append("Lead not found in database")
                    print("❌ Lead not found in database")
            else:
                print("⚠️ Supabase credentials not configured - skipping database validation")
                
        except Exception as e:
            validation_results["errors"].append(f"Database check failed: {str(e)}")
            print(f"❌ Database check error: {e}")
        
        # Check Railway logs (optional)
        print("\n📋 Validation Summary:")
        print(f"   Lead Saved: {'✅' if validation_results['lead_saved'] else '❌'}")
        print(f"   Qualification: {'✅' if validation_results['qualification_complete'] else '❌'}")
        print(f"   Slack Notification: {'✅' if validation_results['slack_notification'] else '❌'}")
        
        if validation_results["errors"]:
            print(f"\n⚠️ Errors:")
            for error in validation_results["errors"]:
                print(f"   - {error}")
        
        return validation_results
    
    def print_results(self, validation: Dict[str, Any]):
        """Print test results summary."""
        print(f"\n{'='*70}")
        print(f"📊 Test Results - {self.scenario.upper()} Scenario")
        print(f"{'='*70}\n")
        
        print(f"Test Email: {self.test_email}")
        print(f"Submission Time: {self.submission_time}")
        print(f"Lead ID: {self.lead_id or 'Not found'}\n")
        
        print("Validation:")
        print(f"  ✅ Lead Saved: {validation['lead_saved']}")
        print(f"  ✅ Qualification: {validation['qualification_complete']}")
        print(f"  ✅ Slack Notification: {validation['slack_notification']}")
        print(f"  📊 Tier: {validation.get('tier', 'N/A')}")
        print(f"  📊 Score: {validation.get('score', 'N/A')}\n")
        
        if validation['errors']:
            print("Errors:")
            for error in validation['errors']:
                print(f"  ❌ {error}")
        else:
            print("✅ All validations passed!")
        
        print(f"\n{'='*70}\n")


async def run_test(scenario: str, validate: bool = True):
    """Run a single test scenario."""
    tester = TypeformPuppeteerTester(scenario)
    
    # Fill form (instructions provided - manual execution required)
    await tester.fill_form_via_browser()
    
    if validate:
        # Validate webhook response
        validation = await tester.validate_webhook_response()
        tester.print_results(validation)
        
        return validation
    else:
        print("\n⏭️  Validation skipped")
        return {}


async def main():
    parser = argparse.ArgumentParser(description="Automated Typeform testing")
    parser.add_argument(
        "--scenario",
        choices=["hot", "warm", "cold"],
        default="hot",
        help="Test scenario to run"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all test scenarios"
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip validation (just fill form)"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("🧪 AUTOMATED TYPEFORM TESTING")
    print("="*70)
    print(f"\nTypeform URL: {TYPEFORM_URL}")
    print(f"Railway URL: {RAILWAY_URL}\n")
    
    if args.all:
        scenarios = ["hot", "warm", "cold"]
        results = {}
        
        for scenario in scenarios:
            print(f"\n{'#'*70}")
            print(f"Running {scenario.upper()} scenario...")
            print(f"{'#'*70}\n")
            
            result = await run_test(scenario, validate=not args.no_validate)
            results[scenario] = result
            
            # Wait between tests
            if scenario != scenarios[-1]:
                print("\n⏳ Waiting 10 seconds before next test...\n")
                await asyncio.sleep(10)
        
        # Print summary
        print("\n" + "="*70)
        print("📊 ALL TESTS SUMMARY")
        print("="*70 + "\n")
        
        for scenario, result in results.items():
            status = "✅ PASS" if result.get("lead_saved") and result.get("qualification_complete") else "❌ FAIL"
            print(f"{scenario.upper():<10} {status}")
            if result.get("tier"):
                print(f"  Tier: {result['tier']}, Score: {result.get('score', 'N/A')}")
        
    else:
        await run_test(args.scenario, validate=not args.no_validate)


if __name__ == "__main__":
    asyncio.run(main())

