"""AI-Driven Tier Determination using DSPy.

Replaces hardcoded tier thresholds with context-aware AI classification.
Expected improvement: 15%+ conversion rate increase.
"""

import dspy
from typing import Optional
from models.lead import LeadTier
import logging

logger = logging.getLogger(__name__)


class ContextualTierDetermination(dspy.Signature):
    """Determine lead tier based on holistic context, not just score.

    Consider:
    - Qualification score (baseline indicator)
    - Engagement signals (Calendly booking = strong intent, complete submission = engaged)
    - Lead context (large practice + healthcare = better fit than small + retail)
    - Industry norms (telehealth boom = higher priority for remote monitoring)

    Do not rely solely on score thresholds. A score of 89 with Calendly booking might be SCORCHING,
    while a score of 91 with no engagement might be just HOT.

    Identify hidden gems - leads with lower scores but high intent signals.

    Tier Definitions:
    - SCORCHING (90-100): Book meeting immediately, highest priority
    - HOT (75-89): High priority follow-up, same-day outreach
    - WARM (60-74): Standard nurture sequence, 24-48h follow-up
    - COOL (45-59): Long-term nurture, weekly touchpoints
    - COLD (30-44): Low priority drip campaign, monthly check-ins
    - UNQUALIFIED (<30): No active outreach, passive content only
    """

    qualification_score: int = dspy.InputField(desc="Overall qualification score (0-100)")
    engagement_signals: str = dspy.InputField(desc="Calendly booking, response quality, completion status")
    lead_context: str = dspy.InputField(desc="Company, industry, patient volume, business size, pain points")
    similar_lead_outcomes: str = dspy.InputField(desc="How similar leads converted (optional)", default="")

    tier: str = dspy.OutputField(desc="SCORCHING, HOT, WARM, COOL, COLD, or UNQUALIFIED")
    confidence: float = dspy.OutputField(desc="Confidence in tier assignment (0.0-1.0)")
    reasoning: str = dspy.OutputField(desc="Why this tier? What signals matter most? Be specific and conversational.")


class AITierClassifier(dspy.Module):
    """AI-driven tier classifier using DSPy ChainOfThought."""

    def __init__(self):
        super().__init__()
        self.classifier = dspy.ChainOfThought(ContextualTierDetermination)

    def forward(self, lead, qualification_score: int, engagement_data: dict):
        """Classify lead tier using AI.

        Args:
            lead: Lead object with all context
            qualification_score: Overall qualification score (0-100)
            engagement_data: Dict with engagement analysis

        Returns:
            DSPy result with tier, confidence, reasoning
        """
        # Build engagement signals string
        engagement_signals = self._build_engagement_signals(lead, engagement_data)

        # Build lead context string
        lead_context = self._build_lead_context(lead)

        # Get similar lead outcomes (TODO: implement historical lookup)
        similar_outcomes = self._get_similar_lead_outcomes(lead)

        # Call AI classifier
        result = self.classifier(
            qualification_score=qualification_score,
            engagement_signals=engagement_signals,
            lead_context=lead_context,
            similar_lead_outcomes=similar_outcomes
        )

        logger.info(f"AI Tier Classification:")
        logger.info(f"   Score: {qualification_score}")
        logger.info(f"   AI Tier: {result.tier}")
        logger.info(f"   Confidence: {result.confidence:.2f}")
        logger.info(f"   Reasoning: {result.reasoning[:100]}...")

        return result

    def _build_engagement_signals(self, lead, engagement_data: dict) -> str:
        """Build engagement signals string for AI."""
        signals = []

        # Calendly booking (strongest signal)
        if lead.has_field('calendly_url'):
            signals.append("Calendly call scheduled (STRONG intent signal)")
        else:
            signals.append("No Calendly booking")

        # Form completion
        if lead.is_complete():
            signals.append("Complete form submission (engaged)")
        else:
            signals.append("Partial submission (may need nurturing)")

        # Response quality
        response_quality = engagement_data.get('response_quality', 0)
        if response_quality >= 8:
            signals.append(f"High-quality responses (score: {response_quality}/10)")
        elif response_quality >= 5:
            signals.append(f"Medium-quality responses (score: {response_quality}/10)")
        else:
            signals.append(f"Low-quality responses (score: {response_quality}/10)")

        # Engagement score
        engagement_score = engagement_data.get('score', 0)
        signals.append(f"Overall engagement: {engagement_score}/50")

        return ", ".join(signals)

    def _build_lead_context(self, lead) -> str:
        """Build lead context string for AI."""
        context_parts = []

        # Company
        company = lead.get_field('company') or lead.company or "Unknown"
        context_parts.append(f"Company: {company}")

        # Industry
        industry = lead.get_field('industry', 'Healthcare')
        context_parts.append(f"Industry: {industry}")

        # Business size
        business_size = lead.get_field('business_size', 'Unknown')
        context_parts.append(f"Business Size: {business_size}")

        # Patient volume (critical for Hume Health)
        patient_volume = lead.get_field('patient_volume', 'Unknown')
        context_parts.append(f"Patient Volume: {patient_volume}")

        # Pain points / use case
        use_case = lead.get_field('use_case') or lead.get_field('business_description')
        if use_case:
            use_case_preview = use_case[:200] + "..." if len(use_case) > 200 else use_case
            context_parts.append(f"Use Case: {use_case_preview}")

        # Contact info quality
        if lead.email and lead.phone:
            context_parts.append("Contact: Email + Phone (complete)")
        elif lead.email:
            context_parts.append("Contact: Email only")
        elif lead.phone:
            context_parts.append("Contact: Phone only")

        return ", ".join(context_parts)

    def _get_similar_lead_outcomes(self, lead) -> str:
        """Get outcomes of similar leads (TODO: implement with Supabase query).

        For now, returns empty string. In production, this should:
        1. Query Supabase for leads with similar:
           - Patient volume range
           - Business size
           - Industry
        2. Return conversion outcomes:
           - How many converted?
           - What tiers were they assigned?
           - What was their engagement pattern?
        """
        # TODO: Implement historical lookup
        return ""
