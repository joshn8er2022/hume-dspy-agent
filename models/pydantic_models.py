"""
Comprehensive Pydantic Data Models (v2 Compatible)

All data structures for Hume DSPy Agent system.
Follows hybrid LangGraph+DSPy+Pydantic architecture.

Principles:
- ALL data must be Pydantic BaseModel
- Validators for business logic (v2 API)
- Proper field descriptions
- Type safety throughout
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ===== ENUMS =====

class QualificationTier(str, Enum):
    """Lead qualification tiers."""
    SCORCHING = "scorching"
    HOT = "hot"
    WARM = "warm"
    COOL = "cool"
    COLD = "cold"
    UNQUALIFIED = "unqualified"


class LeadStatus(str, Enum):
    """Lead lifecycle status."""
    NEW = "new"
    QUALIFIED = "qualified"
    CONTACTED = "contacted"
    ENGAGED = "engaged"
    NURTURING = "nurturing"
    CONVERTED = "converted"
    LOST = "lost"


class ChannelType(str, Enum):
    """Communication channels."""
    EMAIL = "email"
    SMS = "sms"
    CALL = "call"
    LINKEDIN = "linkedin"
    SLACK = "slack"
    LETTER = "letter"


class Priority(str, Enum):
    """Task priority levels."""
    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ===== CORE DATA MODELS =====

class Lead(BaseModel):
    """Lead data model with validation."""
    id: Optional[str] = Field(default=None, description="Lead UUID")
    email: str = Field(..., description="Lead email address")
    name: Optional[str] = Field(default=None, description="Lead name")
    company: Optional[str] = Field(default=None, description="Company name")
    phone: Optional[str] = Field(default=None, description="Phone number")
    
    # Qualification
    qualification_tier: Optional[QualificationTier] = Field(default=None)
    qualification_score: Optional[int] = Field(default=None, ge=0, le=100)
    business_fit_score: Optional[int] = Field(default=None, ge=0, le=50)
    engagement_score: Optional[int] = Field(default=None, ge=0, le=50)
    
    # Status
    status: LeadStatus = Field(default=LeadStatus.NEW)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    # Metadata
    source: Optional[str] = Field(default=None, description="Lead source")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        if '@' not in v or '.' not in v:
            raise ValueError('Invalid email format')
        return v.lower().strip()
    
    @field_validator('qualification_score', 'business_fit_score', 'engagement_score')
    @classmethod
    def validate_score_range(cls, v: Optional[int]) -> Optional[int]:
        """Validate score is in valid range."""
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Score must be between 0 and 100')
        return v


class QualificationResult(BaseModel):
    """Result of lead qualification."""
    lead_id: str = Field(..., description="Lead UUID")
    tier: QualificationTier = Field(..., description="Qualification tier")
    score: int = Field(..., ge=0, le=100, description="Overall score")
    business_fit_score: int = Field(..., ge=0, le=50)
    engagement_score: int = Field(..., ge=0, le=50)
    
    reasoning: str = Field(..., description="Qualification reasoning")
    next_actions: List[str] = Field(default_factory=list)
    
    qualified_at: datetime = Field(default_factory=datetime.utcnow)


# ===== COMPANY & CONTACT MODELS =====

class CompanyData(BaseModel):
    """Company information."""
    name: str = Field(..., description="Company name")
    domain: Optional[str] = Field(default=None, description="Company domain")
    industry: Optional[str] = Field(default=None, description="Industry")
    size: Optional[str] = Field(default=None, description="Company size")
    revenue: Optional[str] = Field(default=None, description="Annual revenue")
    location: Optional[str] = Field(default=None, description="HQ location")
    
    # Metadata
    linkedin: Optional[str] = Field(default=None)
    website: Optional[str] = Field(default=None)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ContactInfo(BaseModel):
    """Contact information."""
    id: Optional[str] = Field(default=None, description="Contact UUID")
    name: str = Field(..., description="Contact name")
    email: str = Field(..., description="Contact email")
    title: Optional[str] = Field(default=None, description="Job title")
    phone: Optional[str] = Field(default=None, description="Phone number")
    linkedin: Optional[str] = Field(default=None, description="LinkedIn URL")
    
    # Company
    company_name: Optional[str] = Field(default=None)
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v.lower().strip()


# ===== COMMUNICATION MODELS =====

class EmailMessage(BaseModel):
    """Email message data model."""
    to: str = Field(..., description="Recipient email")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body (HTML or plain text)")
    from_email: Optional[str] = Field(default=None)
    cc: Optional[List[str]] = Field(default=None)
    bcc: Optional[List[str]] = Field(default=None)
    
    # Metadata
    template_id: Optional[str] = Field(default=None)
    campaign_id: Optional[str] = Field(default=None)
    lead_id: Optional[str] = Field(default=None)
    
    @field_validator('to')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v.lower().strip()


class SMSMessage(BaseModel):
    """SMS message data model."""
    to: str = Field(..., description="Recipient phone number")
    body: str = Field(..., max_length=160, description="SMS body")
    from_number: Optional[str] = Field(default=None)
    
    # Metadata
    lead_id: Optional[str] = Field(default=None)
    campaign_id: Optional[str] = Field(default=None)
    
    @field_validator('body')
    @classmethod
    def validate_length(cls, v: str) -> str:
        if len(v) > 160:
            raise ValueError('SMS must be 160 characters or less')
        return v


class CallRecord(BaseModel):
    """Phone call record."""
    lead_id: str = Field(...)
    phone_number: str = Field(...)
    duration_seconds: Optional[int] = Field(default=None, ge=0)
    outcome: Optional[str] = Field(default=None)
    transcript: Optional[str] = Field(default=None)
    
    called_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class Touchpoint(BaseModel):
    """Campaign touchpoint."""
    id: Optional[str] = Field(default=None)
    contact_id: str = Field(...)
    channel: ChannelType = Field(...)
    message: str = Field(...)
    
    scheduled_at: datetime = Field(...)
    executed_at: Optional[datetime] = Field(default=None)
    outcome: Optional[str] = Field(default=None)
    
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


# ===== RESEARCH MODELS =====

class ResearchFindings(BaseModel):
    """Research findings data model."""
    lead_id: str = Field(...)
    company_name: Optional[str] = Field(default=None)
    
    # Findings
    company_info: Optional[Dict[str, Any]] = Field(default_factory=dict)
    person_info: Optional[Dict[str, Any]] = Field(default_factory=dict)
    competitive_intel: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    # Quality
    sources: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    
    researched_at: datetime = Field(default_factory=datetime.utcnow)


# ===== WORKFLOW STATE MODELS =====

class FollowUpState(BaseModel):
    """State for FollowUpAgent LangGraph workflow."""
    lead: Lead = Field(...)
    qualification: QualificationResult = Field(...)
    
    # Sequence tracking
    emails_sent: int = Field(default=0, ge=0)
    sms_sent: int = Field(default=0, ge=0)
    calls_made: int = Field(default=0, ge=0)
    
    # Timing
    last_contact_at: Optional[datetime] = Field(default=None)
    next_contact_at: Optional[datetime] = Field(default=None)
    
    # Current state
    current_step: str = Field(default="initial_email")
    next_action: str = Field(default="send_initial_email")
    current_email: Optional[EmailMessage] = Field(default=None)
    
    # Results
    responses_received: int = Field(default=0)
    engagement_detected: bool = Field(default=False)


class ABMCampaignState(BaseModel):
    """State for AccountOrchestrator LangGraph workflow."""
    company: CompanyData = Field(...)
    contacts: List[ContactInfo] = Field(default_factory=list)
    touchpoints: List[Touchpoint] = Field(default_factory=list)
    
    # Campaign tracking
    touchpoints_executed: int = Field(default=0)
    contacts_engaged: int = Field(default=0)
    
    # Current state
    current_contact_index: int = Field(default=0)
    current_step: str = Field(default="research_contacts")
    
    # Results
    responses_received: int = Field(default=0)
    meetings_booked: int = Field(default=0)
    campaign_status: str = Field(default="active")


# ===== STRATEGY MODELS =====

class StrategyDecision(BaseModel):
    """Strategic decision data model."""
    decision_type: str = Field(...)
    recommendation: str = Field(...)
    reasoning: str = Field(...)
    
    # Impact
    expected_impact: str = Field(...)
    confidence: float = Field(..., ge=0.0, le=1.0)
    
    # Execution
    priority: Priority = Field(default=Priority.MEDIUM)
    estimated_effort: Optional[str] = Field(default=None)
    
    decided_at: datetime = Field(default_factory=datetime.utcnow)


class PipelineStats(BaseModel):
    """Pipeline statistics data model."""
    total_leads: int = Field(default=0, ge=0)
    scorching: int = Field(default=0, ge=0)
    hot: int = Field(default=0, ge=0)
    warm: int = Field(default=0, ge=0)
    cool: int = Field(default=0, ge=0)
    cold: int = Field(default=0, ge=0)
    unqualified: int = Field(default=0, ge=0)
    
    # Metrics
    qualification_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    avg_score: float = Field(default=0.0, ge=0.0, le=100.0)
    
    # Timing
    time_range: str = Field(default="24h")
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ===== TASK MODELS =====

class Task(BaseModel):
    """Task data model for delegation."""
    id: str = Field(...)
    description: str = Field(...)
    assigned_to: str = Field(...)
    assigned_by: str = Field(...)
    
    priority: Priority = Field(default=Priority.MEDIUM)
    status: str = Field(default="pending")
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    deadline: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    
    # Results
    result: Optional[str] = Field(default=None)
    error: Optional[str] = Field(default=None)


# ===== MONITORING MODELS =====

class Issue(BaseModel):
    """Issue detected by monitoring."""
    id: str = Field(...)
    severity: str = Field(...)
    description: str = Field(...)
    component: str = Field(...)
    
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = Field(default=None)
    
    # Resolution
    fix_description: Optional[str] = Field(default=None)
    fix_implemented: bool = Field(default=False)


class MonitoringState(BaseModel):
    """State for autonomous monitoring workflow."""
    last_check_at: datetime = Field(default_factory=datetime.utcnow)
    issues_detected: List[Issue] = Field(default_factory=list)
    fixes_implemented: int = Field(default=0)
    
    # Metrics
    pipeline_health: float = Field(default=1.0, ge=0.0, le=1.0)
    system_health: float = Field(default=1.0, ge=0.0, le=1.0)
    
    current_step: str = Field(default="check_pipeline")
