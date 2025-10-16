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

    CONTEXT: Hume Health sells Body Pod (98% accuracy BIA scale) + Hume Connect
    (HIPAA-compliant RPM platform) to healthcare practitioners. We're a $72M company
    with 650K MAU. Target: clinics needing remote patient monitoring.

    KEY DIFFERENTIATORS vs competitors (InBody, Withings, DXA):
    - Daily-use tracking for TRENDS (not just single-point accuracy)
    - Practitioner workflow efficiency (saves 15+ hours/week)
    - Improved patient adherence through daily engagement

    IDEAL B2B CUSTOMER:
    - Healthcare practitioners (weight loss, diabetes, functional medicine, telehealth)
    - 50+ patients (100+ is excellent, 300+ is ideal)
    - Clear pain point: manual data collection, low patient adherence
    - Budget-conscious but ROI-focused

    SCORING GUIDANCE (0-50):
    - 40-50: EXCELLENT FIT - 100+ patients, healthcare practice, clear RPM use case
    - 30-39: GOOD FIT - 50-100 patients, relevant industry, identifiable pain points
    - 20-29: MODERATE FIT - <50 patients OR non-healthcare but wellness-adjacent
    - 10-19: WEAK FIT - Very small practice, unclear use case, but still B2B
    - 0-9: POOR FIT - Consumer inquiry, wrong industry, or no clear business need

    IMPORTANT: Patient volume is the PRIMARY signal. A solo practitioner with 200 patients
    is better than a 50-employee corporate wellness company with 20 clients.

    TONE: Conversational peer-to-peer consultant, NOT robotic AI or pushy salesperson.
    Focus on problems solved, not features. Use practitioner language.
    """

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

    CONTEXT: We're assessing practitioner interest in Hume Connect (RPM platform)
    and Body Pod hardware for their practice. High engagement = clear pain point
    + specific use case + ready to discuss implementation.

    ENGAGEMENT INDICATORS (ranked):
    1. Calendly booking = HIGH INTENT (ready to discuss seriously)
    2. Complete submission = MEDIUM INTENT (interested, needs education)
    3. Specific pain points mentioned = STRONG SIGNAL (knows what they need)
    4. Generic interest = LOW INTENT (browsing, not urgent)

    SCORING GUIDANCE (0-50):
    - 45-50: VERY HIGH INTENT - Calendly booked + detailed pain points + complete submission
    - 35-44: HIGH INTENT - Calendly booked OR very detailed responses about needs
    - 25-34: MEDIUM INTENT - Complete submission with specific use case mentioned
    - 15-24: LOW-MEDIUM INTENT - Partial submission but shows genuine interest
    - 5-14: LOW INTENT - Generic interest, vague responses, just browsing
    - 0-4: VERY LOW INTENT - Spam, wrong audience, or no engagement signals

    IMPORTANT: Quality over quantity. A short but specific response ("I need to track
    50 diabetes patients remotely") scores higher than a long generic one.

    TONE: Consultant analyzing a potential partnership, not grading a student.
    """

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
