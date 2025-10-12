"""Dynamic Typeform webhook transformation utility.

This module provides form-agnostic transformation of Typeform webhooks.
No hardcoded field mappings - works with ANY Typeform structure.

Core Philosophy:
- Extract ALL fields dynamically
- Store raw answers for complete flexibility
- Handle all Typeform answer types
- Gracefully handle missing/partial data
- Let the DSPy agent interpret the data
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from models.lead import Lead, ResponseType
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# DYNAMIC FIELD EXTRACTION
# ============================================================================

def extract_answer_value(answer: Dict[str, Any]) -> Any:
    """Extract value from a Typeform answer object.

    Handles all Typeform answer types:
    - text, email, url, phone_number
    - number, date
    - choice, choices (single/multiple selection)
    - boolean
    - file_url
    - payment

    Args:
        answer: Typeform answer object

    Returns:
        Extracted value or None
    """
    answer_type = answer.get('type')

    # Text-based answers
    if answer_type in ['text', 'email', 'url', 'phone_number']:
        return answer.get(answer_type)

    # Number answers
    if answer_type == 'number':
        return answer.get('number')

    # Date answers
    if answer_type == 'date':
        return answer.get('date')

    # Single choice answers (dropdown, multiple_choice, picture_choice)
    if answer_type in ['choice', 'dropdown', 'multiple_choice', 'picture_choice']:
        choice = answer.get('choice')
        if choice:
            return choice.get('label') or choice.get('other')

    # Multiple choices answers
    if answer_type == 'choices':
        choices = answer.get('choices', [])
        labels = [c.get('label') for c in choices if c.get('label')]
        return labels if labels else None

    # Boolean answers
    if answer_type == 'boolean':
        return answer.get('boolean')

    # File upload answers
    if answer_type == 'file_url':
        return answer.get('file_url')

    # Payment answers
    if answer_type == 'payment':
        payment = answer.get('payment')
        if payment:
            return f"{payment.get('amount')} {payment.get('currency')}"

    # Unknown type - log and return None
    logger.warning(f"Unknown answer type: {answer_type}")
    return None


def extract_field_name(field: Dict[str, Any]) -> str:
    """Extract a clean field name from Typeform field object.

    Priority:
    1. field.ref (if exists and not empty)
    2. field.title (cleaned)
    3. field.id (as fallback)

    Args:
        field: Typeform field object

    Returns:
        Clean field name
    """
    # Try ref first (best option)
    ref = field.get('ref', '').strip()
    if ref:
        return ref

    # Try title (clean it up)
    title = field.get('title', '').strip()
    if title:
        # Convert to snake_case
        clean_title = title.lower()
        clean_title = clean_title.replace(' ', '_')
        clean_title = clean_title.replace('-', '_')
        # Remove special characters
        clean_title = ''.join(c for c in clean_title if c.isalnum() or c == '_')
        return clean_title

    # Fallback to field ID
    return field.get('id', 'unknown_field')


def build_raw_answers(answers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build raw_answers dictionary from Typeform answers array.

    Extracts ALL fields dynamically with no hardcoded mappings.

    Args:
        answers: List of Typeform answer objects

    Returns:
        Dictionary mapping field names to values
    """
    raw_answers = {}

    for answer in answers:
        # Get field info
        field = answer.get('field', {})
        field_name = extract_field_name(field)

        # Extract value
        value = extract_answer_value(answer)

        # Store in raw_answers
        if value is not None:
            raw_answers[field_name] = value

            # Also store field metadata for reference
            raw_answers[f"{field_name}_type"] = answer.get('type')
            raw_answers[f"{field_name}_id"] = field.get('id')

    return raw_answers


