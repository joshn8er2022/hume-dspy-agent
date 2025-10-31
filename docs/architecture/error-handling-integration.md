# Error Handling Integration: agent-zero + DSPy

**Integrating agent-zero's 3-tier error handling into DSPy-based agents**

**Author:** Claude Code
**Date:** October 30, 2025
**Version:** 1.0

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [agent-zero Error Handling Analysis](#agent-zero-error-handling-analysis)
3. [Exception Hierarchy Design](#exception-hierarchy-design)
4. [Pydantic Models for Error States](#pydantic-models-for-error-states)
5. [DSPy Error Recovery Implementation](#dspy-error-recovery-implementation)
6. [Integration with hume-dspy-agent](#integration-with-hume-dspy-agent)
7. [Code Examples](#code-examples)
8. [Testing Strategy](#testing-strategy)
9. [Configuration](#configuration)
10. [Migration Guide](#migration-guide)

---

## Executive Summary

This document presents a comprehensive design for integrating **agent-zero's proven 3-tier exception handling** into **DSPy-based agents** while maintaining **Pydantic validation** throughout.

### Key Features

- **3-tier exception hierarchy** compatible with DSPy modules
- **Self-repair capability** using DSPy's reasoning for error recovery
- **Pydantic-validated error states** for type safety
- **Minimal changes** to existing hume-dspy-agent code
- **Graceful degradation** when errors cannot be repaired

### Design Philosophy

1. **Preserve DSPy reasoning** - Error recovery uses DSPy's ChainOfThought for intelligent repair
2. **Maintain Pydantic validation** - All error states are validated Pydantic models
3. **Follow agent-zero patterns** - Same 3-tier exception model proven in production
4. **Enable observability** - Structured error logging for debugging and monitoring

---

## agent-zero Error Handling Analysis

### How agent-zero's Error Tiers Work

agent-zero implements a sophisticated 3-tier exception system in `/Users/joshisrael/agent-zero/agent.py`:

#### Tier 1: InterventionException (Line 261-262)

```python
class InterventionException(Exception):
    pass
```

**Purpose:** User interrupted the agent mid-execution
**Behavior:** Skips rest of current message loop iteration, restarts gracefully
**Use Case:** User provides new instructions while agent is working

**Handling in agent.py (Lines 378-379, 397-398):**
```python
except InterventionException as e:
    pass  # intervention already handled in handle_intervention()
```

#### Tier 2: RepairableException (Line 266-267)

```python
class RepairableException(Exception):
    pass
```

**Purpose:** Error that the LLM can potentially fix through reasoning
**Behavior:**
- Error message formatted and added to conversation history
- Agent loop continues with error context
- LLM sees the error and can adjust its approach
- Allows self-repair through reasoning

**Handling in agent.py (Lines 380-386):**
```python
except RepairableException as e:
    # Forward repairable errors to the LLM, maybe it can fix them
    error_message = errors.format_error(e)
    self.hist_add_warning(error_message)  # Add to LLM's context
    PrintStyle(font_color="red", padding=True).print(error_message)
    self.context.log.log(type="error", content=error_message)
```

**Key Insight:** The error becomes part of the conversation history, allowing the LLM to reason about what went wrong and try a different approach in the next iteration.

#### Tier 3: HandledException (Line 270-271)

```python
class HandledException(Exception):
    pass
```

**Purpose:** Critical error that cannot be recovered
**Behavior:** Ends the message loop immediately, no retry possible
**Use Case:** Fatal errors, cancelled operations, system failures

**Handling in agent.py (Lines 457-479):**
```python
def handle_critical_exception(self, exception: Exception):
    if isinstance(exception, HandledException):
        raise exception  # Re-raise to kill the loop
    else:
        # Format error, log it, convert to HandledException
        error_text = errors.error_text(exception)
        error_message = errors.format_error(exception)
        self.context.log.log(type="error", heading="Error",
                           content=error_message, kvps={"text": error_text})
        raise HandledException(exception)  # End the loop
```

### Why This Design Works

1. **Clear separation of concerns** - Each tier has a distinct purpose
2. **LLM self-repair** - RepairableException enables autonomous error recovery
3. **Graceful degradation** - System can continue operation despite partial failures
4. **Observability** - All errors are logged with context for debugging

---

## Exception Hierarchy Design

### DSPy-Compatible Exception Classes

```python
"""error_handling/exceptions.py - Exception hierarchy for DSPy-based agents."""

from typing import Optional, Dict, Any
from datetime import datetime
import uuid
from .models import ErrorContext


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


class InterventionException(AgentException):
    """Tier 1: User intervention required.

    Raised when user interrupts agent execution to provide
    new instructions or guidance. Agent should restart
    gracefully with user's input.

    Examples:
    - User clicks "Stop" button during execution
    - User provides correction mid-stream
    - User changes priorities during multi-step task
    """

    def __init__(self, message: str = "User intervention requested"):
        super().__init__(message)


class RepairableException(AgentException):
    """Tier 2: Self-repairable error.

    Raised when an error occurs that the LLM can potentially
    fix through reasoning. Error context is added to the
    conversation history, allowing the LLM to adjust its
    approach and retry.

    Examples:
    - API call with invalid parameters → LLM adjusts parameters
    - Missing required field → LLM provides the field
    - Rate limit hit → LLM waits and retries
    - Validation error → LLM fixes the data format
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
            original_exception=str(original_exception) if original_exception else None
        )
        super().__init__(message, error_ctx)
        self.original_exception = original_exception


# Specific repairable exceptions for common scenarios

class APICallException(RepairableException):
    """API call failed - LLM can adjust parameters or retry."""
    pass


class ValidationException(RepairableException):
    """Data validation failed - LLM can fix the data format."""
    pass


class RateLimitException(RepairableException):
    """Rate limit hit - LLM can wait and retry."""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(
            message,
            repair_hint=f"Wait {retry_after} seconds before retrying" if retry_after else None
        )
        self.retry_after = retry_after


class MissingDataException(RepairableException):
    """Required data missing - LLM can provide it or find alternative."""
    pass
```

### Key Design Decisions

1. **Inherits from Exception** - Standard Python exception handling works
2. **Pydantic ErrorContext** - All error data is validated
3. **DSPy-compatible** - No special requirements, works with any DSPy module
4. **Repair hints** - Guide the LLM toward correct solutions
5. **Attempt tracking** - Prevent infinite retry loops

---

## Pydantic Models for Error States

### ErrorContext Model

```python
"""error_handling/models.py - Pydantic models for error states."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import uuid


class ErrorSeverity(str, Enum):
    """Error severity levels."""
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
                "timestamp": "2025-10-30T12:34:56.789Z",
                "exception_type": "APICallException",
                "error_message": "Clearbit API returned 422: Invalid email format",
                "inputs_attempted": {
                    "email": "invalid-email",
                    "timeout": 10
                },
                "repair_hint": "Email must be in format user@domain.com",
                "repair_attempts": 1,
                "max_repair_attempts": 3,
                "agent_name": "ResearchAgent",
                "operation_name": "clearbit_person_lookup"
            }
        }


class RecoveryAction(BaseModel):
    """LLM's decision on how to recover from error.

    Generated by DSPy ErrorAnalysis module after analyzing
    the error context.
    """

    action_type: str = Field(
        ...,
        description="Type of recovery action",
        pattern="^(retry|modify_inputs|skip|escalate|alternative_approach)$"
    )

    reasoning: str = Field(
        ...,
        description="LLM's reasoning for this action"
    )

    modified_inputs: Optional[Dict[str, Any]] = Field(
        None,
        description="Corrected inputs for retry"
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="LLM's confidence in this recovery (0-1)"
    )

    wait_seconds: Optional[int] = Field(
        None,
        description="Seconds to wait before retry (for rate limits)"
    )

    alternative_approach: Optional[str] = Field(
        None,
        description="Alternative method to try"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "action_type": "modify_inputs",
                "reasoning": "Email format is invalid. Should use proper email format.",
                "modified_inputs": {
                    "email": "john@example.com",
                    "timeout": 10
                },
                "confidence": 0.95
            }
        }


class ErrorRecoveryResult(BaseModel):
    """Result of error recovery attempt.

    Captures the outcome of attempting to recover from
    a RepairableException using DSPy reasoning.
    """

    success: bool = Field(..., description="Whether recovery succeeded")

    result: Optional[Any] = Field(
        None,
        description="Successful result (if success=True)"
    )

    error_context: Optional[ErrorContext] = Field(
        None,
        description="Error context (if success=False)"
    )

    recovery_action: Optional[RecoveryAction] = Field(
        None,
        description="Action taken by LLM"
    )

    attempts_made: int = Field(..., ge=1)

    final_error: Optional[str] = Field(
        None,
        description="Final error if recovery failed"
    )

    recovery_path: List[str] = Field(
        default_factory=list,
        description="Sequence of recovery actions attempted"
    )

    total_duration_ms: int = Field(
        ...,
        description="Total time spent on recovery"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "result": {"name": "John Doe", "company": "Acme Corp"},
                "recovery_action": {
                    "action_type": "modify_inputs",
                    "reasoning": "Fixed email format",
                    "confidence": 0.95
                },
                "attempts_made": 2,
                "recovery_path": [
                    "Initial attempt failed: Invalid email",
                    "Modified inputs: Fixed email format",
                    "Retry succeeded"
                ],
                "total_duration_ms": 1250
            }
        }


class ErrorLog(BaseModel):
    """Structured error log entry for observability.

    Used for error analytics, debugging, and monitoring.
    """

    log_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    error_context: ErrorContext
    recovery_result: Optional[ErrorRecoveryResult] = None

    agent_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional agent context (user_id, session_id, etc.)"
    )

    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorization and filtering"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "log_id": "660e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2025-10-30T12:35:00.000Z",
                "error_context": {
                    "error_id": "550e8400-e29b-41d4-a716-446655440000",
                    "exception_type": "APICallException",
                    "error_message": "API call failed"
                },
                "agent_context": {
                    "user_id": "user_123",
                    "session_id": "session_456"
                },
                "tags": ["api_error", "clearbit", "recovered"]
            }
        }
```

### Benefits of Pydantic Models

1. **Type safety** - All fields are validated at runtime
2. **Documentation** - Models serve as API documentation
3. **Serialization** - Easy conversion to JSON for logging
4. **IDE support** - Autocomplete and type hints
5. **Testing** - Easy to create mock error contexts

---

## DSPy Error Recovery Implementation

### DSPy Signatures for Error Analysis

```python
"""error_handling/dspy_modules.py - DSPy modules for error recovery."""

import dspy
from typing import Optional, Dict, Any
import json


class ErrorAnalysis(dspy.Signature):
    """Analyze an error and determine recovery strategy.

    Given an error that occurred during agent execution,
    analyze the root cause and recommend how to fix it.
    This enables self-repair through LLM reasoning.
    """

    # Error information
    error_message: str = dspy.InputField(
        desc="The error message that occurred"
    )
    exception_type: str = dspy.InputField(
        desc="Type of exception (e.g., APICallException, ValidationException)"
    )
    failed_inputs: str = dspy.InputField(
        desc="The inputs that caused the error (JSON format)"
    )

    # Context
    operation_context: str = dspy.InputField(
        desc="What operation was being attempted when error occurred"
    )
    repair_hint: str = dspy.InputField(
        desc="Optional hint about how to fix the error"
    )
    previous_attempts: str = dspy.InputField(
        desc="Previous repair attempts and their results"
    )

    # Analysis output
    root_cause: str = dspy.OutputField(
        desc="Root cause analysis: Why did this error occur?"
    )
    recovery_strategy: str = dspy.OutputField(
        desc="How to recover: retry, modify_inputs, skip, escalate, or alternative_approach"
    )
    reasoning: str = dspy.OutputField(
        desc="Detailed reasoning for the recovery strategy"
    )
    modified_inputs: str = dspy.OutputField(
        desc="Corrected inputs as JSON (if recovery_strategy=modify_inputs)"
    )
    confidence: float = dspy.OutputField(
        desc="Confidence in recovery strategy (0.0 to 1.0)"
    )


class ErrorRecoveryPlanning(dspy.Signature):
    """Plan error recovery across multiple attempts.

    When initial recovery fails, plan the next approach
    considering all previous attempts.
    """

    # History
    error_history: str = dspy.InputField(
        desc="Sequence of errors and recovery attempts so far"
    )
    remaining_attempts: int = dspy.InputField(
        desc="Number of retry attempts remaining"
    )

    # Context
    original_goal: str = dspy.InputField(
        desc="What we were originally trying to accomplish"
    )
    constraints: str = dspy.InputField(
        desc="Any constraints or limitations on recovery"
    )

    # Planning output
    next_approach: str = dspy.OutputField(
        desc="Next recovery approach to try"
    )
    fallback_plan: str = dspy.OutputField(
        desc="Fallback plan if next approach also fails"
    )
    should_continue: bool = dspy.OutputField(
        desc="Whether to continue trying or give up"
    )
```

### Error Recovery Orchestrator

```python
"""error_handling/recovery.py - DSPy-based error recovery orchestrator."""

import dspy
import logging
import time
from typing import Optional, Any, Dict, Callable, TypeVar
import json

from .models import (
    ErrorContext,
    RecoveryAction,
    ErrorRecoveryResult,
    ErrorLog
)
from .exceptions import (
    RepairableException,
    HandledException,
    InterventionException
)
from .dspy_modules import ErrorAnalysis, ErrorRecoveryPlanning

logger = logging.getLogger(__name__)

T = TypeVar('T')


class DSPyErrorRecovery:
    """Orchestrates error recovery using DSPy reasoning.

    This class wraps any operation with intelligent error recovery:
    1. Catches RepairableException
    2. Uses DSPy to analyze error and plan recovery
    3. Retries with modified inputs
    4. Returns ErrorRecoveryResult

    Compatible with both sync and async operations.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        enable_logging: bool = True
    ):
        self.max_attempts = max_attempts
        self.enable_logging = enable_logging

        # Initialize DSPy modules
        self.error_analyzer = dspy.ChainOfThought(ErrorAnalysis)
        self.recovery_planner = dspy.ChainOfThought(ErrorRecoveryPlanning)

        logger.info(f"DSPyErrorRecovery initialized (max_attempts={max_attempts})")

    async def execute_with_recovery(
        self,
        operation: Callable[..., Any],
        operation_name: str,
        operation_context: str,
        *args,
        **kwargs
    ) -> ErrorRecoveryResult:
        """Execute operation with automatic error recovery.

        Args:
            operation: Function to execute
            operation_name: Name for logging
            operation_context: What we're trying to accomplish
            *args, **kwargs: Arguments for operation

        Returns:
            ErrorRecoveryResult with outcome
        """
        start_time = time.time()
        recovery_path = []
        attempts = 0

        while attempts < self.max_attempts:
            attempts += 1

            try:
                # Attempt the operation
                logger.info(f"Attempt {attempts}/{self.max_attempts}: {operation_name}")
                result = await operation(*args, **kwargs) if self._is_async(operation) else operation(*args, **kwargs)

                # Success!
                duration_ms = int((time.time() - start_time) * 1000)
                recovery_path.append(f"Attempt {attempts}: Success")

                return ErrorRecoveryResult(
                    success=True,
                    result=result,
                    attempts_made=attempts,
                    recovery_path=recovery_path,
                    total_duration_ms=duration_ms
                )

            except RepairableException as e:
                logger.warning(f"RepairableException on attempt {attempts}: {e.message}")
                recovery_path.append(f"Attempt {attempts}: {e.message}")

                # Check if we can retry
                if attempts >= self.max_attempts:
                    logger.error(f"Max attempts ({self.max_attempts}) exceeded")
                    duration_ms = int((time.time() - start_time) * 1000)
                    return ErrorRecoveryResult(
                        success=False,
                        error_context=e.error_context,
                        attempts_made=attempts,
                        final_error=f"Max attempts exceeded: {e.message}",
                        recovery_path=recovery_path,
                        total_duration_ms=duration_ms
                    )

                # Analyze error and plan recovery
                recovery_action = await self._analyze_and_recover(
                    e,
                    operation_context,
                    recovery_path,
                    attempts
                )

                # Check if we should continue
                if not recovery_action or recovery_action.action_type == "escalate":
                    logger.error("Recovery strategy: escalate to HandledException")
                    raise HandledException(
                        f"Error escalated after {attempts} attempts: {e.message}",
                        original_exception=e
                    )

                # Apply recovery action
                if recovery_action.action_type == "modify_inputs":
                    # Update kwargs with modified inputs
                    if recovery_action.modified_inputs:
                        kwargs.update(recovery_action.modified_inputs)
                        logger.info(f"Modified inputs: {recovery_action.modified_inputs}")

                elif recovery_action.action_type == "skip":
                    # Return partial success with None result
                    logger.info("Recovery strategy: skip operation")
                    duration_ms = int((time.time() - start_time) * 1000)
                    return ErrorRecoveryResult(
                        success=True,  # Graceful degradation
                        result=None,
                        recovery_action=recovery_action,
                        attempts_made=attempts,
                        recovery_path=recovery_path,
                        total_duration_ms=duration_ms
                    )

                # Wait if needed (rate limits)
                if recovery_action.wait_seconds:
                    logger.info(f"Waiting {recovery_action.wait_seconds}s before retry")
                    await asyncio.sleep(recovery_action.wait_seconds)

                # Loop continues to retry

            except InterventionException:
                # User interrupted - re-raise immediately
                raise

            except Exception as e:
                # Non-repairable exception
                logger.error(f"Non-repairable exception: {type(e).__name__}: {str(e)}")
                raise HandledException(
                    f"Critical error in {operation_name}: {str(e)}",
                    original_exception=e
                )

        # Should never reach here, but just in case
        duration_ms = int((time.time() - start_time) * 1000)
        return ErrorRecoveryResult(
            success=False,
            attempts_made=attempts,
            final_error="Unexpected exit from recovery loop",
            recovery_path=recovery_path,
            total_duration_ms=duration_ms
        )

    async def _analyze_and_recover(
        self,
        exception: RepairableException,
        operation_context: str,
        recovery_path: list,
        attempt: int
    ) -> Optional[RecoveryAction]:
        """Use DSPy to analyze error and determine recovery."""

        logger.info("Analyzing error with DSPy...")

        # Prepare inputs for DSPy
        error_ctx = exception.error_context
        failed_inputs_json = json.dumps(error_ctx.inputs_attempted, indent=2)
        previous_attempts_str = "\n".join(recovery_path)

        # Call DSPy error analyzer
        try:
            analysis = self.error_analyzer(
                error_message=exception.message,
                exception_type=error_ctx.exception_type,
                failed_inputs=failed_inputs_json,
                operation_context=operation_context,
                repair_hint=error_ctx.repair_hint or "No hint provided",
                previous_attempts=previous_attempts_str or "First attempt"
            )

            # Parse DSPy output into RecoveryAction
            recovery_action = RecoveryAction(
                action_type=analysis.recovery_strategy,
                reasoning=analysis.reasoning,
                modified_inputs=json.loads(analysis.modified_inputs) if analysis.modified_inputs else None,
                confidence=float(analysis.confidence)
            )

            logger.info(f"Recovery strategy: {recovery_action.action_type}")
            logger.info(f"Reasoning: {recovery_action.reasoning}")
            logger.info(f"Confidence: {recovery_action.confidence:.2f}")

            return recovery_action

        except Exception as e:
            logger.error(f"Error analysis failed: {str(e)}")
            return None

    def _is_async(self, func: Callable) -> bool:
        """Check if function is async."""
        import asyncio
        return asyncio.iscoroutinefunction(func)


# Decorator for easy error recovery

def with_retry_logic(
    operation_name: str,
    operation_context: str,
    max_attempts: int = 3
):
    """Decorator to add automatic error recovery to any function.

    Usage:
        @with_retry_logic(
            operation_name="clearbit_lookup",
            operation_context="Enriching lead with Clearbit API",
            max_attempts=3
        )
        async def enrich_lead(email: str) -> Dict:
            # ... API call that might fail ...
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., ErrorRecoveryResult]:
        recovery_engine = DSPyErrorRecovery(max_attempts=max_attempts)

        async def wrapper(*args, **kwargs) -> ErrorRecoveryResult:
            return await recovery_engine.execute_with_recovery(
                func,
                operation_name,
                operation_context,
                *args,
                **kwargs
            )

        return wrapper
    return decorator
```

### Error Recovery Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Execute Operation                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
                   ┌─────────┐
                   │ Success?│
                   └────┬────┘
                        │
           ┌────────────┴────────────┐
           │ YES                     │ NO
           ▼                         ▼
    ┌─────────────┐          ┌──────────────┐
    │Return Result│          │Exception Type?│
    └─────────────┘          └──────┬────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
       ┌────────────┐     ┌──────────────┐      ┌──────────────┐
       │Intervention│     │  Repairable  │      │ Other/Fatal  │
       │ Exception  │     │  Exception   │      │  Exception   │
       └─────┬──────┘     └──────┬───────┘      └──────┬───────┘
             │                   │                      │
             ▼                   ▼                      ▼
       ┌───────────┐      ┌────────────┐      ┌────────────────┐
       │ Re-raise  │      │Attempts < │      │Convert to      │
       │ Immediate │      │   Max?     │      │HandledException│
       └───────────┘      └─────┬──────┘      └────────┬───────┘
                                │                      │
                     ┌──────────┴──────────┐          │
                     │ YES                 │ NO       │
                     ▼                     ▼          ▼
              ┌────────────┐        ┌──────────┐  ┌────────┐
              │DSPy Analyze│        │Max Retries│  │Re-raise│
              │   Error    │        │ Exceeded  │  │        │
              └─────┬──────┘        └─────┬─────┘  └────────┘
                    │                     │
                    ▼                     │
           ┌─────────────────┐           │
           │ Recovery Action │           │
           └────────┬─────────┘           │
                    │                     │
      ┌─────────────┼─────────────┐      │
      │             │             │      │
      ▼             ▼             ▼      │
┌──────────┐ ┌──────────┐ ┌───────────┐ │
│ Modify   │ │   Skip   │ │ Escalate  │ │
│ Inputs   │ │ Graceful │ │ To Fatal  │ │
└────┬─────┘ └────┬─────┘ └─────┬─────┘ │
     │            │              │       │
     │            ▼              ▼       │
     │     ┌──────────────┐ ┌────────┐  │
     │     │Return Partial│ │Re-raise│  │
     │     │   Success    │ │        │  │
     │     └──────────────┘ └────────┘  │
     │                                   │
     └────────────►Wait if needed        │
                          │               │
                          ▼               │
                    ┌───────────┐         │
                    │  Retry    │         │
                    │ Operation │         │
                    └─────┬─────┘         │
                          │               │
                          └───────────────┘
                      (Loop back to Execute)
```

---

## Integration with hume-dspy-agent

### Step 1: Add Error Handling Module

Create new module structure:

```
hume-dspy-agent/
├── error_handling/
│   ├── __init__.py          # Public API exports
│   ├── exceptions.py        # 3-tier exception hierarchy
│   ├── models.py           # Pydantic error models
│   ├── dspy_modules.py     # DSPy signatures for recovery
│   ├── recovery.py         # Error recovery orchestrator
│   └── logging.py          # Structured error logging
```

### Step 2: Update InboundAgent

```python
"""agents/inbound_agent.py - Updated with error recovery."""

import dspy
from typing import Optional
import time

from models import Lead, QualificationResult
from error_handling import (
    RepairableException,
    HandledException,
    DSPyErrorRecovery,
    with_retry_logic
)

class InboundAgent(dspy.Module):
    """Inbound lead qualification with error recovery."""

    def __init__(self):
        super().__init__()

        # Initialize DSPy modules
        self.analyze_business = dspy.ChainOfThought(AnalyzeBusinessFit)
        self.analyze_engagement = dspy.ChainOfThought(AnalyzeEngagement)
        self.determine_actions = dspy.ChainOfThought(DetermineNextActions)

        # Initialize error recovery
        self.error_recovery = DSPyErrorRecovery(max_attempts=3)

    def forward(self, lead: Lead) -> QualificationResult:
        """Process and qualify a lead with error recovery."""
        start_time = time.time()

        try:
            # Step 1: Analyze business fit (with recovery)
            business_fit = self._analyze_business_fit_with_recovery(lead)

            # Step 2: Analyze engagement (with recovery)
            engagement = self._analyze_engagement_with_recovery(lead)

            # Step 3: Calculate criteria and determine tier
            criteria = self._calculate_criteria(lead, business_fit, engagement)
            total_score = criteria.calculate_total()
            tier = self._determine_tier(total_score)

            # Step 4: Determine next actions (with recovery)
            actions_result = self._determine_actions_with_recovery(
                total_score, tier, lead
            )

            # ... rest of qualification logic ...

        except HandledException as e:
            # Critical error - log and return error result
            logger.error(f"Critical error qualifying lead {lead.id}: {e.message}")
            return self._create_error_result(lead, e)

    def _analyze_business_fit_with_recovery(self, lead: Lead) -> Dict[str, Any]:
        """Analyze business fit with automatic error recovery."""

        async def analyze():
            try:
                result = self.analyze_business(
                    company_context=get_company_context_for_qualification(),
                    business_size=lead.get_field('business_size') or "Unknown",
                    patient_volume=lead.get_field('patient_volume') or "Unknown",
                    company=lead.get_field('company') or "Unknown",
                    industry="Healthcare"
                )
                return {
                    "score": result.fit_score,
                    "reasoning": result.reasoning
                }
            except Exception as e:
                # Wrap non-repairable errors
                raise RepairableException(
                    f"Business fit analysis failed: {str(e)}",
                    inputs={
                        "business_size": lead.get_field('business_size'),
                        "patient_volume": lead.get_field('patient_volume')
                    },
                    repair_hint="Check if lead has required fields for analysis"
                )

        # Execute with recovery
        recovery_result = await self.error_recovery.execute_with_recovery(
            analyze,
            operation_name="analyze_business_fit",
            operation_context=f"Analyzing business fit for lead {lead.id}"
        )

        if recovery_result.success:
            return recovery_result.result
        else:
            # Graceful degradation - return default values
            logger.warning(f"Business fit analysis failed, using defaults")
            return {
                "score": 25,  # Neutral score
                "reasoning": "Analysis failed - using default neutral score"
            }

    def _create_error_result(self, lead: Lead, error: HandledException) -> QualificationResult:
        """Create error qualification result for failed processing."""
        return QualificationResult(
            is_qualified=False,
            score=0,
            tier=LeadTier.UNQUALIFIED,
            reasoning=f"Qualification failed due to error: {error.message}",
            key_factors=[],
            concerns=["Processing error occurred"],
            error_context=error.error_context
        )
```

### Step 3: Update ResearchAgent

```python
"""agents/research_agent.py - Updated with error recovery."""

import dspy
from typing import Optional, Dict, Any
import httpx

from error_handling import (
    RepairableException,
    APICallException,
    RateLimitException,
    with_retry_logic
)

class ResearchAgent(dspy.Module):
    """Research agent with error recovery."""

    def __init__(self):
        super().__init__()
        self.plan_research = dspy.ChainOfThought(ResearchPlanning)
        self.synthesize_findings = dspy.ChainOfThought(ResearchSynthesis)
        self.clearbit_api_key = os.getenv("CLEARBIT_API_KEY")

    @with_retry_logic(
        operation_name="clearbit_person_lookup",
        operation_context="Enriching person data via Clearbit API",
        max_attempts=3
    )
    async def _clearbit_person_lookup(self, email: str) -> Optional[Dict[str, Any]]:
        """Look up person via Clearbit with automatic error recovery."""

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://person.clearbit.com/v2/combined/find?email={email}",
                    auth=(self.clearbit_api_key, ""),
                    timeout=10.0
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 422:
                    # Validation error - repairable
                    raise RepairableException(
                        f"Invalid email format: {email}",
                        inputs={"email": email},
                        repair_hint="Email must be in format user@domain.com"
                    )
                elif response.status_code == 429:
                    # Rate limit - repairable with wait
                    retry_after = int(response.headers.get("Retry-After", 60))
                    raise RateLimitException(
                        "Clearbit rate limit exceeded",
                        retry_after=retry_after
                    )
                else:
                    # API error - repairable
                    raise APICallException(
                        f"Clearbit API error {response.status_code}",
                        inputs={"email": email},
                        repair_hint=f"API returned: {response.text}"
                    )

        except httpx.TimeoutException:
            raise APICallException(
                "Clearbit API timeout",
                inputs={"email": email},
                repair_hint="Try increasing timeout or check network"
            )
        except httpx.NetworkError as e:
            raise APICallException(
                f"Network error calling Clearbit: {str(e)}",
                inputs={"email": email},
                repair_hint="Check internet connection and API endpoint"
            )

    async def research_person(
        self,
        name: Optional[str],
        email: Optional[str],
        company: Optional[str] = None
    ) -> PersonProfile:
        """Research person with error recovery and graceful degradation."""

        profile_data = {
            "name": name or "Unknown",
            "email": email,
            "company": company
        }

        # Try Clearbit enrichment with error recovery
        if email and self.clearbit_api_key:
            recovery_result = await self._clearbit_person_lookup(email)

            if recovery_result.success and recovery_result.result:
                profile_data.update(recovery_result.result)
                logger.info("✅ Clearbit enrichment successful")
            else:
                logger.warning(f"⚠️ Clearbit failed after {recovery_result.attempts_made} attempts")
                # Continue with partial data - graceful degradation

        # Continue with other enrichment sources...
        # Each wrapped with error recovery

        return PersonProfile(**profile_data)
```

### Step 4: Update Configuration

```python
"""config/settings.py - Add error recovery configuration."""

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ... existing settings ...

    # Error recovery configuration
    error_recovery_enabled: bool = True
    error_recovery_max_attempts: int = 3
    error_recovery_log_level: str = "INFO"
    error_recovery_log_to_file: bool = True
    error_recovery_log_path: str = "logs/error_recovery.jsonl"

    # Error handling by agent
    inbound_agent_max_retries: int = 3
    research_agent_max_retries: int = 3
    strategy_agent_max_retries: int = 2

    # API-specific settings
    api_timeout_seconds: int = 30
    api_retry_on_timeout: bool = True
    api_rate_limit_retry: bool = True
    api_rate_limit_max_wait: int = 300  # 5 minutes max wait

settings = Settings()
```

---

## Code Examples

### Example 1: Basic RepairableException Usage

```python
"""Example: Using RepairableException for API validation errors."""

from error_handling import RepairableException
import dspy

class LeadEnrichment(dspy.Module):
    def forward(self, email: str) -> Dict:
        # Validate email before API call
        if not self._is_valid_email(email):
            raise RepairableException(
                f"Invalid email format: {email}",
                inputs={"email": email},
                repair_hint="Email must match pattern: user@domain.com"
            )

        # Make API call
        return self._call_enrichment_api(email)
```

### Example 2: Error Recovery with DSPy

```python
"""Example: Automatic error recovery with DSPy reasoning."""

from error_handling import DSPyErrorRecovery, RepairableException

async def enrich_lead_with_recovery(lead_id: str, email: str):
    """Enrich lead with automatic error recovery."""

    recovery = DSPyErrorRecovery(max_attempts=3)

    async def enrich_operation(email: str):
        if not validate_email(email):
            raise RepairableException(
                "Invalid email",
                inputs={"email": email},
                repair_hint="Fix email format"
            )
        return await api_call(email)

    result = await recovery.execute_with_recovery(
        enrich_operation,
        operation_name="lead_enrichment",
        operation_context=f"Enriching lead {lead_id}",
        email=email
    )

    if result.success:
        logger.info(f"✅ Enrichment succeeded after {result.attempts_made} attempts")
        return result.result
    else:
        logger.error(f"❌ Enrichment failed: {result.final_error}")
        return None
```

### Example 3: Using the Decorator

```python
"""Example: Decorator for automatic error recovery."""

from error_handling import with_retry_logic

@with_retry_logic(
    operation_name="clearbit_lookup",
    operation_context="Enriching lead with Clearbit",
    max_attempts=3
)
async def enrich_with_clearbit(email: str) -> Dict:
    """Enrich lead via Clearbit API.

    Automatically retries on RepairableException.
    DSPy analyzes errors and adjusts parameters.
    """
    if not email or '@' not in email:
        raise RepairableException(
            f"Invalid email: {email}",
            inputs={"email": email},
            repair_hint="Email must contain @ symbol"
        )

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://person.clearbit.com/v2/combined/find?email={email}",
            auth=(CLEARBIT_KEY, ""),
            timeout=10
        )

        if response.status_code == 422:
            raise RepairableException(
                "Clearbit validation error",
                inputs={"email": email},
                repair_hint=response.json().get("error", {}).get("message")
            )

        return response.json()

# Usage
result = await enrich_with_clearbit("john@example.com")
if result.success:
    print(f"Enrichment data: {result.result}")
else:
    print(f"Failed after {result.attempts_made} attempts")
```

### Example 4: Graceful Degradation

```python
"""Example: Graceful degradation when recovery fails."""

from error_handling import HandledException

async def qualify_lead(lead: Lead) -> QualificationResult:
    """Qualify lead with graceful degradation."""

    try:
        # Try to enrich lead data
        enrichment = await enrich_lead_with_recovery(lead.id, lead.email)

        # Qualification with enrichment
        return await qualify_with_enrichment(lead, enrichment)

    except HandledException as e:
        # Enrichment failed - fall back to basic qualification
        logger.warning(f"Enrichment failed, using basic qualification: {e.message}")
        return await qualify_without_enrichment(lead)

async def qualify_with_enrichment(lead: Lead, enrichment: Dict) -> QualificationResult:
    """Full qualification with enrichment data."""
    # Use enrichment data for better scoring
    pass

async def qualify_without_enrichment(lead: Lead) -> QualificationResult:
    """Basic qualification without enrichment."""
    # Use only form data, lower confidence
    pass
```

### Example 5: Custom Error Recovery Logic

```python
"""Example: Custom recovery logic for specific scenarios."""

from error_handling import ErrorAnalysis, RecoveryAction
import dspy

class CustomErrorRecovery:
    """Custom error recovery with domain-specific logic."""

    def __init__(self):
        self.analyzer = dspy.ChainOfThought(ErrorAnalysis)

    async def recover_api_error(
        self,
        error: RepairableException,
        operation: str
    ) -> RecoveryAction:
        """Custom recovery for API errors."""

        # Use DSPy to analyze error
        analysis = self.analyzer(
            error_message=error.message,
            exception_type="APICallException",
            failed_inputs=json.dumps(error.error_context.inputs_attempted),
            operation_context=operation,
            repair_hint=error.repair_hint or "",
            previous_attempts=""
        )

        # Custom logic based on error type
        if "rate limit" in error.message.lower():
            return RecoveryAction(
                action_type="retry",
                reasoning="Rate limit hit - waiting before retry",
                wait_seconds=60,
                confidence=0.9
            )

        elif "timeout" in error.message.lower():
            return RecoveryAction(
                action_type="modify_inputs",
                reasoning="Timeout - increasing timeout duration",
                modified_inputs={"timeout": 30},  # Double the timeout
                confidence=0.8
            )

        elif "validation" in error.message.lower():
            # Use DSPy's suggested fix
            return RecoveryAction(
                action_type="modify_inputs",
                reasoning=analysis.reasoning,
                modified_inputs=json.loads(analysis.modified_inputs),
                confidence=float(analysis.confidence)
            )

        else:
            # Unknown error - escalate
            return RecoveryAction(
                action_type="escalate",
                reasoning="Unknown error type - cannot recover",
                confidence=0.0
            )
```

---

## Testing Strategy

### Unit Tests

```python
"""tests/test_error_handling.py - Unit tests for error handling."""

import pytest
from error_handling import (
    RepairableException,
    HandledException,
    InterventionException,
    DSPyErrorRecovery,
    ErrorContext
)

class TestExceptionHierarchy:
    """Test exception classes."""

    def test_repairable_exception_creation(self):
        """Test creating RepairableException with context."""
        exc = RepairableException(
            "Test error",
            inputs={"param": "value"},
            repair_hint="Fix the param",
            max_attempts=3
        )

        assert exc.message == "Test error"
        assert exc.error_context.inputs_attempted == {"param": "value"}
        assert exc.repair_hint == "Fix the param"
        assert exc.max_attempts == 3
        assert exc.can_retry() == True

    def test_repairable_exception_attempts(self):
        """Test retry attempt tracking."""
        exc = RepairableException("Test", max_attempts=2)

        assert exc.can_retry() == True
        exc.increment_repair_attempt()
        assert exc.can_retry() == True
        exc.increment_repair_attempt()
        assert exc.can_retry() == False

    def test_handled_exception_wraps_original(self):
        """Test HandledException wraps original exception."""
        original = ValueError("Original error")
        handled = HandledException(
            "Handled wrapper",
            original_exception=original
        )

        assert handled.original_exception == original
        assert "Original error" in str(handled.error_context.original_exception)

class TestErrorRecovery:
    """Test DSPy error recovery."""

    @pytest.mark.asyncio
    async def test_successful_operation_no_retry(self):
        """Test successful operation requires no retry."""
        recovery = DSPyErrorRecovery(max_attempts=3)

        async def success_operation():
            return {"result": "success"}

        result = await recovery.execute_with_recovery(
            success_operation,
            "test_op",
            "Testing success"
        )

        assert result.success == True
        assert result.result == {"result": "success"}
        assert result.attempts_made == 1

    @pytest.mark.asyncio
    async def test_repairable_exception_retry(self):
        """Test RepairableException triggers retry."""
        recovery = DSPyErrorRecovery(max_attempts=3)

        attempts = [0]

        async def failing_operation():
            attempts[0] += 1
            if attempts[0] < 2:
                raise RepairableException(
                    "First attempt failed",
                    inputs={"attempt": attempts[0]}
                )
            return {"result": "success"}

        result = await recovery.execute_with_recovery(
            failing_operation,
            "test_op",
            "Testing retry"
        )

        assert result.success == True
        assert result.attempts_made == 2

    @pytest.mark.asyncio
    async def test_max_attempts_exceeded(self):
        """Test max attempts exceeded returns failure."""
        recovery = DSPyErrorRecovery(max_attempts=2)

        async def always_fails():
            raise RepairableException(
                "Always fails",
                inputs={}
            )

        result = await recovery.execute_with_recovery(
            always_fails,
            "test_op",
            "Testing max attempts"
        )

        assert result.success == False
        assert result.attempts_made == 2
        assert "Max attempts exceeded" in result.final_error

    @pytest.mark.asyncio
    async def test_intervention_exception_reraise(self):
        """Test InterventionException is re-raised immediately."""
        recovery = DSPyErrorRecovery(max_attempts=3)

        async def interrupted_operation():
            raise InterventionException("User stopped")

        with pytest.raises(InterventionException):
            await recovery.execute_with_recovery(
                interrupted_operation,
                "test_op",
                "Testing intervention"
            )

    @pytest.mark.asyncio
    async def test_handled_exception_conversion(self):
        """Test non-repairable exceptions convert to HandledException."""
        recovery = DSPyErrorRecovery(max_attempts=3)

        async def fatal_error():
            raise ValueError("Fatal error")

        with pytest.raises(HandledException) as exc_info:
            await recovery.execute_with_recovery(
                fatal_error,
                "test_op",
                "Testing fatal error"
            )

        assert "Fatal error" in str(exc_info.value)
```

### Integration Tests

```python
"""tests/test_integration.py - Integration tests."""

import pytest
from agents import InboundAgent
from models import Lead
from error_handling import HandledException

class TestInboundAgentErrorHandling:
    """Test InboundAgent with error handling."""

    @pytest.mark.asyncio
    async def test_qualification_with_api_failure(self):
        """Test lead qualification handles API failures gracefully."""
        agent = InboundAgent()

        # Create lead
        lead = Lead(
            id="test_123",
            email="john@example.com",
            phone="+1234567890",
            typeform_response={"business_size": "Large"}
        )

        # Mock API to fail first, then succeed
        with patch.object(agent, '_clearbit_person_lookup') as mock_api:
            mock_api.side_effect = [
                RepairableException("API timeout", inputs={}),
                {"name": "John Doe", "company": "Acme"}
            ]

            # Qualify lead - should recover from API failure
            result = agent.forward(lead)

            assert result.is_qualified == True
            assert mock_api.call_count == 2  # Retry succeeded

    @pytest.mark.asyncio
    async def test_qualification_with_max_retries(self):
        """Test lead qualification handles max retries gracefully."""
        agent = InboundAgent()

        lead = Lead(
            id="test_456",
            email="john@example.com",
            typeform_response={"business_size": "Large"}
        )

        # Mock API to always fail
        with patch.object(agent, '_clearbit_person_lookup') as mock_api:
            mock_api.side_effect = RepairableException("Always fails", inputs={})

            # Should not raise, should degrade gracefully
            result = agent.forward(lead)

            assert mock_api.call_count == 3  # Max attempts
            # Should still return result, just without enrichment
            assert result.is_qualified in [True, False]
```

---

## Configuration

### Environment Variables

```bash
# Error Recovery Configuration
ERROR_RECOVERY_ENABLED=true
ERROR_RECOVERY_MAX_ATTEMPTS=3
ERROR_RECOVERY_LOG_LEVEL=INFO
ERROR_RECOVERY_LOG_PATH=logs/error_recovery.jsonl

# Agent-specific Retries
INBOUND_AGENT_MAX_RETRIES=3
RESEARCH_AGENT_MAX_RETRIES=3
STRATEGY_AGENT_MAX_RETRIES=2

# API Settings
API_TIMEOUT_SECONDS=30
API_RETRY_ON_TIMEOUT=true
API_RATE_LIMIT_RETRY=true
API_RATE_LIMIT_MAX_WAIT=300
```

### Logging Configuration

```python
"""error_handling/logging.py - Structured error logging."""

import logging
import json
from typing import Optional
from datetime import datetime

from .models import ErrorLog, ErrorContext, ErrorRecoveryResult

class ErrorLogger:
    """Structured logger for error handling."""

    def __init__(self, log_path: str = "logs/error_recovery.jsonl"):
        self.log_path = log_path
        self.logger = logging.getLogger("error_handling")

    def log_error(
        self,
        error_context: ErrorContext,
        recovery_result: Optional[ErrorRecoveryResult] = None,
        agent_context: Optional[dict] = None,
        tags: Optional[list] = None
    ):
        """Log structured error with recovery result."""

        error_log = ErrorLog(
            error_context=error_context,
            recovery_result=recovery_result,
            agent_context=agent_context or {},
            tags=tags or []
        )

        # Write to JSONL file
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(error_log.model_dump()) + '\n')

        # Also log to standard logger
        self.logger.error(
            f"Error: {error_context.error_message}",
            extra={
                "error_id": error_context.error_id,
                "exception_type": error_context.exception_type,
                "recovery_success": recovery_result.success if recovery_result else None
            }
        )
```

---

## Migration Guide

### Phase 1: Add Error Handling Module

1. Create `error_handling/` directory
2. Add exception classes
3. Add Pydantic models
4. Add DSPy modules
5. Add recovery orchestrator

### Phase 2: Update Existing Agents

1. **InboundAgent**: Wrap DSPy calls in error recovery
2. **ResearchAgent**: Replace generic Exception with RepairableException
3. **StrategyAgent**: Add error recovery for planning operations
4. **FollowUpAgent**: Add error recovery for message generation

### Phase 3: Update Configuration

1. Add error recovery settings to `config/settings.py`
2. Add environment variables to `.env`
3. Configure logging paths

### Phase 4: Testing

1. Run unit tests for exception hierarchy
2. Run integration tests for each agent
3. Test error recovery with mock API failures
4. Verify graceful degradation

### Phase 5: Monitoring

1. Set up error log monitoring
2. Create dashboard for error metrics
3. Alert on high error rates
4. Track recovery success rates

---

## Conclusion

This design integrates **agent-zero's proven 3-tier error handling** with **DSPy's reasoning capabilities** while maintaining **Pydantic validation** throughout.

### Key Benefits

1. **Self-repair** - LLM can fix errors through reasoning
2. **Type safety** - Pydantic models ensure data integrity
3. **Observability** - Structured logging for debugging
4. **Graceful degradation** - System continues despite failures
5. **Minimal changes** - Easy to integrate into existing code

### Next Steps

1. Implement error handling module
2. Update InboundAgent and ResearchAgent
3. Add comprehensive tests
4. Deploy and monitor error rates
5. Tune max retry attempts based on production data

---

**Document Version:** 1.0
**Last Updated:** October 30, 2025
**Status:** Ready for Implementation
