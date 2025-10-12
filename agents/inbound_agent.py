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

        # Qualification thresholds
        self.HOT_THRESHOLD = 80
        self.WARM_THRESHOLD = 60
        self.COLD_THRESHOLD = 40

    def forward(self, lead: Lead) -> QualificationResult:
        """Process and qualify a lead.

        Args:
            lead: Lead object to qualify

        Returns:
            QualificationResult with score, reasoning, and next actions
        """
        start_time = time.time()

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
            has_booking=lead.has_booking(),
            response_complete=lead.is_complete_submission(),
        )

        # Step 6: Generate personalized templates if qualified
        email_template = None
        sms_template = None

        if is_qualified and lead.is_complete_submission():
            email_result = self.generate_email(
                lead_name=lead.get_full_name(),
                company=lead.company or "your practice",
                business_size=lead.business_size.value if lead.business_size else "small business",
                patient_volume=lead.patient_volume.value if lead.patient_volume else "1-50 patients",
                needs_summary=lead.ai_summary or "body composition tracking",
                tier=tier.value,
            )
            email_template = f"""Subject: {email_result.email_subject}

{email_result.email_body}"""

            sms_result = self.generate_sms(
                lead_name=lead.first_name,
                tier=tier.value,
                has_booking=lead.has_booking(),
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
        result = self.analyze_business(
            business_size=lead.business_size.value if lead.business_size else "Unknown",
            patient_volume=lead.patient_volume.value if lead.patient_volume else "Unknown",
            company=lead.company or "Unknown",
            industry=lead.enrichment.company_primary_industry if lead.enrichment else "Healthcare",
        )
        return {
            "score": result.fit_score,
            "reasoning": result.reasoning,
        }

    def _analyze_engagement(self, lead: Lead) -> Dict[str, Any]:
        """Analyze engagement using DSPy."""
        result = self.analyze_engagement(
            response_type=lead.response_type.value,
            has_calendly_booking=lead.has_booking(),
            body_comp_response=lead.body_comp_tracking or "No response provided",
            ai_summary=lead.ai_summary or "No summary available",
        )
        return {
            "score": result.engagement_score,
            "intent_level": result.intent_level,
            "reasoning": result.reasoning,
        }

    def _calculate_criteria(self, lead: Lead, business_fit: Dict, engagement: Dict) -> QualificationCriteria:
        """Calculate detailed qualification criteria."""
        # Business size scoring (0-20)
        business_size_score = 0
        if lead.business_size:
            if "Large" in lead.business_size.value:
                business_size_score = 20
            elif "Medium" in lead.business_size.value:
                business_size_score = 15
            elif "Small" in lead.business_size.value:
                business_size_score = 10

        # Patient volume scoring (0-20)
        patient_volume_score = 0
        if lead.patient_volume:
            if "300+" in lead.patient_volume.value:
                patient_volume_score = 20
            elif "51-300" in lead.patient_volume.value:
                patient_volume_score = 15
            elif "1-50" in lead.patient_volume.value:
                patient_volume_score = 10

        # Industry fit (0-15) - from business fit analysis
        industry_fit_score = min(15, int(business_fit["score"] * 0.3))

        # Response completeness (0-15)
        response_completeness_score = 15 if lead.is_complete_submission() else 5

        # Calendly booking (0-10)
        calendly_booking_score = 10 if lead.has_booking() else 0

        # Response quality (0-10) - from engagement analysis
        response_quality_score = min(10, int(engagement["score"] * 0.2))

        # Company data (0-10)
        company_data_score = 0
        if lead.enrichment:
            if lead.enrichment.company_revenue_numeric and lead.enrichment.company_revenue_numeric > 0:
                company_data_score += 5
            if lead.enrichment.company_employee_count and lead.enrichment.company_employee_count > 0:
                company_data_score += 5

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
        """Determine qualification tier from score."""
        if score >= self.HOT_THRESHOLD:
            return LeadTier.HOT
        elif score >= self.WARM_THRESHOLD:
            return LeadTier.WARM
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

        if lead.has_booking():
            reasoning_parts.append("\n✅ Lead has scheduled a Calendly call - high intent signal.")

        if lead.is_complete_submission():
            reasoning_parts.append("✅ Complete Typeform submission - strong engagement.")
        else:
            reasoning_parts.append("⚠️ Partial submission - may need nurturing.")

        return "\n".join(reasoning_parts)

    def _extract_key_factors(self, lead: Lead, business_fit: Dict, engagement: Dict) -> List[str]:
        """Extract key positive factors."""
        factors = []

        if lead.has_booking():
            factors.append("Calendly call scheduled")

        if lead.is_complete_submission():
            factors.append("Complete Typeform response")

        if lead.business_size and "Large" in lead.business_size.value:
            factors.append("Large business (20+ employees)")

        if lead.patient_volume and "300+" in lead.patient_volume.value:
            factors.append("High patient volume (300+)")

        if engagement["intent_level"] == "high":
            factors.append("High purchase intent")

        if lead.enrichment and lead.enrichment.company_revenue_numeric and lead.enrichment.company_revenue_numeric > 1000000:
            factors.append("Revenue > $1M")

        return factors

    def _extract_concerns(self, lead: Lead, business_fit: Dict, engagement: Dict) -> List[str]:
        """Extract potential concerns."""
        concerns = []

        if not lead.is_complete_submission():
            concerns.append("Partial Typeform submission")

        if not lead.has_booking():
            concerns.append("No Calendly booking yet")

        if not lead.phone:
            concerns.append("No phone number provided")

        if engagement["intent_level"] == "low":
            concerns.append("Low engagement signals")

        if lead.business_size and "Small" in lead.business_size.value:
            concerns.append("Small business (may have budget constraints)")

        return concerns
