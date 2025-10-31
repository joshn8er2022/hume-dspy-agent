"""
Mock Lead Data for Testing

Provides realistic sample lead data representing different:
- Tiers (HOT, WARM, COOL, COLD, UNKNOWN)
- Sources (typeform, vapi, slack)
- Industries (healthcare, wellness, fitness)
- Patient volumes (small to large)

Used for testing pipeline analysis and recommendation logic without
requiring actual database queries.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any


# Sample lead data with various tiers and characteristics
MOCK_LEADS_DIVERSE = [
    # HOT LEADS - High quality, ready to buy
    {
        "id": "lead_001",
        "email": "dr.johnson@healthyliveclinic.com",
        "company": "Healthy Live Wellness Clinic",
        "tier": "HOT",
        "source": "typeform",
        "created_at": (datetime.now() - timedelta(hours=2)).isoformat(),
        "industry": "healthcare",
        "patient_volume": 250,
        "use_case": "Body composition tracking for metabolic health program",
        "qualification_score": 92
    },
    {
        "id": "lead_002",
        "email": "sarah@optimumwellness.com",
        "company": "Optimum Wellness Center",
        "tier": "HOT",
        "source": "typeform",
        "created_at": (datetime.now() - timedelta(hours=5)).isoformat(),
        "industry": "wellness",
        "patient_volume": 180,
        "use_case": "Weight loss clinic needs accurate body composition",
        "qualification_score": 88
    },
    {
        "id": "lead_003",
        "email": "mike@vitalitymedical.com",
        "company": "Vitality Medical Group",
        "tier": "SCORCHING",
        "source": "vapi",
        "created_at": (datetime.now() - timedelta(hours=1)).isoformat(),
        "industry": "healthcare",
        "patient_volume": 500,
        "use_case": "Large telehealth practice, urgent need for body comp",
        "qualification_score": 97
    },

    # WARM LEADS - Interested but need nurturing
    {
        "id": "lead_004",
        "email": "info@zenfitnessclub.com",
        "company": "Zen Fitness Club",
        "tier": "WARM",
        "source": "typeform",
        "created_at": (datetime.now() - timedelta(hours=12)).isoformat(),
        "industry": "fitness",
        "patient_volume": 120,
        "use_case": "Fitness center looking at body composition options",
        "qualification_score": 72
    },
    {
        "id": "lead_005",
        "email": "contact@renewhealth.com",
        "company": "Renew Health Clinic",
        "tier": "WARM",
        "source": "typeform",
        "created_at": (datetime.now() - timedelta(hours=18)).isoformat(),
        "industry": "wellness",
        "patient_volume": 90,
        "use_case": "Considering adding body comp to services",
        "qualification_score": 68
    },

    # COOL LEADS - Some interest, lower priority
    {
        "id": "lead_006",
        "email": "admin@localphysio.com",
        "company": "Local Physiotherapy Center",
        "tier": "COOL",
        "source": "typeform",
        "created_at": (datetime.now() - timedelta(days=1)).isoformat(),
        "industry": "healthcare",
        "patient_volume": 45,
        "use_case": "Small practice, just researching",
        "qualification_score": 55
    },
    {
        "id": "lead_007",
        "email": "hello@gymstudio.com",
        "company": "Personal Training Studio",
        "tier": "COOL",
        "source": "slack",
        "created_at": (datetime.now() - timedelta(days=2)).isoformat(),
        "industry": "fitness",
        "patient_volume": 30,
        "use_case": "Personal trainer wants body comp for clients",
        "qualification_score": 48
    },

    # COLD LEADS - Low quality or poor fit
    {
        "id": "lead_008",
        "email": "student@university.edu",
        "company": "University Student",
        "tier": "COLD",
        "source": "typeform",
        "created_at": (datetime.now() - timedelta(days=3)).isoformat(),
        "industry": "education",
        "patient_volume": 0,
        "use_case": "Research project, no budget",
        "qualification_score": 22
    },
    {
        "id": "lead_009",
        "email": "personal@email.com",
        "company": "",
        "tier": "COLD",
        "source": "typeform",
        "created_at": (datetime.now() - timedelta(days=4)).isoformat(),
        "industry": "unknown",
        "patient_volume": 1,
        "use_case": "Personal use only",
        "qualification_score": 15
    },

    # UNKNOWN TIER - Not yet qualified
    {
        "id": "lead_010",
        "email": "inquiry@newclinic.com",
        "company": "New Wellness Clinic",
        "tier": "UNKNOWN",
        "source": "typeform",
        "created_at": (datetime.now() - timedelta(minutes=30)).isoformat(),
        "industry": "wellness",
        "patient_volume": 0,
        "use_case": "Just submitted, not qualified yet",
        "qualification_score": 0
    }
]


# Sample lead data focused on healthcare segment (for segment-specific tests)
MOCK_LEADS_HEALTHCARE = [
    {
        "id": "hc_001",
        "email": "dr.martinez@cardioclinic.com",
        "company": "Advanced Cardiology Clinic",
        "tier": "HOT",
        "source": "typeform",
        "created_at": (datetime.now() - timedelta(hours=3)).isoformat(),
        "industry": "healthcare",
        "specialty": "cardiology",
        "patient_volume": 300,
        "use_case": "Cardiac rehab program needs body composition",
        "qualification_score": 90
    },
    {
        "id": "hc_002",
        "email": "admin@endocrinecenter.com",
        "company": "Metabolic & Endocrine Center",
        "tier": "HOT",
        "source": "vapi",
        "created_at": (datetime.now() - timedelta(hours=6)).isoformat(),
        "industry": "healthcare",
        "specialty": "endocrinology",
        "patient_volume": 220,
        "use_case": "Diabetes and metabolic health tracking",
        "qualification_score": 85
    },
    {
        "id": "hc_003",
        "email": "contact@familymed.com",
        "company": "Family Medicine Practice",
        "tier": "WARM",
        "source": "typeform",
        "created_at": (datetime.now() - timedelta(hours=10)).isoformat(),
        "industry": "healthcare",
        "specialty": "family_medicine",
        "patient_volume": 150,
        "use_case": "Primary care with wellness focus",
        "qualification_score": 70
    }
]


# Sample lead data for testing empty/sparse data scenarios
MOCK_LEADS_MINIMAL = [
    {
        "id": "min_001",
        "email": "test@example.com",
        "company": "Single Test Lead",
        "tier": "WARM",
        "source": "typeform",
        "created_at": datetime.now().isoformat(),
        "industry": "other",
        "patient_volume": 50,
        "use_case": "Testing",
        "qualification_score": 60
    }
]


# Empty dataset for testing zero-lead scenarios
MOCK_LEADS_EMPTY: List[Dict[str, Any]] = []


# Helper function to get leads by tier
def get_leads_by_tier(tier: str, dataset: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Get all leads of a specific tier.

    Args:
        tier: Tier to filter by (HOT, WARM, COOL, COLD, SCORCHING, UNKNOWN)
        dataset: Dataset to filter (defaults to MOCK_LEADS_DIVERSE)

    Returns:
        List of leads matching the tier
    """
    if dataset is None:
        dataset = MOCK_LEADS_DIVERSE
    return [lead for lead in dataset if lead.get('tier') == tier]


