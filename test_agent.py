#!/usr/bin/env python3
"""Test script to demonstrate DSPy InboundAgent."""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import Lead, ResponseType, BusinessSize, PatientVolume
from agents import InboundAgent
from core import dspy_manager
import json


def test_hot_lead():
    """Test with a hot lead (complete submission, booking, large business)."""
    print("
" + "="*80)
    print("🔥 Testing HOT Lead")
    print("="*80)

    lead = Lead(
        id="test-hot-001",
        typeform_id="c9v0nmng13rkfcqq0bc9v0nm3fi3cfje",
        first_name="Judith",
        last_name="Chimienti",
        email="chimienti4@aol.com",
        phone="+16097605976",
        company="Fitness Delivered LLC",
        business_size=BusinessSize.MEDIUM,
        patient_volume=PatientVolume.MEDIUM,
        response_type=ResponseType.COMPLETED,
        body_comp_tracking="Currently using Omron handheld monitor. Need more accurate DEXA-like measurements.",
        ai_summary="Lead wants comprehensive body composition data similar to DEXA scan for better patient assessment.",
        calendly_link="https://calendly.com/d/cv27-cth-sdz/hume-connect-call/invitees/a9a30766",
        calendly_booked=True,
    )

    agent = InboundAgent()
    result = agent.forward(lead)

    print(f"
📊 Qualification Score: {result.score}/100")
    print(f"🎯 Tier: {result.tier.value.upper()}")
    print(f"✅ Qualified: {result.is_qualified}")
    print(f"⚡ Priority: {result.priority}/5")
    print(f"
💭 Reasoning:
{result.reasoning}")
    print(f"
🎯 Key Factors:")
    for factor in result.key_factors:
        print(f"  ✓ {factor}")
    print(f"
⚠️  Concerns:")
    for concern in result.concerns:
        print(f"  • {concern}")
    print(f"
📋 Next Actions:")
    for action in result.next_actions:
        print(f"  → {action.value}")

    if result.suggested_email_template:
        print(f"
📧 Suggested Email:
{result.suggested_email_template[:200]}...")

    if result.suggested_sms_message:
        print(f"
📱 Suggested SMS:
{result.suggested_sms_message}")

    print(f"
⏱️  Processing Time: {result.processing_time_ms}ms")
    print(f"🤖 Model: {result.model_used}")


def test_warm_lead():
    """Test with a warm lead (complete submission, no booking)."""
    print("
" + "="*80)
    print("🌡️  Testing WARM Lead")
    print("="*80)

    lead = Lead(
        id="test-warm-001",
        typeform_id="5y8g4irf56aowzj65y839uzx0h65qsq7",
        first_name="Mika",
        last_name="Moore",
        email="mikamoore@thryvewellness.org",
        phone="+19362306821",
        company="Thryve Health and Wellness",
        business_size=BusinessSize.SMALL,
        patient_volume=PatientVolume.SMALL,
        response_type=ResponseType.COMPLETED,
        body_comp_tracking="Starting new telemedicine business focused on weight loss.",
        ai_summary="New telemedicine business interested in body composition tracking for weight loss programs.",
        calendly_link=None,
        calendly_booked=False,
    )

    agent = InboundAgent()
    result = agent.forward(lead)

    print(f"
📊 Qualification Score: {result.score}/100")
    print(f"🎯 Tier: {result.tier.value.upper()}")
    print(f"✅ Qualified: {result.is_qualified}")
    print(f"⚡ Priority: {result.priority}/5")
    print(f"
💭 Reasoning:
{result.reasoning}")


def test_partial_lead():
    """Test with a partial submission (unqualified)."""
    print("
" + "="*80)
    print("❄️  Testing PARTIAL Lead")
    print("="*80)

    lead = Lead(
        id="test-partial-001",
        typeform_id="8wqzmrvkijv7bxagnkw8wqzm91ytrqnr",
        first_name="Bolden",
        last_name="Harris",
        email="DrBolden@TeravistaWellness.com",
        phone="+15122489355",
        company="Teravista Family Wellness, PLLC",
        business_size=BusinessSize.SMALL,
        response_type=ResponseType.PARTIAL,
        partnership_interest="Dropshipping Membership",
        calendly_link=None,
        calendly_booked=False,
    )

    agent = InboundAgent()
    result = agent.forward(lead)

    print(f"
📊 Qualification Score: {result.score}/100")
    print(f"🎯 Tier: {result.tier.value.upper()}")
    print(f"✅ Qualified: {result.is_qualified}")
    print(f"⚡ Priority: {result.priority}/5")
    print(f"
💭 Reasoning:
{result.reasoning}")


if __name__ == "__main__":
    # Initialize DSPy
    print("🚀 Initializing DSPy...")
    dspy_manager.initialize()

    # Run tests
    test_hot_lead()
    test_warm_lead()
    test_partial_lead()

    print("
" + "="*80)
    print("✅ All tests completed!")
    print("="*80)
