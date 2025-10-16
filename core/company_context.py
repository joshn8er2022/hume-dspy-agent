"""Hume Health Company Context for RAG-Enhanced Qualification.

This module provides company-specific context for the lead qualification agent.
Context is injected into DSPy signatures to ensure agents understand Hume Health's
value proposition, ideal customer profile, and competitive positioning.

Based on: Hume Health Comprehensive Report v2.0 (July 2025)
"""

# ==========================
# COMPANY OVERVIEW
# ==========================

COMPANY_NAME = "Hume Health"
ANNUAL_REVENUE = "$72 million"
MONTHLY_ACTIVE_USERS = "650,000"
COMPANY_STAGE = "Established enterprise with strong D2C foundation"

MISSION = """
Democratize personal health data and empower individuals and professionals to achieve
better health outcomes through accessible, clinical-grade insights from home.
"""

# ==========================
# PRODUCTS
# ==========================

BODY_POD_CONTEXT = """
**The Body Pod** (Primary B2B Hardware Product)
- Multi-frequency bioimpedance (BIA) smart scale
- 98% accuracy - Clinical-grade body composition analysis
- Price: $1k-$3k (wholesale/professional tier)
- Key USP: Daily-use model for tracking trends vs. single-point measurements
- Enables practitioners to track patient adherence and understand impact of daily habits
- Portable, convenient alternative to DXA scans (no clinic visit required)
- Integrates with Hume Connect platform for remote monitoring
"""

HUME_CONNECT_CONTEXT = """
**Hume Connect** (Most Powerful B2B Differentiator - SaaS Platform)
- HIPAA-compliant remote patient monitoring (RPM) platform
- Transforms hardware sale into complete business solution for clinics
- Key Benefits for Practitioners:
  * Saves 15+ hours per week on data analysis
  * Improves patient outcomes by 37% (faster results)
  * Creates new revenue streams for practices
  * Automates data collection and analysis
  * AI-powered analytics and patient engagement tools
- Target: Health and wellness professionals, clinics, telehealth practices
- Scalable solution for practices of all sizes
"""

HUME_BAND_CONTEXT = """
**Hume Band** (Wearable Product)
- WHOOP competitor for continuous health tracking
- Tracks: Heart rate, HRV, sleep, recovery
- Integrates into same Hume consumer app ecosystem
- Not primary focus for B2B practitioners (Body Pod + Connect is the core offering)
"""

# ==========================
# IDEAL CUSTOMER PROFILE (ICP) - B2B
# ==========================

ICP_SUMMARY = """
**B2B Ideal Customer Profile:**

This bot serves the B2B department focused on **practitioners and businesses**
using Body Pod for remote patient tracking, NOT direct-to-consumer individuals.

**Three B2B Segments:**
1. **Hume Connect (Professional Clinics)** - Healthcare practitioners who need RPM
2. **Wholesale** - Businesses buying units for corporate wellness, retail resale
3. **Affiliates** - Partners promoting products for commission

**Qualification Focus:**
- We seek QUALIFIED leads with clear use cases
- "Qualified" ≠ "Hot/Warm/Cold" (these are separate dimensions)
- Low-quality practitioners are not inherently bad, but we prioritize firmographics:
  * Patient/client volume
  * Number of units they might purchase
  * Practice size and stability
  * Budget alignment
  * Existing pain points in patient management
"""

TARGET_CUSTOMER_PROFILES = {
    "hume_connect_clinics": {
        "description": "Healthcare practitioners needing remote patient monitoring",
        "examples": [
            "Weight loss clinics",
            "Diabetes management practices",
            "Functional medicine practitioners",
            "Telehealth providers",
            "Wellness coaches",
            "Corporate wellness programs"
        ],
        "key_pain_points": [
            "Manual data collection is time-consuming",
            "Patient adherence is low without daily tracking",
            "No centralized platform for patient data",
            "Inefficient workflow for analyzing patient progress",
            "Want to create new revenue streams"
        ],
        "ideal_size": "1-50+ patients currently, growth potential",
        "decision_criteria": "Workflow efficiency, patient outcomes, ROI"
    },
    "wholesale": {
        "description": "Businesses buying Body Pods for corporate wellness or resale",
        "examples": [
            "Corporate wellness programs (employee incentives)",
            "Retail stores (fitness equipment)",
            "Gym/fitness center chains",
            "Health coaching businesses"
        ],
        "ideal_order_size": "10+ units minimum",
        "decision_criteria": "ROI, bulk pricing, support infrastructure"
    },
    "affiliates": {
        "description": "Partners promoting Hume products for commission",
        "examples": [
            "Health influencers",
            "Wellness bloggers",
            "Fitness coaches with audience",
            "Health tech reviewers"
        ],
        "decision_criteria": "Commission structure, brand alignment, marketing support"
    }
}

# ==========================
# COMPETITIVE POSITIONING
# ==========================

