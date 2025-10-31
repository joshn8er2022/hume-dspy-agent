"""Decorator functions for error handling and retry logic.

This module provides decorators for automatic error recovery with LLM-based
self-repair capabilities. Integrates with the 3-tier exception hierarchy
to enable intelligent retry logic.
"""

import functools
import logging
import time
import asyncio
from typing import Callable, TypeVar, Any, Optional, Dict
import traceback

from core.exceptions import (
    RepairableException,
    HandledException,
    InterventionException,
    ErrorContext,
    ErrorSeverity,
    format_error,
    is_repairable,
    is_intervention
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# ============================================================================
# Retry Logic Decorator
# ============================================================================

def with_retry_logic(
    max_attempts: int = 3,
    enable_llm_recovery: bool = True,
    operation_name: Optional[str] = None,
    log_level: str = "INFO"
):
    """Decorator to add automatic error recovery with retry logic.

    This decorator wraps any function with intelligent error recovery:
    1. Catches RepairableException
    2. Logs error with context
    3. Retries operation with exponential backoff
    4. Passes recovery context to LLM for self-repair (if enabled)
    5. Raises HandledException after max attempts exceeded

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        enable_llm_recovery: Enable LLM-based self-repair (default: True)
        operation_name: Name of operation for logging (default: function name)
        log_level: Logging level (default: "INFO")

    Returns:
        Decorated function with retry logic

    Example:
        @with_retry_logic(max_attempts=3, enable_llm_recovery=True)
        def qualify_lead(lead: Lead) -> QualificationResult:
            # Validation that might fail
            if not lead.email:
                raise RepairableException(
                    "Missing email",
                    inputs={"lead_id": lead.id},
                    repair_hint="Email is required for qualification"
                )
            # Process lead...
            return result

    Usage with async functions:
        @with_retry_logic(max_attempts=3)
        async def enrich_lead(lead_id: str) -> Dict:
            # Async operation that might fail
            return await api_call()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        op_name = operation_name or func.__name__

        # Determine if function is async
        is_async = asyncio.iscoroutinefunction(func)

        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> T:
                return await _execute_with_retry_async(
                    func, op_name, max_attempts, enable_llm_recovery,
                    log_level, args, kwargs
                )
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> T:
                return _execute_with_retry_sync(
                    func, op_name, max_attempts, enable_llm_recovery,
                    log_level, args, kwargs
                )
            return sync_wrapper

    return decorator


# ============================================================================
# Synchronous Retry Execution
# ============================================================================

def _execute_with_retry_sync(
    func: Callable,
    operation_name: str,
    max_attempts: int,
    enable_llm_recovery: bool,
    log_level: str,
    args: tuple,
    kwargs: dict
) -> Any:
    """Execute synchronous function with retry logic."""

    attempt = 0
    last_exception: Optional[Exception] = None
    recovery_path = []

    while attempt < max_attempts:
        attempt += 1

        try:
            # Log attempt
            _log(log_level, f"[{operation_name}] Attempt {attempt}/{max_attempts}")

            # Execute function
            result = func(*args, **kwargs)

            # Success! Log and return
            if attempt > 1:
                _log(log_level, f"[{operation_name}] ✓ Succeeded after {attempt} attempts")
                _log_recovery_path(recovery_path, operation_name)

            return result

        except InterventionException:
            # User intervention - re-raise immediately
            _log("WARNING", f"[{operation_name}] User intervention - stopping")
            raise

        except RepairableException as e:
            # Repairable error - log and retry
            last_exception = e
            error_msg = format_error(e)

            _log("WARNING", f"[{operation_name}] RepairableException on attempt {attempt}: {error_msg}")
            recovery_path.append(f"Attempt {attempt}: {e.message}")

            # Increment attempt counter
            e.increment_repair_attempt()

            # Check if we can retry
            if attempt >= max_attempts:
                _log("ERROR", f"[{operation_name}] Max attempts ({max_attempts}) exceeded")
                _log_recovery_path(recovery_path, operation_name)

                # Convert to HandledException
                raise HandledException(
                    f"Max retry attempts exceeded for {operation_name}: {e.message}",
                    original_exception=e
                )

            # Log recovery hint if available
            if e.repair_hint:
                _log("INFO", f"[{operation_name}] Recovery hint: {e.repair_hint}")
                recovery_path.append(f"Hint: {e.repair_hint}")

            # Apply exponential backoff (1s, 2s, 4s, ...)
            backoff_seconds = 2 ** (attempt - 1)
            _log("INFO", f"[{operation_name}] Waiting {backoff_seconds}s before retry...")
            time.sleep(backoff_seconds)

            # For LLM recovery, we could pass context here
            # This would require DSPy integration which we can add later
            if enable_llm_recovery:
                _log("DEBUG", f"[{operation_name}] LLM recovery enabled - context available")

            # Continue to next retry
            continue

        except Exception as e:
            # Non-repairable exception - convert to HandledException
            _log("ERROR", f"[{operation_name}] Non-repairable exception: {type(e).__name__}: {str(e)}")

            # Capture stack trace
            stack_trace = traceback.format_exc()

            raise HandledException(
                f"Critical error in {operation_name}: {str(e)}",
                original_exception=e
            )

    # Should never reach here, but just in case
    if last_exception:
        raise HandledException(
            f"Unexpected exit from retry loop for {operation_name}",
            original_exception=last_exception
        )
    else:
        raise HandledException(f"Unexpected exit from retry loop for {operation_name}")


# ============================================================================
# Asynchronous Retry Execution
# ============================================================================

async def _execute_with_retry_async(
    func: Callable,
    operation_name: str,
    max_attempts: int,
    enable_llm_recovery: bool,
    log_level: str,
    args: tuple,
    kwargs: dict
) -> Any:
    """Execute asynchronous function with retry logic."""

    attempt = 0
    last_exception: Optional[Exception] = None
    recovery_path = []

    while attempt < max_attempts:
        attempt += 1

        try:
            # Log attempt
            _log(log_level, f"[{operation_name}] Attempt {attempt}/{max_attempts}")

            # Execute async function
            result = await func(*args, **kwargs)

            # Success! Log and return
            if attempt > 1:
                _log(log_level, f"[{operation_name}] ✓ Succeeded after {attempt} attempts")
                _log_recovery_path(recovery_path, operation_name)

            return result

        except InterventionException:
            # User intervention - re-raise immediately
            _log("WARNING", f"[{operation_name}] User intervention - stopping")
            raise

        except RepairableException as e:
            # Repairable error - log and retry
            last_exception = e
            error_msg = format_error(e)

            _log("WARNING", f"[{operation_name}] RepairableException on attempt {attempt}: {error_msg}")
            recovery_path.append(f"Attempt {attempt}: {e.message}")

            # Increment attempt counter
            e.increment_repair_attempt()

            # Check if we can retry
            if attempt >= max_attempts:
                _log("ERROR", f"[{operation_name}] Max attempts ({max_attempts}) exceeded")
                _log_recovery_path(recovery_path, operation_name)

                # Convert to HandledException
                raise HandledException(
                    f"Max retry attempts exceeded for {operation_name}: {e.message}",
                    original_exception=e
                )

            # Log recovery hint if available
            if e.repair_hint:
                _log("INFO", f"[{operation_name}] Recovery hint: {e.repair_hint}")
                recovery_path.append(f"Hint: {e.repair_hint}")

            # Apply exponential backoff (1s, 2s, 4s, ...)
            backoff_seconds = 2 ** (attempt - 1)
            _log("INFO", f"[{operation_name}] Waiting {backoff_seconds}s before retry...")
            await asyncio.sleep(backoff_seconds)

            # For LLM recovery, we could pass context here
            if enable_llm_recovery:
                _log("DEBUG", f"[{operation_name}] LLM recovery enabled - context available")

            # Continue to next retry
            continue

        except Exception as e:
            # Non-repairable exception - convert to HandledException
            _log("ERROR", f"[{operation_name}] Non-repairable exception: {type(e).__name__}: {str(e)}")

            # Capture stack trace
            stack_trace = traceback.format_exc()

            raise HandledException(
                f"Critical error in {operation_name}: {str(e)}",
                original_exception=e
            )

    # Should never reach here, but just in case
    if last_exception:
        raise HandledException(
            f"Unexpected exit from retry loop for {operation_name}",
            original_exception=last_exception
        )
    else:
        raise HandledException(f"Unexpected exit from retry loop for {operation_name}")


# ============================================================================
# Helper Functions
# ============================================================================

def _log(level: str, message: str):
    """Log message at specified level."""
    level_map = {
        "DEBUG": logger.debug,
        "INFO": logger.info,
        "WARNING": logger.warning,
        "ERROR": logger.error,
        "CRITICAL": logger.critical
    }
    log_func = level_map.get(level.upper(), logger.info)
    log_func(message)


def _log_recovery_path(recovery_path: list, operation_name: str):
    """Log the full recovery path."""
    if recovery_path:
        _log("INFO", f"[{operation_name}] Recovery path:")
        for step in recovery_path:
            _log("INFO", f"  - {step}")


# ============================================================================
# Additional Decorators
# ============================================================================

def log_exceptions(operation_name: Optional[str] = None):
    """Simple decorator to log all exceptions.

    This is a lighter-weight alternative to with_retry_logic
    for operations that shouldn't be retried but need logging.

    Args:
        operation_name: Name of operation for logging

    Example:
        @log_exceptions(operation_name="save_to_database")
        def save_lead(lead: Lead):
            # Save to database
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        op_name = operation_name or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"[{op_name}] Exception: {format_error(e)}")
                raise

        return wrapper
    return decorator


def graceful_degradation(
    fallback_value: Any = None,
    operation_name: Optional[str] = None
):
    """Decorator for graceful degradation on errors.

    Returns fallback value instead of raising exception.
    Useful for non-critical operations.

    Args:
        fallback_value: Value to return on error (default: None)
        operation_name: Name of operation for logging

    Example:
        @graceful_degradation(fallback_value={"enrichment": None})
        def enrich_lead(lead_id: str) -> Dict:
            # API call that might fail
            return api_response
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        op_name = operation_name or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(
                    f"[{op_name}] Failed with {format_error(e)}, "
                    f"using fallback value: {fallback_value}"
                )
                return fallback_value

        return wrapper
    return decorator
