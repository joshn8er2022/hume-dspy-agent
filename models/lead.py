"""Lead models based on Typeform submission data."""
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from .base import TimestampedModel


class ResponseType(str, Enum):
    """Typeform response completion status."""
    COMPLETED = "completed"
    PARTIAL = "partial"


class BusinessSize(str, Enum):
    """Business size categories."""
    SMALL = "Small business  (1-5 employees)"
    MEDIUM = "Medium-sized business  (6-20 employees)"
    LARGE = "Large business  (20+ employees)"


class PatientVolume(str, Enum):
    """Patient monitoring volume categories."""
    SMALL = "1-50 patients"
    MEDIUM = "51-300 patients"
    LARGE = "300+ patients"


class PartnershipType(str, Enum):
    """Partnership program types."""
    AFFILIATE = "affiliate"
    WHOLESALE_RETAIL = "wholesale_retail"
    PROFESSIONAL = "professional"


class LeadStatus(str, Enum):
    """Lead lifecycle status."""
    NEW = "new"
    PARTIAL = "partial"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    UNQUALIFIED = "unqualified"
    BOOKING_SCHEDULED = "booking_scheduled"
    BOOKING_COMPLETED = "booking_completed"
    NO_SHOW = "no_show"
    CONVERTED = "converted"
    NURTURE = "nurture"


class EnrichmentData(BaseModel):
    """Enriched data from external sources."""

    # Personal Info
    age: Optional[float] = None
    age_range: Optional[str] = None
    gender: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    region_code: Optional[str] = None

    # Professional Info
    job_title: Optional[str] = None
    job_function: Optional[str] = None
    linkedin_url: Optional[str] = None

    # Company Info
    company_name: Optional[str] = None
    company_employee_count: Optional[float] = None
    company_employee_range: Optional[str] = None
    company_revenue: Optional[str] = None
    company_revenue_numeric: Optional[float] = None
    company_revenue_range: Optional[str] = None
    company_primary_industry: Optional[str] = None
    company_description: Optional[str] = None
    company_phone: Optional[str] = None
    company_website: Optional[str] = None

    # Additional
    photo_url: Optional[str] = None
    twitter_url: Optional[str] = None


# ============================================================================
# TYPEFORM WEBHOOK MODELS (Actual Typeform API Structure)
# ============================================================================

class TypeformFieldRef(BaseModel):
    """Typeform field reference."""
    id: str
    type: str
    ref: str


class TypeformChoice(BaseModel):
    """Typeform multiple choice answer."""
    id: Optional[str] = None
    label: Optional[str] = None
    ref: Optional[str] = None


class TypeformAnswer(BaseModel):
    """Individual answer in Typeform response."""
    type: str
    field: TypeformFieldRef

    # Different answer types
    text: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    url: Optional[str] = None
    choice: Optional[TypeformChoice] = None
    number: Optional[float] = None
    boolean: Optional[bool] = None
    date: Optional[str] = None


class TypeformFormResponse(BaseModel):
    """Typeform form response data."""
    form_id: str
    token: str
    landed_at: str
    submitted_at: str
    answers: List[TypeformAnswer]
    hidden: Optional[Dict[str, Any]] = None
    variables: Optional[List[Dict[str, Any]]] = None
    definition: Optional[Dict[str, Any]] = None
    ending: Optional[Dict[str, Any]] = None


class TypeformWebhook(BaseModel):
    """Complete Typeform webhook payload."""
    event_id: str
    event_type: str
    form_response: TypeformFormResponse


# ============================================================================
# FIELD MAPPING FOR HUME WHOLESALE PARTNERSHIP FORM
# ============================================================================

FIELD_MAPPING = {
    # Core contact fields
    "3KodbBKF4sjs": "first_name",
    "E5lZOmaIikF3": "last_name",
    "rOpAikQSG0QU": "company",
    "pPr9YAraUEmw": "phone",
    "YatnhdTnor9d": "email",

    # Business context fields
    "mHMo6Fy1kvei": "currently_selling",
    "6FtQFaJWOXEj": "products_selling",
    "Za2AoM3CQPlE": "bodypod_familiarity",
    "Q3WLjtqYcf5T": "business_description",
    "YnUfbQ4i3JXX": "number_of_locations",
    "aNbfZ4kgMafJ": "bodypod_quantity",
    "jl8tMiHkukdJ": "web_portal_interest",

    # Calendly booking
    "ocRGUnixrKTF": "calendly_link",
}


# ============================================================================
# LEGACY MODEL (For CSV imports)
# ============================================================================

