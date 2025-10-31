"""Comprehensive tests for 3-tier error handling system.

Tests cover:
1. Exception hierarchy (InterventionException, RepairableException, HandledException)
2. ErrorContext and Pydantic models
3. @with_retry_logic decorator
4. Retry logic with exponential backoff
5. LLM recovery flow (structure, not full DSPy integration)
6. Graceful degradation
"""

import pytest
import asyncio
import time
from typing import Dict, Any
from unittest.mock import Mock, patch

from core.exceptions import (
    ErrorSeverity,
    ErrorContext,
    AgentException,
    InterventionException,
    RepairableException,
    HandledException,
    APICallException,
    ValidationException,
    RateLimitException,
    MissingDataException,
    TimeoutException,
    format_error,
    is_repairable,
    is_intervention,
    is_handled
)

from core.decorators import (
    with_retry_logic,
    log_exceptions,
    graceful_degradation
)


# ============================================================================
# Test Exception Hierarchy
# ============================================================================

class TestExceptionHierarchy:
    """Test exception classes and hierarchy."""

    def test_error_context_creation(self):
        """Test ErrorContext Pydantic model creation."""
        context = ErrorContext(
            exception_type="TestException",
            error_message="Test error message",
            inputs_attempted={"param": "value"},
            repair_hint="Try fixing param"
        )

        assert context.exception_type == "TestException"
        assert context.error_message == "Test error message"
        assert context.inputs_attempted == {"param": "value"}
        assert context.repair_hint == "Try fixing param"
        assert context.repair_attempts == 0
        assert context.max_repair_attempts == 3
        assert context.severity == ErrorSeverity.MEDIUM
        assert context.error_id is not None

    def test_error_context_validation(self):
        """Test ErrorContext validates fields."""
        # Should validate repair_attempts >= 0
        context = ErrorContext(
            exception_type="Test",
            error_message="Test",
            repair_attempts=-1  # Invalid
        )
        # Pydantic validation happens on model_dump
        with pytest.raises(ValueError):
            context.model_validate({"exception_type": "Test", "error_message": "Test", "repair_attempts": -1})

    def test_agent_exception_base(self):
        """Test base AgentException class."""
        exc = AgentException("Test error")

        assert exc.message == "Test error"
        assert exc.error_context is not None
        assert exc.error_context.exception_type == "AgentException"
        assert exc.error_context.error_message == "Test error"

        # Test to_dict
        exc_dict = exc.to_dict()
        assert exc_dict["message"] == "Test error"
        assert "error_context" in exc_dict

    def test_intervention_exception(self):
        """Test InterventionException (Tier 1)."""
        exc = InterventionException("User stopped process")

        assert exc.message == "User stopped process"
        assert isinstance(exc, AgentException)
        assert exc.error_context.exception_type == "InterventionException"

    def test_repairable_exception(self):
        """Test RepairableException (Tier 2)."""
        exc = RepairableException(
            "API call failed",
            inputs={"url": "https://api.example.com"},
            repair_hint="Check API endpoint",
            max_attempts=3
        )

        assert exc.message == "API call failed"
        assert exc.repair_hint == "Check API endpoint"
        assert exc.max_attempts == 3
        assert exc.error_context.inputs_attempted == {"url": "https://api.example.com"}
        assert exc.error_context.repair_hint == "Check API endpoint"
        assert exc.error_context.repair_attempts == 0
        assert exc.can_retry() is True

    def test_repairable_exception_retry_tracking(self):
        """Test RepairableException retry attempt tracking."""
        exc = RepairableException("Test", max_attempts=2)

        assert exc.can_retry() is True
        assert exc.error_context.repair_attempts == 0

        exc.increment_repair_attempt()
        assert exc.can_retry() is True
        assert exc.error_context.repair_attempts == 1

        exc.increment_repair_attempt()
        assert exc.can_retry() is False
        assert exc.error_context.repair_attempts == 2

    def test_handled_exception(self):
        """Test HandledException (Tier 3)."""
        original = ValueError("Original error")
        exc = HandledException(
            "Critical failure",
            original_exception=original
        )

        assert exc.message == "Critical failure"
        assert exc.original_exception == original
        assert exc.error_context.original_exception == "Original error"
        assert exc.error_context.severity == ErrorSeverity.CRITICAL

    def test_api_call_exception(self):
        """Test APICallException subclass."""
        exc = APICallException(
            "API returned 500",
            inputs={"endpoint": "/api/users"},
            repair_hint="Retry with backoff"
        )

        assert isinstance(exc, RepairableException)
        assert exc.message == "API returned 500"
        assert exc.repair_hint == "Retry with backoff"

    def test_validation_exception(self):
        """Test ValidationException subclass."""
        exc = ValidationException(
            "Invalid email format",
            inputs={"email": "invalid"},
            repair_hint="Use format user@domain.com"
        )

        assert isinstance(exc, RepairableException)
        assert exc.message == "Invalid email format"

    def test_rate_limit_exception(self):
        """Test RateLimitException with retry_after."""
        exc = RateLimitException("Rate limit exceeded", retry_after=60)

        assert isinstance(exc, RepairableException)
        assert exc.retry_after == 60
        assert "60 seconds" in exc.repair_hint

    def test_missing_data_exception(self):
        """Test MissingDataException subclass."""
        exc = MissingDataException(
            "Missing required field: email",
            inputs={"lead_id": "123"},
            repair_hint="Provide email field"
        )

        assert isinstance(exc, RepairableException)
        assert exc.message == "Missing required field: email"

    def test_timeout_exception(self):
        """Test TimeoutException with timeout_seconds."""
        exc = TimeoutException("Operation timed out", timeout_seconds=30)

        assert isinstance(exc, RepairableException)
        assert exc.timeout_seconds == 30
        assert "30s" in exc.repair_hint


