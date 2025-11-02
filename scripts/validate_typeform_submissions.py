#!/usr/bin/env python3
"""
Quick validation script for Typeform submissions.
Use this to validate submissions after manual form filling.
"""

import asyncio
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_typeform_puppeteer_automated import TypeformPuppeteerTester


async def validate_scenario(scenario: str, email: str = None):
    """Validate a single scenario."""
    tester = TypeformPuppeteerTester(scenario)
    
    if email:
        tester.test_email = email
    
    print(f"\n{'='*70}")
    print(f"Validating {scenario.upper()} scenario")
    print(f"Email: {tester.test_email}")
    print(f"{'='*70}\n")
    
    validation = await tester.validate_webhook_response(wait_seconds=30)
    tester.print_results(validation)
    
    return validation


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate Typeform submission")
    parser.add_argument(
        "--scenario",
        choices=["hot", "warm", "cold"],
        required=True,
        help="Test scenario"
    )
    parser.add_argument(
        "--email",
        help="Specific test email to validate (optional)"
    )
    
    args = parser.parse_args()
    
    result = asyncio.run(validate_scenario(args.scenario, args.email))
    
    if result.get("lead_saved") and result.get("qualification_complete"):
        print("\n✅ Validation PASSED!")
    else:
        print("\n❌ Validation FAILED - Check errors above")

