"""Lead data models for Typeform webhook processing.

This module implements a form-agnostic architecture that can handle:
- Multiple different Typeform structures
- Partial submissions (incomplete forms)
- Full submissions
- Any combination of fields

The core principle: Store raw webhook data and extract fields dynamically.
"""

from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import uuid
import json


class ResponseType(str, Enum):
    """Type of form response."""
    PARTIAL = "partial"
    COMPLETE = "complete"


class BusinessSize(str, Enum):
    """Business size categories."""
    SOLO = "solo"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class PatientVolume(str, Enum):
    """Patient volume categories."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class PartnershipType(str, Enum):
    """Partnership type options."""
    WHOLESALE = "wholesale"
    DROPSHIP = "dropship"
    AFFILIATE = "affiliate"
    PLATFORM = "platform"


class LeadStatus(str, Enum):
    """Lead status in the pipeline."""
    NEW = "new"
    CONTACTED = "contacted"
    AWAITING_RESPONSE = "awaiting_response"
    FOLLOWING_UP = "following_up"
    RESPONDED = "responded"
    QUALIFIED = "qualified"
    UNQUALIFIED = "unqualified"
    COLD = "cold"
    CONVERTED = "converted"


class LeadTier(str, Enum):
    """Lead qualification tier with granular segmentation.

    6-tier system for precise lead prioritization and nurture cadence:
    - SCORCHING: 90-100 - Book meeting immediately, highest priority
    - HOT: 75-89 - High priority follow-up, same-day outreach
    - WARM: 60-74 - Standard nurture sequence, 24-48h follow-up
    - COOL: 45-59 - Long-term nurture, weekly touchpoints
    - COLD: 30-44 - Low priority drip campaign, monthly check-ins
    - UNQUALIFIED: <30 - No active outreach, passive content only
    """
    SCORCHING = "scorching"
    HOT = "hot"
    WARM = "warm"
    COOL = "cool"
    COLD = "cold"
    UNQUALIFIED = "unqualified"


# ============================================================================
# FORM-AGNOSTIC LEAD MODEL
# ============================================================================

class Lead(BaseModel):
    """Form-agnostic lead model that can handle ANY Typeform structure.

    Core Philosophy:
    - Only 3 required fields: id, typeform_id, form_id
    - All business data stored in raw_answers JSON
    - Extract fields dynamically based on form_id
    - No hardcoded field mappings
    - Gracefully handles missing/partial data
    """

    # ========================================================================
    # REQUIRED FIELDS (Minimal - only what we MUST have)
    # ========================================================================
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    typeform_id: str = Field(..., description="Unique Typeform response token")
    form_id: str = Field(..., description="Typeform form ID that sent this webhook")

    # ========================================================================
    # RAW DATA STORAGE (The key to flexibility)
    # ========================================================================
    raw_answers: Dict[str, Any] = Field(
        default_factory=dict,
        description="Complete raw answers array from Typeform webhook"
    )
    raw_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Metadata from webhook (landed_at, submitted_at, etc.)"
    )

    @field_validator('raw_metadata', mode='before')
    @classmethod
    def handle_null_metadata(cls, v):
        """Handle NULL raw_metadata from old database records."""
        return v if v is not None else {}

    # ========================================================================
    # RESPONSE METADATA (Optional but useful)
    # ========================================================================
    response_type: ResponseType = Field(
        default=ResponseType.PARTIAL,
        description="Whether this is a partial or complete submission"
    )
    submitted_at: Optional[datetime] = Field(
        default=None,
        description="When form was submitted (null for partial)"
    )
    landed_at: Optional[datetime] = Field(
        default=None,
        description="When user first opened the form"
    )

    # ========================================================================
    # EXTRACTED CONTACT FIELDS (All optional - may not exist in all forms)
    # ========================================================================
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None

    # ========================================================================
    # EXTRACTED BUSINESS CONTEXT (All optional)
    # ========================================================================
    business_size: Optional[BusinessSize] = None
    patient_volume: Optional[PatientVolume] = None
    partnership_type: Optional[PartnershipType] = None
    currently_selling: Optional[str] = None
    products_selling: Optional[str] = None
    bodypod_familiarity: Optional[str] = None
    business_description: Optional[str] = None
    number_of_locations: Optional[str] = None
    bodypod_quantity: Optional[str] = None
    web_portal_interest: Optional[str] = None

    # ========================================================================
    # BOOKING & ENGAGEMENT (All optional)
    # ========================================================================
    calendly_url: Optional[str] = None
    booking_confirmed: bool = False

    # ========================================================================
    # QUALIFICATION DATA (Set by agent)
    # ========================================================================
    status: LeadStatus = LeadStatus.NEW
    tier: Optional[LeadTier] = None
    qualification_score: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
        description="Overall qualification score 0-100"
    )

    # ========================================================================
    # TIMESTAMPS
    # ========================================================================
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def get_field(self, field_name: str, default: Any = None) -> Any:
        """Safely get a field from raw_answers by name.

        Args:
            field_name: Name of the field to retrieve
            default: Default value if field not found

        Returns:
            Field value or default
        """
        return self.raw_answers.get(field_name, default)

    def has_field(self, field_name: str) -> bool:
        """Check if a field exists in raw_answers.

        Args:
            field_name: Name of the field to check

        Returns:
            True if field exists and has a value
        """
        value = self.raw_answers.get(field_name)
        return value is not None and value != ""

    def get_all_fields(self) -> Dict[str, Any]:
        """Get all available fields from raw_answers.

        Returns:
            Dictionary of all field names and values
        """
        return self.raw_answers.copy()

    def extract_semantic_fields(self) -> Dict[str, Any]:
        """Extract semantic fields from raw Typeform field IDs.

        For old database records that have Typeform field IDs as keys,
        this extracts useful information by searching for patterns in values.

        Returns:
            Dictionary with extracted semantic fields
        """
        extracted = {}

        for field_id, value in self.raw_answers.items():
            if not value or value == "null":
                continue

            value_str = str(value).lower()

            # Detect Calendly URL
            if "calendly.com" in value_str:
                extracted["calendly_url"] = value
                extracted["has_calendly"] = True

            # Detect email
            elif "@" in value_str and "." in value_str:
                extracted["email"] = value

            # Detect company (heuristic: contains LLC, Inc, Corp, or is longer text)
            elif any(x in value for x in ["LLC", "Inc", "Corp", "Company", "Tactical", "Clinic"]):
                extracted["company"] = value

            # Detect use case / business goals (long text responses)
            elif len(value_str) > 100:
                extracted["use_case"] = value
                extracted["business_goals"] = value

                # Extract patient volume mentions
                if "member" in value_str or "patient" in value_str:
                    import re
                    numbers = re.findall(r'\d+', value_str)
                    if numbers:
                        volume = max([int(n) for n in numbers])
                        extracted["patient_volume_raw"] = volume

                        # Categorize
                        if volume >= 300:
                            extracted["patient_volume_category"] = "very_high"
                        elif volume >= 100:
                            extracted["patient_volume_category"] = "high"
                        elif volume >= 50:
                            extracted["patient_volume_category"] = "medium"
                        else:
                            extracted["patient_volume_category"] = "low"

        return extracted

    def is_complete(self) -> bool:
        """Check if this is a complete submission.

        Returns:
            True if response_type is COMPLETE
        """
        return self.response_type == ResponseType.COMPLETE

    def has_contact_info(self) -> bool:
        """Check if lead has basic contact information.

        Returns:
            True if has email or phone
        """
        return bool(self.email or self.phone)

    class Config:
        """Pydantic model configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
