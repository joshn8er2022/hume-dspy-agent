"""DSPy signatures for follow-up agent."""
import dspy


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
