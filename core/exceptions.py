"""3-Tier Error Handling System for hume-dspy-agent.

This module implements agent-zero's proven 3-tier exception hierarchy,
adapted for DSPy-based agents with Pydantic validation.

Tier 1: InterventionException - User interruption (restart gracefully)
Tier 2: RepairableException - LLM can self-repair (retry with guidance)
Tier 3: HandledException - Terminal error (log and continue)
"""

from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import uuid


# ============================================================================
# Error Severity and Context Models
# ============================================================================

class ErrorSeverity(str, Enum):
    """Error severity levels for classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorContext(BaseModel):
    """Structured error context with full observability.

    Captures all information needed for:
    - LLM-based error recovery
    - Debugging and troubleshooting
    - Error analytics and monitoring
    """

    # Identification
    error_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Error details
    exception_type: str = Field(..., description="Name of exception class")
    error_message: str = Field(..., description="Human-readable error message")
    stack_trace: Optional[str] = Field(None, description="Full stack trace")
    severity: ErrorSeverity = Field(default=ErrorSeverity.MEDIUM)

    # Context for recovery
    inputs_attempted: Dict[str, Any] = Field(
        default_factory=dict,
        description="Inputs that caused the error"
    )
    repair_hint: Optional[str] = Field(
        None,
        description="Hint to guide LLM toward solution"
    )

    # Retry tracking
    repair_attempts: int = Field(default=0, ge=0)
    max_repair_attempts: int = Field(default=3, ge=1)

    # Original error (if wrapped)
    original_exception: Optional[str] = Field(None)

    # Additional context
    agent_name: Optional[str] = Field(None)
    operation_name: Optional[str] = Field(None)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "error_id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2025-10-31T12:34:56.789Z",
                "exception_type": "ValidationException",
                "error_message": "Invalid email format",
                "inputs_attempted": {
                    "email": "invalid-email",
                    "timeout": 10
                },
                "repair_hint": "Email must be in format user@domain.com",
                "repair_attempts": 1,
                "max_repair_attempts": 3,
                "agent_name": "InboundAgent",
                "operation_name": "validate_lead_data"
            }
        }


# ============================================================================
# Base Exception Class
# ============================================================================

class AgentException(Exception):
    """Base exception with structured error data.

    All agent exceptions carry an ErrorContext Pydantic model
    for structured error information and observability.
    """

    def __init__(
        self,
        message: str,
        error_context: Optional[ErrorContext] = None
    ):
        self.message = message
        self.error_context = error_context or ErrorContext(
            error_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            exception_type=self.__class__.__name__,
            error_message=message
        )
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            "message": self.message,
            "error_context": self.error_context.model_dump() if self.error_context else None
        }


# ============================================================================
# Tier 1: InterventionException
# ============================================================================

class InterventionException(AgentException):
    """Tier 1: User intervention required.

    Raised when user interrupts agent execution to provide
    new instructions or guidance. Agent should restart
    gracefully with user's input.

    Examples:
    - User clicks "Stop" button during execution
    - User provides correction mid-stream
    - User changes priorities during multi-step task

    Behavior:
    - Skip rest of current operation
    - Restart gracefully with new user input
    - Do NOT retry automatically
    """

    def __init__(self, message: str = "User intervention requested"):
        super().__init__(message)


# ============================================================================
# Tier 2: RepairableException
# ============================================================================

class RepairableException(AgentException):
    """Tier 2: Self-repairable error.

    Raised when an error occurs that the LLM can potentially
    fix through reasoning. Error context is added to the
    conversation history, allowing the LLM to adjust its
    approach and retry.

    Examples:
    - API call with invalid parameters -> LLM adjusts parameters
    - Missing required field -> LLM provides the field
    - Rate limit hit -> LLM waits and retries
    - Validation error -> LLM fixes the data format

    Behavior:
    - Capture error context
    - Allow automatic retry with modified inputs
    - Use LLM reasoning to fix the problem
    - Track retry attempts to prevent infinite loops
    """

    def __init__(
        self,
        message: str,
        inputs: Optional[Dict[str, Any]] = None,
        repair_hint: Optional[str] = None,
        max_attempts: int = 3
    ):
        # Create detailed error context
        error_ctx = ErrorContext(
            error_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            exception_type=self.__class__.__name__,
            error_message=message,
            inputs_attempted=inputs or {},
            repair_hint=repair_hint,
            repair_attempts=0,
            max_repair_attempts=max_attempts
        )
        super().__init__(message, error_ctx)

        # Store repair guidance
        self.repair_hint = repair_hint
        self.max_attempts = max_attempts

    def increment_repair_attempt(self):
        """Increment repair attempt counter."""
        if self.error_context:
            self.error_context.repair_attempts += 1

    def can_retry(self) -> bool:
        """Check if more retry attempts are available."""
        if self.error_context:
            return self.error_context.repair_attempts < self.error_context.max_repair_attempts
        return False


# ============================================================================
# Tier 3: HandledException
# ============================================================================

class HandledException(AgentException):
    """Tier 3: Terminal error.

    Raised when a critical error occurs that cannot be recovered.
    Agent execution should terminate gracefully, but the system
    should remain stable.

    Examples:
    - Authentication failure (cannot proceed without auth)
    - System resource exhausted (out of memory, disk full)
    - Configuration error (missing required config)
    - Max retry attempts exceeded
    - Cancelled operation (asyncio.CancelledError)

    Behavior:
    - End current operation immediately
    - Log error with full context
    - Return graceful error response
    - Do NOT retry
    """

    def __init__(
        self,
        message: str,
        original_exception: Optional[Exception] = None
    ):
        error_ctx = ErrorContext(
            error_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            exception_type=self.__class__.__name__,
            error_message=message,
            original_exception=str(original_exception) if original_exception else None,
            severity=ErrorSeverity.CRITICAL
        )
        super().__init__(message, error_ctx)
        self.original_exception = original_exception


# ============================================================================
# Specific RepairableException Subclasses
# ============================================================================

class APICallException(RepairableException):
    """API call failed - LLM can adjust parameters or retry.

    Examples:
    - Invalid request parameters
    - Temporary API downtime
    - Network connectivity issues
    """
    pass


class ValidationException(RepairableException):
    """Data validation failed - LLM can fix the data format.

    Examples:
    - Invalid email format
    - Missing required fields
    - Type mismatch
    """
    pass


class RateLimitException(RepairableException):
    """Rate limit hit - LLM can wait and retry.

    Examples:
    - API rate limit exceeded
    - Too many requests in time window
    """

    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(
            message,
            repair_hint=f"Wait {retry_after} seconds before retrying" if retry_after else "Wait before retrying"
        )
        self.retry_after = retry_after


class MissingDataException(RepairableException):
    """Required data missing - LLM can provide it or find alternative.

    Examples:
    - Missing lead email
    - Missing required field in API response
    - Incomplete data structure
    """
    pass


class TimeoutException(RepairableException):
    """Operation timed out - LLM can retry with longer timeout.

    Examples:
    - API call timeout
    - Database query timeout
    - Long-running operation timeout
    """

    def __init__(self, message: str, timeout_seconds: Optional[int] = None):
        super().__init__(
            message,
            repair_hint=f"Increase timeout beyond {timeout_seconds}s" if timeout_seconds else "Increase timeout"
        )
        self.timeout_seconds = timeout_seconds


# ============================================================================
# Utility Functions
# ============================================================================

def format_error(exception: Exception) -> str:
    """Format exception for logging and display.

    Args:
        exception: Exception to format

    Returns:
        Formatted error message string
    """
    if isinstance(exception, AgentException):
        error_type = exception.__class__.__name__
        message = exception.message
        if exception.error_context:
            error_id = exception.error_context.error_id
            return f"[{error_type}] {message} (Error ID: {error_id})"
        return f"[{error_type}] {message}"
    else:
        return f"[{exception.__class__.__name__}] {str(exception)}"


def is_repairable(exception: Exception) -> bool:
    """Check if exception is repairable.

    Args:
        exception: Exception to check

    Returns:
        True if exception can be repaired, False otherwise
    """
    return isinstance(exception, RepairableException)


def is_intervention(exception: Exception) -> bool:
    """Check if exception is user intervention.

    Args:
        exception: Exception to check

    Returns:
        True if exception is intervention, False otherwise
    """
    return isinstance(exception, InterventionException)


def is_handled(exception: Exception) -> bool:
    """Check if exception is terminal/handled.

    Args:
        exception: Exception to check

    Returns:
        True if exception is terminal, False otherwise
    """
    return isinstance(exception, HandledException)