class TypeformSubmission(BaseModel):
    """Raw Typeform submission data from CSV export."""

    # Unique identifier
    submission_id: str = Field(..., alias="#")

    # Core contact info
    first_name: str = Field(..., alias="First name")
    last_name: str = Field(..., alias="Last name")
    email: EmailStr = Field(..., alias="Email")
    phone_number: Optional[str] = Field(None, alias="Phone number")
    company: Optional[str] = Field(None, alias="Company")

    # Business details
    business_size: Optional[str] = Field(None, alias="Are you a...")
    patient_volume: Optional[str] = Field(
        None,
        alias="Approximately how many patients are you aiming to monitor body composition data for"
    )

    # Partnership interest (for partial submissions)
    partnership_interest: Optional[str] = Field(
        None,
        alias="Please describe what might fit your interests"
    )

    # Long-form response
    body_comp_tracking: Optional[str] = Field(
        None,
        alias="*How do you currently track your patients' body composition data? What do you hope to accomplish by using the BodyPod?*"
    )

    # AI-generated summary
    summary: Optional[str] = Field(None, alias="Summary")

    # Calendly booking
    calendly_link: Optional[str] = Field(
        None,
        alias="Book a call to explore the Hume Ecosystem."
    )

    # Partnership flags
    affiliate: Optional[str] = None
    wholesale_retail: Optional[str] = None
    professional: Optional[str] = None

    # Metadata
    response_type: ResponseType = Field(..., alias="Response Type")
    start_date: Optional[str] = Field(None, alias="Start Date (UTC)")
    stage_date: Optional[str] = Field(None, alias="Stage Date (UTC)")
    submit_date: Optional[str] = Field(None, alias="Submit Date (UTC)")
    network_id: Optional[str] = Field(None, alias="Network ID")
    tags: Optional[str] = Field(None, alias="Tags")
    ending: Optional[str] = Field(None, alias="Ending")

    model_config = {"populate_by_name": True}


class Lead(TimestampedModel):
    """Processed lead with qualification and enrichment."""

    # Core Identity
    id: str = Field(..., description="Unique lead identifier")
    typeform_id: str = Field(..., description="Typeform submission ID")

    # Contact Information
    first_name: str = Field(..., min_length=1, max_length=255)
    last_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: Optional[str] = None
    company: Optional[str] = None

    # Business Profile
    business_size: Optional[BusinessSize] = None
    patient_volume: Optional[PatientVolume] = None

    # Business Context (from Typeform)
    currently_selling: Optional[str] = Field(None, description="Currently selling health/fitness products")
    products_selling: Optional[str] = Field(None, description="Products currently selling")
    bodypod_familiarity: Optional[str] = Field(None, description="Familiarity with BodyPod system")
    business_description: Optional[str] = Field(None, description="Practice/business description")
    number_of_locations: Optional[str] = Field(None, description="Number of business locations")
    bodypod_quantity: Optional[str] = Field(None, description="Desired BodyPod quantity")
    web_portal_interest: Optional[str] = Field(None, description="Interest in web portal")

    # Lead Source & Status
    source: str = Field(default="typeform", description="Lead source")
    status: LeadStatus = Field(default=LeadStatus.NEW)
    response_type: ResponseType

    # Qualification
    score: int = Field(default=0, ge=0, le=100, description="Lead quality score")
    is_qualified: bool = Field(default=False)
    qualification_reason: Optional[str] = None

    # Partnership Interest
    partnership_types: List[PartnershipType] = Field(default_factory=list)
    partnership_interest: Optional[str] = None

    # Engagement
    body_comp_tracking: Optional[str] = None
    ai_summary: Optional[str] = None
    calendly_link: Optional[str] = None
    calendly_booked: bool = Field(default=False)

    # Enrichment
    enrichment: Optional[EnrichmentData] = None

    # CRM Integration
    close_crm_id: Optional[str] = None
    assigned_to: Optional[str] = None

    # Metadata
    typeform_start_date: Optional[datetime] = None
    typeform_submit_date: Optional[datetime] = None
    network_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: int) -> int:
        if v < 0 or v > 100:
            raise ValueError("Score must be between 0 and 100")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v and v.startswith("'"):
            return v[1:]  # Remove leading apostrophe from CSV
        return v

    def get_full_name(self) -> str:
        """Get formatted full name."""
        return f"{self.first_name} {self.last_name}".strip()

    def is_complete_submission(self) -> bool:
        """Check if this is a complete Typeform submission."""
        return self.response_type == ResponseType.COMPLETED

    def has_booking(self) -> bool:
        """Check if lead has a Calendly booking link."""
        return bool(self.calendly_link)
