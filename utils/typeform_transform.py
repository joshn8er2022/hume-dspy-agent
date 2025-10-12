"""Utilities for transforming Typeform webhook data to Lead models."""
from typing import Dict, Any, Optional
from models.typeform import TypeformWebhookPayload, TypeformAnswer
from models.lead import Lead, BusinessSize, PatientVolume, PartnershipType, FIELD_MAPPING
import logging

logger = logging.getLogger(__name__)


def extract_answer_value(answer: TypeformAnswer) -> Any:
    """Extract the actual value from a Typeform answer based on its type.

    Args:
        answer: TypeformAnswer object

    Returns:
        The extracted value (str, int, bool, etc.) or None
    """
    answer_type = answer.type

    # Text-based answers
    if answer_type in ["text", "short_text", "long_text"]:
        return answer.text

    # Email
    elif answer_type == "email":
        return answer.email

    # Numeric answers
    elif answer_type in ["number", "rating", "opinion_scale"]:
        return answer.number

    # Boolean answers
    elif answer_type in ["boolean", "yes_no", "legal"]:
        return answer.boolean

    # Single choice
    elif answer_type in ["choice", "dropdown", "multiple_choice", "picture_choice"]:
        if answer.choice:
            return answer.choice.label or answer.choice.id

    # Multiple choices
    elif answer_type == "choices":
        if answer.choices:
            return answer.choices.labels or answer.choices.ids

    # Date
    elif answer_type == "date":
        return answer.date

    # URL/File
    elif answer_type in ["url", "file_url"]:
        return answer.file_url or answer.url

    # Phone number (usually text type)
    elif answer_type == "phone_number":
        return answer.phone_number if hasattr(answer, "phone_number") else answer.text

    logger.warning(f"Unknown answer type: {answer_type}")
    return None


def map_business_size(value: Optional[str]) -> Optional[BusinessSize]:
    """Map Typeform answer to BusinessSize enum."""
    if not value:
        return None

    value_lower = value.lower()

    if "solo" in value_lower or "1" in value_lower:
        return BusinessSize.SOLO
    elif "small" in value_lower or "2-10" in value_lower:
        return BusinessSize.SMALL
    elif "medium" in value_lower or "11-50" in value_lower:
        return BusinessSize.MEDIUM
    elif "large" in value_lower or "50+" in value_lower or "51+" in value_lower:
        return BusinessSize.LARGE

    return BusinessSize.SMALL  # Default


def map_patient_volume(value: Optional[str]) -> Optional[PatientVolume]:
    """Map Typeform answer to PatientVolume enum."""
    if not value:
        return None

    value_lower = value.lower()

    if "0-50" in value_lower or "under 50" in value_lower:
        return PatientVolume.LOW
    elif "51-200" in value_lower or "50-200" in value_lower:
        return PatientVolume.MEDIUM
    elif "201-500" in value_lower or "200-500" in value_lower:
        return PatientVolume.HIGH
    elif "500+" in value_lower or "501+" in value_lower:
        return PatientVolume.VERY_HIGH

    return PatientVolume.MEDIUM  # Default


def map_partnership_type(value: Optional[str]) -> Optional[PartnershipType]:
    """Map Typeform answer to PartnershipType enum."""
    if not value:
        return None

    value_lower = value.lower()

    if "platform" in value_lower or "connect" in value_lower:
        return PartnershipType.PLATFORM
    elif "wholesale" in value_lower:
        return PartnershipType.WHOLESALE
    elif "dropship" in value_lower:
        return PartnershipType.DROPSHIP
    elif "affiliate" in value_lower:
        return PartnershipType.AFFILIATE
    elif "both" in value_lower or "all" in value_lower:
        return PartnershipType.BOTH

    return PartnershipType.PLATFORM  # Default


def transform_typeform_to_lead(payload: TypeformWebhookPayload) -> Lead:
    """Transform Typeform webhook payload to Lead model.

    Args:
        payload: TypeformWebhookPayload from webhook

    Returns:
        Lead object ready for qualification

    Raises:
        ValueError: If required fields are missing
    """
    form_response = payload.form_response

    # Build field reference map
    field_map: Dict[str, Any] = {}

    for answer in form_response.answers:
        # Use ref if available, otherwise use field ID
        key = answer.field.ref or answer.field.id
        value = extract_answer_value(answer)

        if value is not None:
            field_map[key] = value
            logger.debug(f"Mapped field {key} = {value}")

    # Extract required fields
    email = field_map.get("email") or field_map.get("email_address")
    if not email:
        raise ValueError("Email is required but not found in Typeform response")

    # Build Lead object
    try:
        lead = Lead(
            # Contact info
            first_name=field_map.get("first_name", ""),
            last_name=field_map.get("last_name", ""),
            email=email,
            phone=field_map.get("phone") or field_map.get("phone_number"),

            # Business info
            business_name=field_map.get("business_name") or field_map.get("company_name"),
            business_size=map_business_size(field_map.get("business_size")),
            patient_volume=map_patient_volume(field_map.get("patient_volume")),

            # Partnership info
            partnership_type=map_partnership_type(field_map.get("partnership_type")),

            # Additional fields
            website=field_map.get("website"),
            linkedin=field_map.get("linkedin"),

            # Typeform metadata
            typeform_token=form_response.token,
            submitted_at=form_response.submitted_at,

            # AI summary if available
            ai_summary=field_map.get("ai_summary"),
        )

        logger.info(f"Successfully transformed Typeform submission {form_response.token} to Lead")
        return lead

    except Exception as e:
        logger.error(f"Failed to transform Typeform payload: {e}")
        logger.error(f"Field map: {field_map}")
        raise
