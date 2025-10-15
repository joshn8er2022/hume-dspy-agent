"""Typeform webhook transformation - FIXED to extract email/phone correctly.

Problem: Field refs are UUIDs, not semantic names!
Solution: Use field.type to identify email/phone fields.
"""

from typing import Dict, Any, List
from datetime import datetime
from models.lead import Lead, ResponseType
import logging

logger = logging.getLogger(__name__)

def transform_typeform_webhook(webhook_data: Dict[str, Any]) -> Lead:
    """Transform Typeform webhook into Lead - FIXED VERSION."""
    try:
        form_response = webhook_data.get('form_response', {})
        if not form_response:
            raise ValueError("Missing form_response")
        
        answers = form_response.get('answers', [])
        
        # Extract fields by TYPE (not by ref pattern matching!)
        extracted = {
            'first_name': None,
            'last_name': None,
            'email': None,
            'phone': None,
            'company': None,
            'calendly_url': None
        }
        
        raw_answers = {}
        text_fields = []  # Collect text fields for first/last name
        
        for answer in answers:
            field = answer.get('field', {})
            field_type = answer.get('type')
            field_ref = field.get('ref', '')
            
            # Extract by TYPE (reliable!)
            if field_type == 'email':
                extracted['email'] = answer.get('email')
                raw_answers[field_ref] = answer.get('email')
                
            elif field_type == 'phone_number':
                extracted['phone'] = answer.get('phone_number')
                raw_answers[field_ref] = answer.get('phone_number')
                
            elif field_type == 'url':
                url = answer.get('url', '')
                if 'calendly' in url.lower():
                    extracted['calendly_url'] = url
                raw_answers[field_ref] = url
                
            elif field_type == 'text':
                text_value = answer.get('text')
                text_fields.append(text_value)
                raw_answers[field_ref] = text_value
                
            elif field_type == 'choice':
                choice = answer.get('choice', {})
                label = choice.get('label')
                raw_answers[field_ref] = label
                
            elif field_type == 'transcript':
                transcript = answer.get('transcript', {})
                raw_answers[field_ref] = transcript
                
            else:
                # Store other types
                value = answer.get(field_type)
                if value:
                    raw_answers[field_ref] = value
        
        # Heuristic: First two text fields are usually first_name, last_name
        if len(text_fields) >= 1 and text_fields[0]:
            extracted['first_name'] = text_fields[0]
        if len(text_fields) >= 2 and text_fields[1]:
            extracted['last_name'] = text_fields[1]
        if len(text_fields) >= 3 and text_fields[2]:
            # Third text field might be company
            extracted['company'] = text_fields[2]
        
        # Determine response type
        submitted_at = form_response.get('submitted_at')
        response_type = ResponseType.COMPLETE if submitted_at else ResponseType.PARTIAL
        
        # Create Lead
        lead = Lead(
            typeform_id=form_response.get('token', ''),
            form_id=webhook_data.get('form_id', ''),
            raw_answers=raw_answers,
            raw_metadata={
                'form_id': webhook_data.get('form_id'),
                'event_id': webhook_data.get('event_id'),
                'event_type': webhook_data.get('event_type')
            },
            response_type=response_type,
            first_name=extracted['first_name'],
            last_name=extracted['last_name'],
            email=extracted['email'],
            phone=extracted['phone'],
            company=extracted['company'],
            calendly_url=extracted['calendly_url']
        )
        
        logger.info(f"✅ Transformed to Lead: {lead.id}")
        logger.info(f"   Email: {lead.email}")
        logger.info(f"   Phone: {lead.phone}")
        logger.info(f"   Name: {lead.first_name} {lead.last_name}")
        logger.info(f"   Company: {lead.company}")
        
        return lead
        
    except Exception as e:
        logger.error(f"❌ Transform failed: {str(e)}")
        raise
