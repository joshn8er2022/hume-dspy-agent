"""Qualification models for DSPy agent outputs."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from models.lead import LeadTier  # Import 6-tier system


class NextAction(str, Enum):
    """Recommended next actions for leads."""
    IMMEDIATE_CALL = "immediate_call"
    SCHEDULE_CALL = "schedule_call"
    SEND_EMAIL = "send_email"
    SEND_SMS = "send_sms"
    ADD_TO_NURTURE = "add_to_nurture"
    CREATE_CRM_LEAD = "create_crm_lead"
    ASSIGN_TO_REP = "assign_to_rep"
    FLAG_FOR_REVIEW = "flag_for_review"
    SEND_RESOURCES = "send_resources"
    NO_ACTION = "no_action"


class QualificationCriteria(BaseModel):
    """Individual qualification criteria scores."""

    # Business fit
    business_size_score: int = Field(0, ge=0, le=20)
    patient_volume_score: int = Field(0, ge=0, le=20)
    industry_fit_score: int = Field(0, ge=0, le=15)

    # Engagement
    response_completeness_score: int = Field(0, ge=0, le=15)
    calendly_booking_score: int = Field(0, ge=0, le=10)
    response_quality_score: int = Field(0, ge=0, le=10)

    # Enrichment data
    company_data_score: int = Field(0, ge=0, le=10)

    def calculate_total(self) -> int:
        """Calculate total qualification score."""
        return (
            self.business_size_score +
            self.patient_volume_score +
            self.industry_fit_score +
            self.response_completeness_score +
            self.calendly_booking_score +
            self.response_quality_score +
            self.company_data_score
        )


class QualificationResult(BaseModel):
    """Result of lead qualification by DSPy agent."""

    # Qualification outcome
    is_qualified: bool
    score: int = Field(..., ge=0, le=100)
    tier: LeadTier  # Use 6-tier system

    # Reasoning
    reasoning: str = Field(..., description="AI reasoning for qualification")
    key_factors: List[str] = Field(default_factory=list)
    concerns: List[str] = Field(default_factory=list)

    # Detailed criteria
    criteria: QualificationCriteria

    # Recommended actions
    next_actions: List[NextAction] = Field(default_factory=list)
    priority: int = Field(1, ge=1, le=5, description="1=highest, 5=lowest")

    # Assignment
    assigned_to: Optional[str] = None
    assignment_reason: Optional[str] = None

    # Follow-up
    suggested_email_template: Optional[str] = None
    suggested_sms_message: Optional[str] = None
    suggested_call_script: Optional[str] = None

    # Metadata
    agent_version: str = Field(default="1.0.0")
    model_used: str = Field(default="gpt-4o")
    processing_time_ms: Optional[int] = None
    campaign_id: Optional[str] = Field(None, description="ABM campaign ID if initiated")

    @classmethod
    def from_score(cls, score: int, **kwargs) -> "QualificationResult":
        """Create qualification result from score using 6-tier system."""
        if score >= 90:
            tier = LeadTier.SCORCHING
            is_qualified = True
        elif score >= 75:
            tier = LeadTier.HOT
            is_qualified = True
        elif score >= 60:
            tier = LeadTier.WARM
            is_qualified = True
        elif score >= 45:
            tier = LeadTier.COOL
            is_qualified = False
        elif score >= 30:
            tier = LeadTier.COLD
            is_qualified = False
        else:
            tier = LeadTier.UNQUALIFIED
            is_qualified = False

        return cls(
            is_qualified=is_qualified,
            score=score,
            tier=tier,
            **kwargs
        )
