"""DSPy-based Inbound Lead Qualification Agent."""
import dspy
from typing import Optional, List, Dict, Any
from datetime import datetime
import time

from models import (
    Lead,
    QualificationResult,
    QualificationCriteria,
    LeadTier,
    NextAction,
    LeadStatus,
)
from dspy_modules import (
    QualifyLead,
    AnalyzeBusinessFit,
    AnalyzeEngagement,
    DetermineNextActions,
    GenerateEmailTemplate,
    GenerateSMSMessage,
)
from core import settings
from core.company_context import get_company_context_for_qualification


class InboundAgent(dspy.Module):
    """Intelligent inbound lead qualification agent using DSPy.

    This agent analyzes incoming leads from Typeform submissions,
    qualifies them based on business fit and engagement signals,
    and recommends personalized next actions.
    """

    def __init__(self):
        super().__init__()

        # Initialize DSPy modules
        self.analyze_business = dspy.ChainOfThought(AnalyzeBusinessFit)
        self.analyze_engagement = dspy.ChainOfThought(AnalyzeEngagement)
        self.determine_actions = dspy.ChainOfThought(DetermineNextActions)
        self.generate_email = dspy.ChainOfThought(GenerateEmailTemplate)
        self.generate_sms = dspy.ChainOfThought(GenerateSMSMessage)

        # Qualification thresholds (6-tier granular system)
        self.SCORCHING_THRESHOLD = 90
        self.HOT_THRESHOLD = 75
        self.WARM_THRESHOLD = 60
        self.COOL_THRESHOLD = 45
        self.COLD_THRESHOLD = 30

    def forward(self, lead: Lead) -> QualificationResult:
        """Process and qualify a lead.

        Args:
            lead: Lead object to qualify

        Returns:
            QualificationResult with score, reasoning, and next actions
        """
        start_time = time.time()

        # COMPATIBILITY FIX: Extract semantic fields from old Typeform field IDs
        # Old database records have raw field IDs, new ones have semantic names
        semantic_data = lead.extract_semantic_fields()
        if semantic_data:
            # Enrich lead with extracted semantic data for qualification
            lead._semantic_enrichment = semantic_data

        # Step 1: Analyze business fit
        business_fit = self._analyze_business_fit(lead)

        # Step 2: Analyze engagement
        engagement = self._analyze_engagement(lead)

        # Step 3: Calculate total score and criteria
        criteria = self._calculate_criteria(lead, business_fit, engagement)
        total_score = criteria.calculate_total()

        # Step 4: Determine tier and qualification status
        tier = self._determine_tier(total_score)
        is_qualified = total_score >= self.COLD_THRESHOLD

        # Step 5: Determine next actions
        actions_result = self.determine_actions(
            qualification_score=total_score,
            tier=tier.value,
            has_booking=lead.has_field('calendly_url'),
            response_complete=lead.is_complete(),
        )

        # Step 6: Generate personalized templates if qualified
        email_template = None
        sms_template = None

        if is_qualified and lead.is_complete():
            email_result = self.generate_email(
                company_context=get_company_context_for_qualification(),
                lead_name=(lead.get_field('first_name', '') + ' ' + lead.get_field('last_name', '')).strip() or 'there',
                company=lead.get_field('company') or "your practice",
                business_size=lead.get_field('business_size') if lead.get_field('business_size') else "small business",
                patient_volume=lead.get_field('patient_volume') if lead.get_field('patient_volume') else "1-50 patients",
                needs_summary=lead.get_field('ai_summary') or "body composition tracking",
                tier=tier.value,
            )
            email_template = f"""Subject: {email_result.email_subject}

{email_result.email_body}"""

            sms_result = self.generate_sms(
                lead_name=lead.get_field('first_name'),
                tier=tier.value,
                has_booking=lead.has_field('calendly_url'),
            )
            sms_template = sms_result.sms_message

        # Step 7: Compile reasoning
        reasoning = self._compile_reasoning(
            lead, business_fit, engagement, total_score, tier
        )

        # Step 8: Extract key factors and concerns
        key_factors = self._extract_key_factors(lead, business_fit, engagement)
        concerns = self._extract_concerns(lead, business_fit, engagement)

        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)

        # Create qualification result
        result = QualificationResult(
            is_qualified=is_qualified,
            score=total_score,
            tier=tier,
            reasoning=reasoning,
            key_factors=key_factors,
            concerns=concerns,
            criteria=criteria,
            next_actions=actions_result.next_actions,
            priority=actions_result.priority,
            suggested_email_template=email_template,
            suggested_sms_message=sms_template,
            agent_version="1.0.0",
            model_used=settings.dspy_model,
            processing_time_ms=processing_time,
        )

        return result

    def _analyze_business_fit(self, lead: Lead) -> Dict[str, Any]:
        """Analyze business fit using DSPy."""
        # Use semantic enrichment if available (for old database records)
        semantic = getattr(lead, '_semantic_enrichment', {})

        # Build context string from use case / business goals
        use_case = semantic.get('use_case') or lead.get_field('use_case') or lead.get_field('business_goals') or "No use case provided"

        # Get patient volume
        if 'patient_volume_raw' in semantic:
            patient_volume = f"{semantic['patient_volume_raw']} patients/members ({semantic.get('patient_volume_category', 'unknown')} volume)"
        else:
            patient_volume = lead.get_field('patient_volume') or "Unknown"

        result = self.analyze_business(
            company_context=get_company_context_for_qualification(),
            business_size=lead.get_field('business_size') or semantic.get('business_size') or "Unknown - see use case",
            patient_volume=patient_volume,
            company=semantic.get('company') or lead.get_field('company') or "Unknown",
            industry="Healthcare",
        )
        return {
            "score": result.fit_score,
            "reasoning": result.reasoning,
            "use_case_context": use_case[:200],  # Pass context for debugging
        }

    def _analyze_engagement(self, lead: Lead) -> Dict[str, Any]:
        """Analyze engagement using DSPy."""
        # Use semantic enrichment if available
        semantic = getattr(lead, '_semantic_enrichment', {})

        # Check for Calendly in semantic data or regular fields
        has_calendly = semantic.get('has_calendly', False) or lead.has_field('calendly_url')

        result = self.analyze_engagement(
            company_context=get_company_context_for_qualification(),
            response_type=lead.response_type,
            has_calendly_booking=has_calendly,
            body_comp_response=lead.get_field('body_comp_tracking') or semantic.get('use_case', '')[:100] or "No response provided",
            ai_summary=lead.get_field('ai_summary') or semantic.get('use_case', '')[:200] or "No summary available",
        )
        return {
            "score": result.engagement_score,
            "intent_level": result.intent_level,
            "reasoning": result.reasoning,
        }

    def _calculate_criteria(self, lead: Lead, business_fit: Dict, engagement: Dict) -> QualificationCriteria:
        """Calculate detailed qualification criteria using LLM reasoning.

        This method uses the LLM's analysis from business_fit and engagement
        to derive scores, eliminating hard-coded rules. The LLM already has
        full Hume Health context and ICP understanding from the DSPy signatures.
        """
        # Use LLM's business fit score directly (already 0-50 from DSPy)
        # Split it across business_size and patient_volume based on reasoning
        business_fit_score = business_fit["score"]

        # Allocate business fit score (0-50) into components:
        # - Patient volume gets 60% weight (most important for Hume Health)
        # - Business size gets 40% weight
        patient_volume_score = int(business_fit_score * 0.6 * 0.4)  # Max 20
        business_size_score = int(business_fit_score * 0.4 * 0.5)  # Max 20
        industry_fit_score = min(15, int(business_fit_score * 0.3))  # Max 15

        # Use LLM's engagement score directly (already 0-50 from DSPy)
        engagement_score = engagement["score"]

        # Response completeness: weight based on completion AND LLM's assessment
        if lead.is_complete():
            response_completeness_score = min(15, int(engagement_score * 0.3))
        else:
            # Partial submissions can still score if LLM sees strong signals
            response_completeness_score = min(10, int(engagement_score * 0.2))

        # Calendly booking: highest intent signal
        # But don't just give flat 10 - let LLM determine value
        if lead.has_field('calendly_url'):
            calendly_booking_score = 10
        else:
            # No booking, but strong engagement can still score here
            calendly_booking_score = min(5, int(engagement_score * 0.1))

        # Response quality: use LLM's engagement analysis
        response_quality_score = min(10, int(engagement_score * 0.2))

        # Company data: enrichment disabled, so use LLM's context awareness
        # If LLM mentions company in reasoning, it's doing implicit research
        company_data_score = 0  # Keep at 0 for now (no enrichment)

        return QualificationCriteria(
            business_size_score=business_size_score,
            patient_volume_score=patient_volume_score,
            industry_fit_score=industry_fit_score,
            response_completeness_score=response_completeness_score,
            calendly_booking_score=calendly_booking_score,
            response_quality_score=response_quality_score,
            company_data_score=company_data_score,
        )

    def _determine_tier(self, score: int) -> LeadTier:
        """Determine qualification tier from score using 6-tier granular system."""
        if score >= self.SCORCHING_THRESHOLD:
            return LeadTier.SCORCHING
        elif score >= self.HOT_THRESHOLD:
            return LeadTier.HOT
        elif score >= self.WARM_THRESHOLD:
            return LeadTier.WARM
        elif score >= self.COOL_THRESHOLD:
            return LeadTier.COOL
        elif score >= self.COLD_THRESHOLD:
            return LeadTier.COLD
        else:
            return LeadTier.UNQUALIFIED

    def _compile_reasoning(self, lead: Lead, business_fit: Dict, engagement: Dict, score: int, tier: LeadTier) -> str:
        """Compile comprehensive reasoning for qualification."""
        reasoning_parts = [
            f"Lead scored {score}/100, qualifying as {tier.value.upper()}.",
            "",
            "Business Fit Analysis:",
            business_fit["reasoning"],
            "",
            "Engagement Analysis:",
            engagement["reasoning"],
        ]

        if lead.has_field('calendly_url'):
            reasoning_parts.append("\n✅ Lead has scheduled a Calendly call - high intent signal.")

        if lead.is_complete():
            reasoning_parts.append("✅ Complete Typeform submission - strong engagement.")
        else:
            reasoning_parts.append("⚠️ Partial submission - may need nurturing.")

        return "\n".join(reasoning_parts)

    def _extract_key_factors(self, lead: Lead, business_fit: Dict, engagement: Dict) -> List[str]:
        """Extract key positive factors."""
        factors = []

        if lead.has_field('calendly_url'):
            factors.append("Calendly call scheduled")

        if lead.is_complete():
            factors.append("Complete Typeform response")

        if lead.get_field('business_size') and "Large" in lead.get_field('business_size'):
            factors.append("Large business (20+ employees)")

        if lead.get_field('patient_volume') and "300+" in lead.get_field('patient_volume'):
            factors.append("High patient volume (300+)")

        if engagement["intent_level"] == "high":
            factors.append("High purchase intent")

        # Revenue check removed - enrichment not available in form-agnostic model
        # if lead.enrichment and lead.enrichment.company_revenue_numeric and lead.enrichment.company_revenue_numeric > 1000000:
        #     factors.append("Revenue > $1M")

        return factors

    def _extract_concerns(self, lead: Lead, business_fit: Dict, engagement: Dict) -> List[str]:
        """Extract potential concerns."""
        concerns = []

        if not lead.is_complete():
            concerns.append("Partial Typeform submission")

        if not lead.has_field('calendly_url'):
            concerns.append("No Calendly booking yet")

        if not lead.phone:
            concerns.append("No phone number provided")

        if engagement["intent_level"] == "low":
            concerns.append("Low engagement signals")

        if lead.get_field('business_size') and "Small" in lead.get_field('business_size'):
            concerns.append("Small business (may have budget constraints)")

        return concerns