COMPETITIVE_CONTEXT = """
**Main Competitors:**

1. **InBody** - Professional BIA analyzers (270, 570, 770 models)
   - Strengths: Gold-standard reputation, clinical validation, established market
   - Weaknesses: High cost, requires physical location (not portable), no home-use model
   - Hume Advantage: Portable daily-use model vs. clinical visit requirement

2. **Withings** - Consumer BIA scales + RPM platform
   - Strengths: Strong brand recognition, wide device ecosystem
   - Weaknesses: BIA perceived as less accurate than DXA, direct competitor to Hume Connect
   - Hume Advantage: Focus on practitioner workflow efficiency + patient adherence

3. **DXA Scans** - Medical imaging (gold standard accuracy)
   - Strengths: Most accurate method, measures bone density
   - Weaknesses: Inconvenient (clinic visit), expensive per scan, radiation, not continuous
   - Hume Advantage: Daily tracking for trends vs. single-point accuracy

**Hume Health's Unique Position:**
- Combines portable hardware (Body Pod) with practitioner SaaS (Hume Connect)
- Focus on TREND DATA through daily use, not just single-point accuracy
- Solves operational inefficiency for practitioners (15+ hours saved weekly)
- Improves patient adherence through daily engagement
- RPM market is rapidly growing - perfect timing
"""

# ==========================
# VALUE PROPOSITIONS BY SEGMENT
# ==========================

VALUE_PROPS = {
    "hume_connect": {
        "headline": "Transform your practice with automated patient monitoring",
        "key_benefits": [
            "Save 15+ hours per week on data analysis",
            "37% faster patient results",
            "Improve patient adherence with daily check-ins",
            "Create new revenue streams (RPM billing)",
            "HIPAA-compliant, scalable platform",
            "White-glove onboarding for high-value clients"
        ],
        "roi_message": "High-ticket offer ($8k setup) with clear ROI through time savings and revenue generation"
    },
    "wholesale": {
        "headline": "Business-in-a-box solution with robust support",
        "key_benefits": [
            "Bulk pricing discounts",
            "Dropship or bulk fulfillment options",
            "Marketing and sales resources provided",
            "Automated fulfillment infrastructure",
            "Clear economics for resale or employee programs"
        ]
    },
    "affiliate": {
        "headline": "Earn commissions promoting clinical-grade health tech",
        "key_benefits": [
            "MLM-style tiered incentives",
            "Comprehensive marketing resources",
            "Dedicated community support",
            "Training on product positioning"
        ]
    }
}

# ==========================
# QUALIFICATION SCORING CONTEXT
# ==========================

QUALIFICATION_GUIDANCE = """
**How to Qualify B2B Leads:**

**QUALIFIED = Has clear use case + sufficient volume + budget alignment**

Firmographic Signals (HIGH VALUE):
- Patient/client volume: 50+ = strong, 100+ = excellent, 300+ = ideal
- Practice size: 5+ employees = established
- Existing tech stack: Using EMR/CRM = sophisticated
- Budget indicators: Mentions ROI, asks about financing = serious buyer

Engagement Signals (MEDIUM VALUE):
- Complete Typeform submission
- Books Calendly call = high intent
- Asks specific questions about Hume Connect features
- Mentions specific pain points (time-consuming data collection, low adherence)

Disqualifiers (DO NOT PURSUE):
- Individual consumers looking for personal use (wrong segment)
- No clear patient/client base
- Unrealistic expectations ("cure all" mindset)
- Budget concerns without ROI discussion

**Tier Assignment:**
- HOT (80+): Large practice (100+ patients), clear pain point, budget confirmed, ready to buy
- WARM (60-79): Medium practice (50-100 patients), identified pain, needs nurturing
- COLD (40-59): Small practice (10-50 patients) or needs education, longer sales cycle
- UNQUALIFIED (<40): Missing key firmographics, wrong fit, or unclear use case
"""

# ==========================
# TONE & MESSAGING GUIDELINES
# ==========================

TONE_GUIDELINES = """
**Communication Style:**

AVOID:
- Overly AI-like, robotic language
- Generic corporate speak
- Feature-dumping without context
- Pushy sales tactics

USE:
- Conversational, human tone
- Consultant/advisor approach (not salesperson)
- Focus on PROBLEMS SOLVED, not features
- Practitioner-specific language (workflow, patient adherence, ROI)
- Peer-to-peer communication (we understand your pain)

Example BAD: "Our platform provides comprehensive analytics capabilities."
Example GOOD: "You'll save 15+ hours weekly - no more manually analyzing patient data."
"""

def get_company_context_for_qualification() -> str:
    """
    Get formatted company context for injection into DSPy signatures.
    Used by qualification agent to understand Hume Health ICP.
    """
    return f"""
# HUME HEALTH COMPANY CONTEXT

{COMPANY_NAME} - {COMPANY_STAGE}
Revenue: {ANNUAL_REVENUE} | MAU: {MONTHLY_ACTIVE_USERS}

## MISSION
{MISSION.strip()}

## PRODUCTS
{BODY_POD_CONTEXT.strip()}

{HUME_CONNECT_CONTEXT.strip()}

## B2B IDEAL CUSTOMER
{ICP_SUMMARY.strip()}

## COMPETITIVE POSITION
{COMPETITIVE_CONTEXT.strip()}

## QUALIFICATION APPROACH
{QUALIFICATION_GUIDANCE.strip()}

## TONE
{TONE_GUIDELINES.strip()}
"""

# Export for easy imports
__all__ = [
    'COMPANY_NAME',
    'BODY_POD_CONTEXT',
    'HUME_CONNECT_CONTEXT',
    'ICP_SUMMARY',
    'COMPETITIVE_CONTEXT',
    'QUALIFICATION_GUIDANCE',
    'TONE_GUIDELINES',
    'VALUE_PROPS',
    'TARGET_CUSTOMER_PROFILES',
    'get_company_context_for_qualification'
]