# Helper function to get leads by source
def get_leads_by_source(source: str, dataset: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Get all leads from a specific source.

    Args:
        source: Source to filter by (typeform, vapi, slack)
        dataset: Dataset to filter (defaults to MOCK_LEADS_DIVERSE)

    Returns:
        List of leads from that source
    """
    if dataset is None:
        dataset = MOCK_LEADS_DIVERSE
    return [lead for lead in dataset if lead.get('source') == source]


# Helper function to get leads by industry
def get_leads_by_industry(industry: str, dataset: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Get all leads in a specific industry.

    Args:
        industry: Industry to filter by
        dataset: Dataset to filter (defaults to MOCK_LEADS_DIVERSE)

    Returns:
        List of leads in that industry
    """
    if dataset is None:
        dataset = MOCK_LEADS_DIVERSE
    return [lead for lead in dataset if lead.get('industry') == industry]


# Helper to generate realistic time-series lead data
def generate_time_series_leads(days: int = 7, leads_per_day: int = 5) -> List[Dict[str, Any]]:
    """
    Generate time-series lead data for testing trends.

    Args:
        days: Number of days to generate
        leads_per_day: Average leads per day

    Returns:
        List of leads distributed over time period
    """
    leads = []
    tiers = ["HOT", "WARM", "COOL", "COLD"]
    sources = ["typeform", "vapi", "slack"]
    industries = ["healthcare", "wellness", "fitness"]

    for day in range(days):
        for i in range(leads_per_day):
            lead_time = datetime.now() - timedelta(days=day, hours=i*2)
            tier = tiers[i % len(tiers)]

            leads.append({
                "id": f"ts_{day}_{i}",
                "email": f"lead{day}{i}@company{day}.com",
                "company": f"Company {day}-{i}",
                "tier": tier,
                "source": sources[i % len(sources)],
                "created_at": lead_time.isoformat(),
                "industry": industries[i % len(industries)],
                "patient_volume": 50 + (i * 30),
                "use_case": f"Day {day} lead {i}",
                "qualification_score": 50 + (i * 10)
            })

    return leads


# Pattern-heavy dataset for recommendation testing
MOCK_LEADS_WITH_PATTERNS = [
    # Pattern 1: Healthcare clinics with 200+ patients = HIGH SUCCESS
    {"id": "p1", "tier": "HOT", "industry": "healthcare", "patient_volume": 250, "source": "typeform"},
    {"id": "p2", "tier": "HOT", "industry": "healthcare", "patient_volume": 220, "source": "typeform"},
    {"id": "p3", "tier": "HOT", "industry": "healthcare", "patient_volume": 300, "source": "vapi"},

    # Pattern 2: Small fitness studios = LOW SUCCESS
    {"id": "p4", "tier": "COLD", "industry": "fitness", "patient_volume": 30, "source": "typeform"},
    {"id": "p5", "tier": "COLD", "industry": "fitness", "patient_volume": 40, "source": "slack"},

    # Pattern 3: Wellness clinics 100-200 patients = MEDIUM SUCCESS
    {"id": "p6", "tier": "WARM", "industry": "wellness", "patient_volume": 120, "source": "typeform"},
    {"id": "p7", "tier": "WARM", "industry": "wellness", "patient_volume": 150, "source": "typeform"},
    {"id": "p8", "tier": "WARM", "industry": "wellness", "patient_volume": 180, "source": "vapi"},
]


# Export all datasets
__all__ = [
    'MOCK_LEADS_DIVERSE',
    'MOCK_LEADS_HEALTHCARE',
    'MOCK_LEADS_MINIMAL',
    'MOCK_LEADS_EMPTY',
    'MOCK_LEADS_WITH_PATTERNS',
    'get_leads_by_tier',
    'get_leads_by_source',
    'get_leads_by_industry',
    'generate_time_series_leads',
]
