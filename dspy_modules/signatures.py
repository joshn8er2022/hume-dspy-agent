"""DSPy signatures for lead qualification and processing."""
import dspy
from typing import List
from models import (
    Lead,
    QualificationResult,
    QualificationCriteria,
    NextAction,
)


class QualifyLead(dspy.Signature):
    """Qualify an inbound lead based on business fit and engagement.

    Analyze the lead's business profile, patient volume, response quality,
    and engagement signals to determine qualification score and next actions.
    """

    # Input
    lead_data: Lead = dspy.InputField(
        desc="Complete lead information including contact, business, and engagement data"
    )

    # Output
    qualification: QualificationResult = dspy.OutputField(
        desc="Structured qualification result with score, reasoning, and recommended actions"
    )


class AnalyzeBusinessFit(dspy.Signature):
    """Analyze how well a lead fits the ideal customer profile.

    Consider business size, patient volume, industry, and company data
    to determine business fit score.
    """

    business_size: str = dspy.InputField(desc="Business size category")
    patient_volume: str = dspy.InputField(desc="Target patient monitoring volume")
    company: str = dspy.InputField(desc="Company name")
    industry: str = dspy.InputField(desc="Primary industry")

    fit_score: int = dspy.OutputField(
        desc="Business fit score (0-50)"
    )
    reasoning: str = dspy.OutputField(
        desc="Explanation of fit score"
    )


class AnalyzeEngagement(dspy.Signature):
    """Analyze lead engagement signals and intent.

    Evaluate response completeness, quality, booking status,
    and overall engagement to determine engagement score.
    """

    response_type: str = dspy.InputField(desc="completed or partial")
    has_calendly_booking: bool = dspy.InputField(desc="Whether lead booked a call")
    body_comp_response: str = dspy.InputField(
        desc="Lead's response about body composition tracking needs"
    )
    ai_summary: str = dspy.InputField(
        desc="AI-generated summary of lead's needs"
    )

    engagement_score: int = dspy.OutputField(
        desc="Engagement score (0-50)"
    )
    intent_level: str = dspy.OutputField(
        desc="high, medium, or low intent"
    )
    reasoning: str = dspy.OutputField(
        desc="Explanation of engagement assessment"
    )


class DetermineNextActions(dspy.Signature):
    """Determine optimal next actions for a qualified lead.

    Based on qualification score, tier, and lead characteristics,
    recommend specific actions and prioritization.
    """

    qualification_score: int = dspy.InputField(desc="Lead qualification score (0-100)")
    tier: str = dspy.InputField(desc="hot, warm, cold, or unqualified")
    has_booking: bool = dspy.InputField(desc="Whether lead has Calendly booking")
    response_complete: bool = dspy.InputField(desc="Whether Typeform response is complete")

    next_actions: List[NextAction] = dspy.OutputField(
        desc="Ordered list of recommended next actions"
    )
    priority: int = dspy.OutputField(
        desc="Priority level (1=highest, 5=lowest)"
    )
    reasoning: str = dspy.OutputField(
        desc="Explanation of recommended actions"
    )


class GenerateEmailTemplate(dspy.Signature):
    """Generate personalized email template for lead follow-up.

    Create engaging, personalized email based on lead's specific
    needs, business profile, and qualification tier.
    """

    lead_name: str = dspy.InputField(desc="Lead's full name")
    company: str = dspy.InputField(desc="Company name")
    business_size: str = dspy.InputField(desc="Business size")
    patient_volume: str = dspy.InputField(desc="Target patient volume")
    needs_summary: str = dspy.InputField(desc="Summary of lead's needs")
    tier: str = dspy.InputField(desc="Qualification tier")

    email_subject: str = dspy.OutputField(
        desc="Compelling email subject line"
    )
    email_body: str = dspy.OutputField(
        desc="Personalized email body with clear CTA"
    )


class GenerateSMSMessage(dspy.Signature):
    """Generate concise SMS message for lead follow-up.

    Create brief, engaging SMS (160 chars max) for immediate outreach.
    """

    lead_name: str = dspy.InputField(desc="Lead's first name")
    tier: str = dspy.InputField(desc="Qualification tier")
    has_booking: bool = dspy.InputField(desc="Whether lead has booking")

    sms_message: str = dspy.OutputField(
        desc="SMS message (max 160 characters)"
    )