def extract_common_fields(raw_answers: Dict[str, Any]) -> Dict[str, Any]:
    """Extract common fields from raw_answers using intelligent matching.

    Looks for common field patterns across different forms:
    - first_name, last_name, name
    - email, email_address
    - phone, phone_number, mobile
    - company, business_name, organization
    - etc.

    Args:
        raw_answers: Dictionary of all extracted fields

    Returns:
        Dictionary of extracted common fields
    """
    extracted = {}

    # Helper function to find field by pattern
    def find_field(*patterns):
        for pattern in patterns:
            # Exact match
            if pattern in raw_answers:
                return raw_answers[pattern]
            # Case-insensitive match
            for key in raw_answers:
                if key.lower() == pattern.lower():
                    return raw_answers[key]
            # Contains match
            for key in raw_answers:
                if pattern.lower() in key.lower():
                    return raw_answers[key]
        return None

    # Extract first name
    first_name = find_field('first_name', 'firstname', 'fname', 'given_name')
    if first_name:
        extracted['first_name'] = first_name

    # Extract last name
    last_name = find_field('last_name', 'lastname', 'lname', 'surname', 'family_name')
    if last_name:
        extracted['last_name'] = last_name

    # Extract email
    email = find_field('email', 'email_address', 'e_mail', 'contact_email')
    if email:
        extracted['email'] = email

    # Extract phone
    phone = find_field('phone', 'phone_number', 'mobile', 'telephone', 'contact_number')
    if phone:
        extracted['phone'] = phone

    # Extract company
    company = find_field('company', 'business_name', 'organization', 'company_name', 'business')
    if company:
        extracted['company'] = company

    # Extract Calendly URL
    calendly = find_field('calendly_url', 'calendly', 'booking_url', 'schedule_url')
    if calendly:
        extracted['calendly_url'] = calendly

    return extracted


# ============================================================================
# MAIN TRANSFORM FUNCTION
# ============================================================================

def transform_typeform_webhook(webhook_data: Dict[str, Any]) -> Lead:
    """Transform Typeform webhook into Lead object.

    This is a DYNAMIC transformation that works with ANY Typeform structure.
    No hardcoded field mappings required.

    Args:
        webhook_data: Complete Typeform webhook payload

    Returns:
        Lead object with all available data

    Raises:
        ValueError: If required webhook structure is invalid
    """
    try:
        # Extract form_response
        form_response = webhook_data.get('form_response', {})
        if not form_response:
            raise ValueError("Missing form_response in webhook data")

        # Extract answers array
        answers = form_response.get('answers', [])

        # Build raw_answers dictionary (ALL fields, dynamically)
        raw_answers = build_raw_answers(answers)

        logger.info(f"Extracted {len(raw_answers)} fields from Typeform webhook")
        logger.debug(f"Raw answers: {list(raw_answers.keys())}")

        # Extract common fields intelligently
        common_fields = extract_common_fields(raw_answers)

        # Determine response type
        submitted_at = form_response.get('submitted_at')
        response_type = ResponseType.COMPLETE if submitted_at else ResponseType.PARTIAL

        # Parse timestamps
        submitted_at_dt = None
        landed_at_dt = None

        if submitted_at:
            try:
                submitted_at_dt = datetime.fromisoformat(submitted_at.replace('Z', '+00:00'))
            except:
                pass

        landed_at = form_response.get('landed_at')
        if landed_at:
            try:
                landed_at_dt = datetime.fromisoformat(landed_at.replace('Z', '+00:00'))
            except:
                pass

        # Build metadata
        raw_metadata = {
            'form_id': webhook_data.get('form_id'),
            'event_id': webhook_data.get('event_id'),
            'event_type': webhook_data.get('event_type'),
            'landed_at': landed_at,
            'submitted_at': submitted_at,
        }

        # Create Lead object
        lead = Lead(
            typeform_id=form_response.get('token', ''),
            form_id=webhook_data.get('form_id', ''),
            raw_answers=raw_answers,
            raw_metadata=raw_metadata,
            response_type=response_type,
            submitted_at=submitted_at_dt,
            landed_at=landed_at_dt,
            **common_fields  # Unpack extracted common fields
        )

        logger.info(f"Successfully transformed webhook into Lead: {lead.id}")
        logger.info(f"  Response type: {lead.response_type}")
        logger.info(f"  Has email: {bool(lead.email)}")
        logger.info(f"  Has phone: {bool(lead.phone)}")
        logger.info(f"  Total fields: {len(raw_answers)}")

        return lead

    except Exception as e:
        logger.error(f"Error transforming Typeform webhook: {e}")
        raise
