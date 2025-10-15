"""Transform Typeform webhook payloads to Lead models.

Extraction Strategy:
- Use field.type to identify email, phone, text fields
- No hardcoded FIELD_MAPPING required
- Works with any Typeform structure
"""
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
    LeadStatus
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
    """Transform Typeform webhook payload to Lead model.

    Uses field.type for extraction (no FIELD_MAPPING needed).
    """

    form_response = webhook.form_response

    # Extract by field TYPE (reliable!)
    email = None
    phone = None
    text_fields = []  # For first_name, last_name, company
    business_size_raw = None
    patient_volume_raw = None
    calendly_link = None
    business_goals = None
    current_products = None
    selling_products = None
    portal_interest = None

    for answer in form_response.answers:
        field_type = answer.type
        value = extract_answer_value(answer.model_dump())

        if not value:
            continue

        # Extract by TYPE
        if field_type == "email":
            email = value

        elif field_type == "phone_number":
            phone = value

        elif field_type == "text":
            text_fields.append(value)

        elif field_type == "url":
            if "calendly" in value.lower():
                calendly_link = value

        elif field_type == "choice":
            # Heuristic: Identify by content
            if "employee" in value.lower() or "business" in value.lower():
                business_size_raw = value
            elif "patient" in value.lower():
                patient_volume_raw = value
            elif "yes" in value.lower() or "no" in value.lower():
                if selling_products is None:
                    selling_products = value
                else:
                    portal_interest = value

    # Heuristic: First 3 text fields = first_name, last_name, company
    first_name = text_fields[0] if len(text_fields) >= 1 else "Unknown"
    last_name = text_fields[1] if len(text_fields) >= 2 else "Unknown"
    company = text_fields[2] if len(text_fields) >= 3 else None

    # Remaining text fields might be business_goals or current_products
    if len(text_fields) >= 4:
        business_goals = text_fields[3]
    if len(text_fields) >= 5:
        current_products = text_fields[4]

    # Map business size
    business_size = None
    if business_size_raw:
        if "1-5" in business_size_raw:
            business_size = BusinessSize.SMALL
        elif "6-20" in business_size_raw:
            business_size = BusinessSize.MEDIUM
        elif "20+" in business_size_raw:
            business_size = BusinessSize.LARGE

    # Map patient volume
    patient_volume = None
    if patient_volume_raw:
        if "1-50" in patient_volume_raw:
            patient_volume = PatientVolume.SMALL
        elif "51-300" in patient_volume_raw:
            patient_volume = PatientVolume.MEDIUM
        elif "300+" in patient_volume_raw:
            patient_volume = PatientVolume.LARGE

    # Determine partnership types
    partnership_types = []
    if selling_products and "yes" in selling_products.lower():
        partnership_types.append(PartnershipType.WHOLESALE_RETAIL)
    if portal_interest and "yes" in portal_interest.lower():
        partnership_types.append(PartnershipType.PROFESSIONAL)

    # Check for Calendly booking
    calendly_booked = bool(calendly_link)

    # Determine response type
    has_email = bool(email)
    has_name = bool(first_name and first_name != "Unknown")
    response_type = ResponseType.COMPLETED if (has_email and has_name) else ResponseType.PARTIAL

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

    # Build raw_answers dict for storage
    raw_answers = {}
    for answer in form_response.answers:
        field_id = answer.field.id
        value = extract_answer_value(answer.model_dump())
        if value:
            raw_answers[field_id] = value

    # Create Lead model
    lead = Lead(
        id=str(uuid.uuid4()),
        typeform_id=form_response.token,

        # Contact info
        first_name=first_name,
        last_name=last_name,
        email=email or "unknown@example.com",
        phone=phone,
        company=company,

        # Business profile
        business_size=business_size,
        patient_volume=patient_volume,

        # Status
        source="typeform",
        status=status,
        response_type=response_type,

        # Partnership
        partnership_types=partnership_types,
        partnership_interest=business_goals,

        # Engagement
        body_comp_tracking=current_products,
        calendly_link=calendly_link,
        calendly_booked=calendly_booked,

        # Timestamps
        typeform_start_date=typeform_start_date,
        typeform_submit_date=typeform_submit_date,

        # Metadata
        raw_answers=raw_answers,
        metadata={
            "form_id": form_response.form_id,
            "event_id": webhook.event_id,
            "event_type": webhook.event_type,
            "hidden_fields": form_response.hidden or {},
            "variables": form_response.variables or []
        }
    )

    return lead