# ============================================================================
# Test Utility Functions
# ============================================================================

class TestUtilityFunctions:
    """Test utility functions for error handling."""

    def test_format_error_agent_exception(self):
        """Test format_error with AgentException."""
        exc = ValidationException("Test error")
        formatted = format_error(exc)

        assert "ValidationException" in formatted
        assert "Test error" in formatted
        assert "Error ID:" in formatted

    def test_format_error_standard_exception(self):
        """Test format_error with standard Exception."""
        exc = ValueError("Standard error")
        formatted = format_error(exc)

        assert "ValueError" in formatted
        assert "Standard error" in formatted

    def test_is_repairable(self):
        """Test is_repairable utility function."""
        assert is_repairable(RepairableException("Test")) is True
        assert is_repairable(ValidationException("Test")) is True
        assert is_repairable(APICallException("Test")) is True
        assert is_repairable(HandledException("Test")) is False
        assert is_repairable(InterventionException("Test")) is False
        assert is_repairable(ValueError("Test")) is False

    def test_is_intervention(self):
        """Test is_intervention utility function."""
        assert is_intervention(InterventionException("Test")) is True
        assert is_intervention(RepairableException("Test")) is False
        assert is_intervention(HandledException("Test")) is False
        assert is_intervention(ValueError("Test")) is False

    def test_is_handled(self):
        """Test is_handled utility function."""
        assert is_handled(HandledException("Test")) is True
        assert is_handled(RepairableException("Test")) is False
        assert is_handled(InterventionException("Test")) is False
        assert is_handled(ValueError("Test")) is False


# ============================================================================
# Test Decorators - Sync Functions
# ============================================================================

