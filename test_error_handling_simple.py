#!/usr/bin/env python3
"""Simple test script to verify error handling implementation works.

This script tests the core functionality without requiring pytest.
"""

import sys
import time
import traceback
from datetime import datetime

# Add project to path
sys.path.insert(0, '/Users/joshisrael/hume-dspy-agent')

from core.exceptions import (
    ErrorSeverity,
    ErrorContext,
    InterventionException,
    RepairableException,
    HandledException,
    ValidationException,
    APICallException,
    format_error,
    is_repairable
)

from core.decorators import (
    with_retry_logic,
    graceful_degradation
)


# ============================================================================
# Test Functions
# ============================================================================

def test_error_context():
    """Test ErrorContext creation."""
    print("\n1. Testing ErrorContext creation...")

    context = ErrorContext(
        exception_type="TestException",
        error_message="Test error",
        inputs_attempted={"key": "value"},
        repair_hint="Try this fix"
    )

    assert context.exception_type == "TestException"
    assert context.error_message == "Test error"
    assert context.repair_hint == "Try this fix"
    assert context.repair_attempts == 0
    print("   ✓ ErrorContext creation works")


def test_exception_hierarchy():
    """Test exception hierarchy."""
    print("\n2. Testing exception hierarchy...")

    # Test InterventionException
    intervention = InterventionException("User stopped")
    assert intervention.message == "User stopped"
    print("   ✓ InterventionException works")

    # Test RepairableException
    repairable = RepairableException(
        "API failed",
        inputs={"url": "test"},
        repair_hint="Retry"
    )
    assert repairable.can_retry() is True
    repairable.increment_repair_attempt()
    assert repairable.error_context.repair_attempts == 1
    print("   ✓ RepairableException works")

    # Test HandledException
    handled = HandledException("Critical error")
    assert handled.error_context.severity == ErrorSeverity.CRITICAL
    print("   ✓ HandledException works")

    # Test specific subclasses
    validation = ValidationException("Invalid email")
    assert isinstance(validation, RepairableException)
    print("   ✓ ValidationException works")

    api_error = APICallException("API timeout")
    assert isinstance(api_error, RepairableException)
    print("   ✓ APICallException works")


def test_utility_functions():
    """Test utility functions."""
    print("\n3. Testing utility functions...")

    exc = ValidationException("Test")
    formatted = format_error(exc)
    assert "ValidationException" in formatted
    print("   ✓ format_error works")

    assert is_repairable(ValidationException("Test")) is True
    assert is_repairable(HandledException("Test")) is False
    print("   ✓ is_repairable works")


def test_retry_logic_success():
    """Test retry logic with successful operation."""
    print("\n4. Testing retry logic - success case...")

    call_count = [0]

    @with_retry_logic(max_attempts=3, operation_name="test_success")
    def success_operation():
        call_count[0] += 1
        return {"result": "success"}

    result = success_operation()
    assert result == {"result": "success"}
    assert call_count[0] == 1
    print("   ✓ Successful operation works (no retry)")


def test_retry_logic_with_recovery():
    """Test retry logic with recovery."""
    print("\n5. Testing retry logic - recovery case...")

    call_count = [0]

    @with_retry_logic(max_attempts=3, operation_name="test_recovery")
    def failing_then_success():
        call_count[0] += 1
        if call_count[0] < 2:
            raise RepairableException(
                "First attempt failed",
                repair_hint="Just retry"
            )
        return {"result": "success", "attempts": call_count[0]}

    result = failing_then_success()
    assert result["result"] == "success"
    assert result["attempts"] == 2
    assert call_count[0] == 2
    print(f"   ✓ Recovery works (succeeded after {call_count[0]} attempts)")


def test_retry_logic_max_attempts():
    """Test retry logic max attempts exceeded."""
    print("\n6. Testing retry logic - max attempts...")

    call_count = [0]

    @with_retry_logic(max_attempts=2, operation_name="test_max")
    def always_fails():
        call_count[0] += 1
        raise RepairableException("Always fails")

    try:
        always_fails()
        assert False, "Should have raised HandledException"
    except HandledException as e:
        assert "Max retry attempts exceeded" in str(e)
        assert call_count[0] == 2
        print(f"   ✓ Max attempts works (failed after {call_count[0]} attempts)")


def test_intervention_immediate_stop():
    """Test intervention exception stops immediately."""
    print("\n7. Testing intervention exception...")

    call_count = [0]

    @with_retry_logic(max_attempts=3, operation_name="test_intervention")
    def user_stops():
        call_count[0] += 1
        raise InterventionException("User stopped")

    try:
        user_stops()
        assert False, "Should have raised InterventionException"
    except InterventionException:
        assert call_count[0] == 1
        print("   ✓ Intervention stops immediately (no retry)")


def test_non_repairable_conversion():
    """Test non-repairable exceptions convert to HandledException."""
    print("\n8. Testing non-repairable exception conversion...")

    call_count = [0]

    @with_retry_logic(max_attempts=3, operation_name="test_convert")
    def raises_value_error():
        call_count[0] += 1
        raise ValueError("Not repairable")

    try:
        raises_value_error()
        assert False, "Should have raised HandledException"
    except HandledException as e:
        assert call_count[0] == 1
        assert isinstance(e.original_exception, ValueError)
        print("   ✓ Non-repairable exceptions convert to HandledException")


def test_graceful_degradation():
    """Test graceful degradation decorator."""
    print("\n9. Testing graceful degradation...")

    @graceful_degradation(fallback_value={"default": True})
    def fails():
        raise ValueError("Error")

    result = fails()
    assert result == {"default": True}
    print("   ✓ Graceful degradation returns fallback value")


def test_validation_use_case():
    """Test real-world validation use case."""
    print("\n10. Testing real-world validation use case...")

    @with_retry_logic(max_attempts=2, operation_name="validate_email")
    def validate_email(email: str) -> str:
        if not email:
            raise ValidationException(
                "Email is required",
                inputs={"email": email},
                repair_hint="Provide email"
            )
        if '@' not in email:
            raise ValidationException(
                "Invalid email format",
                inputs={"email": email},
                repair_hint="Email must contain @"
            )
        return email.lower()

    # Test success
    result = validate_email("TEST@EXAMPLE.COM")
    assert result == "test@example.com"
    print("   ✓ Email validation works")

    # Test failure
    try:
        validate_email("")
        assert False, "Should have raised HandledException"
    except HandledException:
        print("   ✓ Email validation fails correctly")


# ============================================================================
# Run All Tests
# ============================================================================

def run_all_tests():
    """Run all tests and report results."""
    print("=" * 70)
    print("Error Handling System - Verification Tests")
    print("=" * 70)

    tests = [
        test_error_context,
        test_exception_hierarchy,
        test_utility_functions,
        test_retry_logic_success,
        test_retry_logic_with_recovery,
        test_retry_logic_max_attempts,
        test_intervention_immediate_stop,
        test_non_repairable_conversion,
        test_graceful_degradation,
        test_validation_use_case,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"\n   ✗ Test failed: {test_func.__name__}")
            print(f"   Error: {str(e)}")
            traceback.print_exc()

    print("\n" + "=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70)

    if failed == 0:
        print("\n✓ All tests passed! Error handling system is working correctly.")
        return 0
    else:
        print(f"\n✗ {failed} test(s) failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
