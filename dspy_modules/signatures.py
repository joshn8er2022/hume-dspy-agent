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
    """Analyze how well a B2B lead fits Hume Health's ideal customer profile.

    Use the provided company_context for detailed guidance on:
    - Product details (Body Pod, Hume Connect)
    - Ideal customer profile
    - Competitive positioning
    - Tone and messaging guidelines
    - Scoring criteria

    Score 0-50 based on patient volume (most important), healthcare specialty, and pain point clarity.
    """

    company_context: str = dspy.InputField(desc="Hume Health company context, ICP, competitive positioning, and tone guidelines")
    business_size: str = dspy.InputField(desc="Business size (employees)")
    patient_volume: str = dspy.InputField(desc="Current patient/client volume for remote monitoring")
    company: str = dspy.InputField(desc="Company/practice name")
    industry: str = dspy.InputField(desc="Industry (healthcare, wellness, fitness, etc.)")

    fit_score: int = dspy.OutputField(
        desc="Business fit score (0-50). CRITICAL: Patient volume > Industry fit > Practice size"
    )
    reasoning: str = dspy.OutputField(
        desc="Conversational explanation of fit (avoid AI-speak, focus on their specific practice)"
    )


class AnalyzeEngagement(dspy.Signature):
    """Analyze B2B lead engagement signals for Hume Health RPM solution.

    Use the provided company_context for tone and qualification guidelines.

    Score 0-50 based on: Calendly booking (highest), response specificity, pain point clarity.
    Calendly booking caps score at 39 if not booked.
    """

    company_context: str = dspy.InputField(desc="Hume Health company context and tone guidelines")
    response_type: str = dspy.InputField(desc="completed or partial Typeform submission")
    has_calendly_booking: bool = dspy.InputField(desc="Booked discovery call? (highest intent signal)")
    body_comp_response: str = dspy.InputField(
        desc="Their stated needs for patient body composition tracking"
    )
    ai_summary: str = dspy.InputField(
        desc="Summary of practice needs and pain points"
    )

    engagement_score: int = dspy.OutputField(
        desc="Engagement score (0-50). CRITICAL: Calendly booking + specificity > length of response"
    )
    intent_level: str = dspy.OutputField(
        desc="high (ready to buy), medium (educating), or low (browsing)"
    )
    reasoning: str = dspy.OutputField(
        desc="Conversational assessment of their readiness (avoid robotic analysis)"
    )


class DetermineNextActions(dspy.Signature):
    """Determine optimal next actions for a qualified lead.

    Use company_context to understand Hume Health's sales process and priorities.
    Based on qualification score, tier, and lead characteristics,
    recommend specific actions and prioritization.
    """

    company_context: str = dspy.InputField(desc="Hume Health context for action prioritization and sales process")
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

    Use company_context for tone guidelines and product details.
    Create engaging, personalized email that focuses on problems solved, not features.
    Address lead by name, reference their specific practice/needs.
    """

    company_context: str = dspy.InputField(desc="Hume Health product details, value props, and tone guidelines")
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

    Use company_context for tone guidelines and value proposition.
    Create brief, engaging SMS (160 chars max) for immediate outreach.
    """

    company_context: str = dspy.InputField(desc="Hume Health context for tone and messaging")
    lead_name: str = dspy.InputField(desc="Lead's first name")
    tier: str = dspy.InputField(desc="Qualification tier")
    has_booking: bool = dspy.InputField(desc="Whether lead has booking")

    sms_message: str = dspy.OutputField(
        desc="SMS message (max 160 characters)"
    )


# ===== FOLLOW-UP AGENT SIGNATURES =====

class ComposeFollowUpEmail(dspy.Signature):
    """Compose personalized follow-up email for lead."""
    lead: str = dspy.InputField(desc="Lead data (JSON)")
    qualification: str = dspy.InputField(desc="Qualification result (JSON)")
    emails_sent: int = dspy.InputField(desc="Number of emails already sent")
    research_findings: str = dspy.InputField(desc="Research findings (JSON)")
    
    email_subject: str = dspy.OutputField(desc="Email subject line")
    email_body: str = dspy.OutputField(desc="Email body (personalized)")
    send_timing: str = dspy.OutputField(desc="When to send (immediate, 2d, 5d, 7d)")


class DecideNextAction(dspy.Signature):
    """Decide next action in follow-up sequence."""
    lead: str = dspy.InputField(desc="Lead data (JSON)")
    emails_sent: int = dspy.InputField(desc="Emails sent so far")
    responses_received: int = dspy.InputField(desc="Responses received")
    engagement_signals: str = dspy.InputField(desc="Engagement signals (JSON)")
    
    next_action: str = dspy.OutputField(desc="send_email, send_sms, escalate, mark_lost")
    reasoning: str = dspy.OutputField(desc="Why this action?")
    wait_hours: int = dspy.OutputField(desc="Hours to wait before action")
