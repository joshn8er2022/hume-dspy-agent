"""Typeform webhook payload models.

These models match the ACTUAL Typeform webhook structure.
See: https://www.typeform.com/developers/webhooks/example-payload/
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class TypeformField(BaseModel):
    """Field metadata in Typeform answer."""
    id: str
    type: str
    ref: Optional[str] = None


class TypeformChoice(BaseModel):
    """Single choice answer."""
    id: Optional[str] = None
    label: Optional[str] = None
    ref: Optional[str] = None


class TypeformChoices(BaseModel):
    """Multiple choice answer."""
    ids: Optional[List[str]] = None
    labels: Optional[List[str]] = None
    refs: Optional[List[str]] = None
    other: Optional[str] = None


class TypeformAnswer(BaseModel):
    """Individual answer in Typeform response.

    The actual answer value is in a type-specific field:
    - text: for text/short_text/long_text
    - email: for email
    - number: for number/rating/opinion_scale
    - boolean: for yes_no/legal
    - choice: for dropdown/multiple_choice/picture_choice
    - choices: for multiple selection
    - date: for date
    - url/file_url: for file uploads
    """
    type: str
    field: TypeformField

    # Type-specific answer fields (only one will be populated)
    text: Optional[str] = None
    email: Optional[str] = None
    number: Optional[int] = None
    boolean: Optional[bool] = None
    choice: Optional[TypeformChoice] = None
    choices: Optional[TypeformChoices] = None
    date: Optional[str] = None
    url: Optional[str] = None
    file_url: Optional[str] = None


class TypeformVariable(BaseModel):
    """Typeform variable."""
    key: str
    type: str
    text: Optional[str] = None
    number: Optional[int] = None


class TypeformCalculated(BaseModel):
    """Calculated score."""
    score: Optional[int] = None


class TypeformFormResponse(BaseModel):
    """Form response data from Typeform webhook."""
    form_id: str
    token: str  # Unique submission ID
    submitted_at: datetime
    landed_at: datetime
    answers: List[TypeformAnswer]

    # Optional fields
    definition: Optional[Dict[str, Any]] = None
    hidden: Optional[Dict[str, Any]] = None
    variables: Optional[List[TypeformVariable]] = None
    calculated: Optional[TypeformCalculated] = None
    ending: Optional[Dict[str, Any]] = None


class TypeformWebhookPayload(BaseModel):
    """Complete Typeform webhook payload.

    This is what Typeform actually sends to your webhook endpoint.
    """
    event_id: str
    event_type: str  # Usually "form_response"
    form_response: TypeformFormResponse


class TypeformWebhook(TypeformWebhookPayload):
    """Alias for backward compatibility."""
    pass
