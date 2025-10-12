"""Transform Typeform webhook payloads to Lead models."""
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from models.lead import (
    TypeformWebhook,
    Lead,
    ResponseType,
    BusinessSize,
    PatientVolume,
    PartnershipType,
    LeadStatus,
    FIELD_MAPPING
)


def extract_answer_value(answer: Dict[str, Any]) -> Optional[str]:
    """Extract the actual value from a Typeform answer based on its type."""
    answer_type = answer.get("type")

    # Map answer types to their value fields
    type_mapping = {
        "text": "text",
        "email": "email",
        "phone_number": "phone_number",
        "url": "url",
        "number": "number",
        "boolean": "boolean",
        "date": "date",
        "choice": "choice",
        "choices": "choices"
    }

    value_field = type_mapping.get(answer_type)
    if not value_field:
        return None

    value = answer.get(value_field)

    # Handle choice type (extract label)
    if answer_type == "choice" and isinstance(value, dict):
        return value.get("label")

    # Handle choices type (multiple choice)
    if answer_type == "choices" and isinstance(value, dict):
        labels = value.get("labels", [])
        return ", ".join(labels) if labels else None

    return str(value) if value is not None else None


def transform_typeform_to_lead(webhook: TypeformWebhook) -> Lead:
    """Transform Typeform webhook payload to Lead model."""

    form_response = webhook.form_response

    # Extract answers into a dictionary using field IDs
    answers_dict: Dict[str, str] = {}
    for answer in form_response.answers:
        field_id = answer.field.id
        field_name = FIELD_MAPPING.get(field_id, field_id)
        value = extract_answer_value(answer.model_dump())
        if value:
            answers_dict[field_name] = value

    # Determine response type (completed if has all required fields)
    required_fields = ["first_name", "last_name", "email"]
    has_all_required = all(field in answers_dict for field in required_fields)
    response_type = ResponseType.COMPLETED if has_all_required else ResponseType.PARTIAL

    # Map business size if present
    business_size = None
    if "business_size" in answers_dict:
        size_value = answers_dict["business_size"]
        if "1-5" in size_value:
            business_size = BusinessSize.SMALL
        elif "6-20" in size_value:
            business_size = BusinessSize.MEDIUM
        elif "20+" in size_value:
            business_size = BusinessSize.LARGE

    # Map patient volume if present
    patient_volume = None
    if "patient_volume" in answers_dict:
        volume_value = answers_dict["patient_volume"]
        if "1-50" in volume_value:
            patient_volume = PatientVolume.SMALL
        elif "51-300" in volume_value:
            patient_volume = PatientVolume.MEDIUM
        elif "300+" in volume_value:
            patient_volume = PatientVolume.LARGE

    # Determine partnership types
    partnership_types = []
    if answers_dict.get("selling_products") == "Yes":
        partnership_types.append(PartnershipType.WHOLESALE_RETAIL)
    if answers_dict.get("portal_interest") == "Yes":
        partnership_types.append(PartnershipType.PROFESSIONAL)

    # Check for Calendly booking
    calendly_link = answers_dict.get("calendly_url")
    calendly_booked = bool(calendly_link)

    # Parse timestamps
    try:
        typeform_start_date = datetime.fromisoformat(
            form_response.landed_at.replace("Z", "+00:00")
        )
    except:
        typeform_start_date = None

    try:
        typeform_submit_date = datetime.fromisoformat(
            form_response.submitted_at.replace("Z", "+00:00")
        )
    except:
        typeform_submit_date = None

    # Determine initial status
    if calendly_booked:
        status = LeadStatus.BOOKING_SCHEDULED
    elif response_type == ResponseType.PARTIAL:
        status = LeadStatus.PARTIAL
    else:
        status = LeadStatus.NEW

    # Create Lead model
    lead = Lead(
        id=str(uuid.uuid4()),
        typeform_id=form_response.token,

        # Contact info
        first_name=answers_dict.get("first_name", "Unknown"),
        last_name=answers_dict.get("last_name", "Unknown"),
        email=answers_dict.get("email", "unknown@example.com"),
        phone=answers_dict.get("phone"),
        company=answers_dict.get("company"),

        # Business profile
        business_size=business_size,
        patient_volume=patient_volume,

        # Status
        source="typeform",
        status=status,
        response_type=response_type,

        # Partnership
        partnership_types=partnership_types,
        partnership_interest=answers_dict.get("business_goals"),

        # Engagement
        body_comp_tracking=answers_dict.get("current_products"),
        calendly_link=calendly_link,
        calendly_booked=calendly_booked,

        # Timestamps
        typeform_start_date=typeform_start_date,
        typeform_submit_date=typeform_submit_date,

        # Metadata
        metadata={
            "form_id": form_response.form_id,
            "event_id": webhook.event_id,
            "event_type": webhook.event_type,
            "raw_answers": answers_dict,
            "hidden_fields": form_response.hidden or {},
            "variables": form_response.variables or []
        }
    )

    return lead
