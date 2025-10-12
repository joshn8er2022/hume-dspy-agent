"""Event models for tracking system events and webhooks."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from .base import TimestampedModel


class EventType(str, Enum):
    """Types of events in the system."""
    TYPEFORM_SUBMISSION = "typeform_submission"
    LEAD_CREATED = "lead_created"
    LEAD_QUALIFIED = "lead_qualified"
    LEAD_CONTACTED = "lead_contacted"
    BOOKING_SCHEDULED = "booking_scheduled"
    BOOKING_COMPLETED = "booking_completed"
    NO_SHOW = "no_show"
    EMAIL_SENT = "email_sent"
    SMS_SENT = "sms_sent"
    CALL_MADE = "call_made"
    SLACK_NOTIFICATION = "slack_notification"
    CRM_UPDATED = "crm_updated"
    AGENT_ACTION = "agent_action"


class EventSource(str, Enum):
    """Source systems for events."""
    TYPEFORM = "typeform"
    N8N = "n8n"
    AGENT = "agent"
    API = "api"
    WEBHOOK = "webhook"
    SCHEDULED = "scheduled"
    MANUAL = "manual"


class Event(TimestampedModel):
    """System event for audit trail and processing."""

    id: str = Field(..., description="Unique event identifier")
    event_type: EventType
    source: EventSource

    # Related entities
    lead_id: Optional[str] = None
    user_id: Optional[str] = None
    agent_name: Optional[str] = None

    # Event data
    payload: Dict[str, Any] = Field(default_factory=dict)

    # Processing status
    processed: bool = Field(default=False)
    processed_at: Optional[datetime] = None
    processed_by: Optional[str] = None

    # Error handling
    error: Optional[str] = None
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def mark_processed(self, processed_by: str) -> None:
        """Mark event as processed."""
        self.processed = True
        self.processed_at = datetime.utcnow()
        self.processed_by = processed_by

    def mark_error(self, error: str) -> None:
        """Mark event as failed with error."""
        self.error = error
        self.retry_count += 1

    def can_retry(self) -> bool:
        """Check if event can be retried."""
        return self.retry_count < self.max_retries