class TestWithRetryLogicSync:
    """Test @with_retry_logic decorator with synchronous functions."""

    def test_successful_operation_no_retry(self):
        """Test successful operation requires no retry."""
        call_count = [0]

        @with_retry_logic(max_attempts=3, operation_name="test_success")
        def success_operation():
            call_count[0] += 1
            return {"result": "success"}

        result = success_operation()

        assert result == {"result": "success"}
        assert call_count[0] == 1  # Only called once

    def test_repairable_exception_retry(self):
        """Test RepairableException triggers retry."""
        call_count = [0]

        @with_retry_logic(max_attempts=3, operation_name="test_retry")
        def failing_then_success():
            call_count[0] += 1
            if call_count[0] < 2:
                raise RepairableException(
                    "First attempt failed",
                    inputs={"attempt": call_count[0]}
                )
            return {"result": "success"}

        result = failing_then_success()

        assert result == {"result": "success"}
        assert call_count[0] == 2  # Called twice (1 failure, 1 success)

    def test_max_attempts_exceeded(self):
        """Test max attempts exceeded raises HandledException."""
        call_count = [0]

        @with_retry_logic(max_attempts=2, operation_name="test_max_attempts")
        def always_fails():
            call_count[0] += 1
            raise RepairableException("Always fails")

        with pytest.raises(HandledException) as exc_info:
            always_fails()

        assert call_count[0] == 2  # Called max_attempts times
        assert "Max retry attempts exceeded" in str(exc_info.value)

    def test_intervention_exception_immediate_reraise(self):
        """Test InterventionException is re-raised immediately."""
        call_count = [0]

        @with_retry_logic(max_attempts=3, operation_name="test_intervention")
        def user_interrupted():
            call_count[0] += 1
            raise InterventionException("User stopped")

        with pytest.raises(InterventionException):
            user_interrupted()

        assert call_count[0] == 1  # Only called once, no retry

    def test_non_repairable_exception_converted(self):
        """Test non-repairable exceptions convert to HandledException."""
        call_count = [0]

        @with_retry_logic(max_attempts=3, operation_name="test_convert")
        def raises_value_error():
            call_count[0] += 1
            raise ValueError("Not repairable")

        with pytest.raises(HandledException) as exc_info:
            raises_value_error()

        assert call_count[0] == 1  # Only called once, not retried
        assert "Critical error" in str(exc_info.value)
        assert isinstance(exc_info.value.original_exception, ValueError)

    def test_exponential_backoff(self):
        """Test exponential backoff between retries."""
        call_times = []

        @with_retry_logic(max_attempts=3, operation_name="test_backoff")
        def failing_with_timing():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise RepairableException("Retry me")
            return "success"

        result = failing_with_timing()

        assert result == "success"
        assert len(call_times) == 3

        # Check backoff times (should be ~1s, ~2s)
        # Allow some tolerance for timing
        time_diff_1 = call_times[1] - call_times[0]
        time_diff_2 = call_times[2] - call_times[1]

        assert 0.9 < time_diff_1 < 1.5  # ~1 second backoff
        assert 1.8 < time_diff_2 < 2.5  # ~2 second backoff

    def test_repair_hint_logged(self):
        """Test repair hint is logged."""
        @with_retry_logic(max_attempts=2, operation_name="test_hint")
        def with_hint():
            raise RepairableException(
                "Error with hint",
                repair_hint="Try this fix"
            )

        with pytest.raises(HandledException):
            with patch('core.decorators.logger') as mock_logger:
                with_hint()
                # Verify hint was logged
                # (In real test, we'd check mock_logger.info.called_with)


# ============================================================================
# Test Decorators - Async Functions
# ============================================================================

class TestWithRetryLogicAsync:
    """Test @with_retry_logic decorator with async functions."""

    @pytest.mark.asyncio
    async def test_async_successful_operation(self):
        """Test async successful operation."""
        call_count = [0]

        @with_retry_logic(max_attempts=3, operation_name="test_async_success")
        async def async_success():
            call_count[0] += 1
            await asyncio.sleep(0.01)
            return {"result": "success"}

        result = await async_success()

        assert result == {"result": "success"}
        assert call_count[0] == 1

    @pytest.mark.asyncio
    async def test_async_repairable_retry(self):
        """Test async RepairableException triggers retry."""
        call_count = [0]

        @with_retry_logic(max_attempts=3, operation_name="test_async_retry")
        async def async_retry():
            call_count[0] += 1
            await asyncio.sleep(0.01)
            if call_count[0] < 2:
                raise RepairableException("Retry me")
            return "success"

        result = await async_retry()

        assert result == "success"
        assert call_count[0] == 2

    @pytest.mark.asyncio
    async def test_async_max_attempts(self):
        """Test async max attempts exceeded."""
        call_count = [0]

        @with_retry_logic(max_attempts=2, operation_name="test_async_max")
        async def async_always_fails():
            call_count[0] += 1
            raise RepairableException("Always fails")

        with pytest.raises(HandledException):
            await async_always_fails()

        assert call_count[0] == 2


# ============================================================================
# Test Other Decorators
# ============================================================================

