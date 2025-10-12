"""Pydantic models for Hume DSPy Agent."""

from .base import TimestampedModel, BaseResponse

from .lead import (
    Lead,
    TypeformSubmission,
    EnrichmentData,
    ResponseType,
    BusinessSize,
    PatientVolume,
    PartnershipType,
    LeadStatus,
)

from .typeform import (
    TypeformWebhookPayload,
    TypeformWebhook,
    TypeformFormResponse,
    TypeformAnswer,
    TypeformField,
    TypeformChoice,
    TypeformChoices,
    TypeformVariable,
    TypeformCalculated,
)

from .event import Event, EventType, EventSource

from .qualification import (
    QualificationResult,
    QualificationCriteria,
    QualificationTier,
    NextAction,
)

__all__ = [
    # Base
    "TimestampedModel",
    "BaseResponse",

    # Lead
    "Lead",
    "TypeformSubmission",
    "EnrichmentData",
    "ResponseType",
    "BusinessSize",
    "PatientVolume",
    "PartnershipType",
    "LeadStatus",

    # Typeform webhook models
    "TypeformWebhookPayload",
    "TypeformWebhook",
    "TypeformFormResponse",
    "TypeformAnswer",
    "TypeformField",
    "TypeformChoice",
    "TypeformChoices",
    "TypeformVariable",
    "TypeformCalculated",

    # Event
    "Event",
    "EventType",
    "EventSource",

    # Qualification
    "QualificationResult",
    "QualificationCriteria",
    "QualificationTier",
    "NextAction",
]