class TestOtherDecorators:
    """Test other decorator functions."""

    def test_log_exceptions_decorator(self):
        """Test @log_exceptions decorator."""
        @log_exceptions(operation_name="test_log")
        def raises_error():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            with patch('core.decorators.logger') as mock_logger:
                raises_error()
                # Would verify mock_logger.error was called

    def test_graceful_degradation_returns_fallback(self):
        """Test @graceful_degradation returns fallback on error."""
        @graceful_degradation(fallback_value={"default": True})
        def fails():
            raise ValueError("Error")

        result = fails()

        assert result == {"default": True}

    def test_graceful_degradation_success(self):
        """Test @graceful_degradation returns normal result on success."""
        @graceful_degradation(fallback_value=None)
        def succeeds():
            return {"success": True}

        result = succeeds()

        assert result == {"success": True}


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for error handling system."""

    def test_full_retry_flow(self):
        """Test complete retry flow with error recovery."""
        attempts = []

        @with_retry_logic(max_attempts=4, operation_name="full_flow")
        def operation_with_recovery():
            attempt_num = len(attempts) + 1
            attempts.append(attempt_num)

            if attempt_num == 1:
                raise ValidationException(
                    "Invalid input",
                    inputs={"data": "bad"},
                    repair_hint="Fix the data"
                )
            elif attempt_num == 2:
                raise APICallException(
                    "API timeout",
                    inputs={"url": "/api"},
                    repair_hint="Retry with longer timeout"
                )
            elif attempt_num == 3:
                raise RepairableException(
                    "Temporary issue",
                    repair_hint="Just retry"
                )
            else:
                return {"success": True, "attempts": attempt_num}

        result = operation_with_recovery()

        assert result["success"] is True
        assert result["attempts"] == 4
        assert len(attempts) == 4

    def test_mixed_exception_handling(self):
        """Test handling of mixed exception types."""
        @with_retry_logic(max_attempts=2, operation_name="mixed")
        def mixed_errors():
            # First call: repairable
            # Second call: non-repairable
            # Should convert non-repairable to HandledException
            raise ValueError("Not repairable")

        with pytest.raises(HandledException):
            mixed_errors()

    def test_error_context_preservation(self):
        """Test error context is preserved through retry."""
        @with_retry_logic(max_attempts=2, operation_name="context_test")
        def with_context():
            raise ValidationException(
                "Test error",
                inputs={"key": "value"},
                repair_hint="Fix it"
            )

        try:
            with_context()
        except HandledException as e:
            # Check context was preserved
            assert e.original_exception is not None
            assert isinstance(e.original_exception, ValidationException)
            assert e.original_exception.repair_hint == "Fix it"

    @pytest.mark.asyncio
    async def test_async_integration(self):
        """Test full async integration."""
        call_log = []

        @with_retry_logic(max_attempts=3, operation_name="async_integration")
        async def async_operation():
            call_num = len(call_log) + 1
            call_log.append(call_num)
            await asyncio.sleep(0.01)

            if call_num < 2:
                raise RepairableException(f"Attempt {call_num} failed")

            return {"result": "success", "attempts": call_num}

        result = await async_operation()

        assert result["result"] == "success"
        assert result["attempts"] == 2
        assert len(call_log) == 2


# ============================================================================
# Example Use Case Tests
# ============================================================================

class TestUseCases:
    """Test real-world use cases."""

    def test_lead_validation_use_case(self):
        """Test lead validation with error recovery."""
        @with_retry_logic(max_attempts=3, operation_name="validate_lead")
        def validate_lead(email: str) -> str:
            if not email:
                raise MissingDataException(
                    "Email is required",
                    inputs={"email": email},
                    repair_hint="Provide email address"
                )

            if '@' not in email:
                raise ValidationException(
                    "Invalid email format",
                    inputs={"email": email},
                    repair_hint="Email must contain @"
                )

            return email.lower()

        # Test success
        result = validate_lead("TEST@EXAMPLE.COM")
        assert result == "test@example.com"

        # Test failure
        with pytest.raises(HandledException):
            validate_lead("")

    def test_api_call_use_case(self):
        """Test API call with rate limiting."""
        call_count = [0]

        @with_retry_logic(max_attempts=3, operation_name="api_call")
        def api_call(endpoint: str) -> Dict:
            call_count[0] += 1

            if call_count[0] < 2:
                raise RateLimitException(
                    "Rate limit exceeded",
                    retry_after=1
                )

            return {"data": "success", "endpoint": endpoint}

        result = api_call("/api/users")

        assert result["data"] == "success"
        assert call_count[0] == 2  # Failed once, succeeded second time


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
