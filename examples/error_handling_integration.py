"""Example integration of 3-tier error handling in InboundAgent.

This file demonstrates how to integrate the error handling system
into the InboundAgent's qualify_lead() method and other operations.

This is a reference implementation showing best practices.
"""

import logging
from typing import Dict, Any, Optional
from models import Lead, QualificationResult, LeadTier
from core.exceptions import (
    RepairableException,
    ValidationException,
    HandledException,
    MissingDataException
)
from core.decorators import with_retry_logic, graceful_degradation

logger = logging.getLogger(__name__)


# ============================================================================
# Example 1: Applying @with_retry_logic to lead validation
# ============================================================================

@with_retry_logic(
    max_attempts=3,
    enable_llm_recovery=True,
    operation_name="validate_lead_data"
)
def validate_lead_data(lead: Lead) -> Dict[str, Any]:
    """Validate lead data with automatic retry on validation errors.

    This method demonstrates wrapping validation logic with error recovery.
    If validation fails, the RepairableException provides hints for self-repair.

    Args:
        lead: Lead object to validate

    Returns:
        Dict with validated fields

    Raises:
        RepairableException: If validation fails (will be retried)
        HandledException: If max retries exceeded
    """
    validated_data = {}

    # Validate email
    email = lead.get_field('email')
    if not email:
        raise MissingDataException(
            "Lead missing email field",
            inputs={"lead_id": lead.id},
            repair_hint="Email is required for qualification. Check if lead has 'email' or 'email_address' field."
        )

    if '@' not in email or '.' not in email.split('@')[-1]:
        raise ValidationException(
            f"Invalid email format: {email}",
            inputs={"email": email, "lead_id": lead.id},
            repair_hint="Email must be in format: user@domain.com"
        )

    validated_data['email'] = email

    # Validate phone (optional but recommended)
    phone = lead.get_field('phone') or lead.get_field('phone_number')
    if phone:
        # Basic phone validation
        clean_phone = ''.join(c for c in phone if c.isdigit() or c == '+')
        if len(clean_phone) < 10:
            logger.warning(f"Phone number may be invalid: {phone}")
            # This is not critical, so we don't raise an exception
        validated_data['phone'] = clean_phone
    else:
        logger.info("Phone number not provided")

    # Validate business size
    business_size = lead.get_field('business_size')
    if not business_size:
        raise MissingDataException(
            "Lead missing business_size field",
            inputs={"lead_id": lead.id},
            repair_hint="business_size is required. Check if lead has 'business_size' or 'company_size' field."
        )

    validated_data['business_size'] = business_size

    logger.info(f"Lead {lead.id} validation successful")
    return validated_data


# ============================================================================
# Example 2: Wrapping qualification with error handling
# ============================================================================

@with_retry_logic(
    max_attempts=3,
    enable_llm_recovery=True,
    operation_name="qualify_lead"
)
def qualify_lead_with_error_handling(lead: Lead, agent: Any) -> QualificationResult:
    """Qualify lead with automatic error recovery.

    This demonstrates wrapping the entire qualification process
    with error recovery logic.

    Args:
        lead: Lead to qualify
        agent: InboundAgent instance

    Returns:
        QualificationResult

    Raises:
        RepairableException: If qualification encounters recoverable error
        HandledException: If critical error or max retries exceeded
    """
    try:
        # Step 1: Validate lead data
        validated_data = validate_lead_data(lead)

        # Step 2: Run qualification (existing agent logic)
        result = agent.forward(lead)

        return result

    except ValidationException as e:
        # Validation failed - this is repairable
        logger.warning(f"Validation failed for lead {lead.id}: {e.message}")
        raise  # Re-raise to trigger retry

    except MissingDataException as e:
        # Missing data - this is repairable
        logger.warning(f"Missing data for lead {lead.id}: {e.message}")
        raise  # Re-raise to trigger retry

    except Exception as e:
        # Unexpected error - convert to HandledException
        logger.error(f"Unexpected error qualifying lead {lead.id}: {str(e)}")
        raise HandledException(
            f"Failed to qualify lead {lead.id}: {str(e)}",
            original_exception=e
        )


# ============================================================================
# Example 3: Graceful degradation for non-critical operations
# ============================================================================

@graceful_degradation(
    fallback_value=None,
    operation_name="enrich_lead_data"
)
def enrich_lead_data(lead: Lead) -> Optional[Dict[str, Any]]:
    """Enrich lead with additional data.

    This demonstrates graceful degradation - if enrichment fails,
    we return None instead of crashing. Qualification can continue
    with basic data.

    Args:
        lead: Lead to enrich

    Returns:
        Enrichment data dict or None if failed
    """
    # Simulated enrichment logic
    # In real implementation, this would call external APIs
    enrichment_data = {
        "company_size": "50-100 employees",
        "industry": "Healthcare",
        "location": "San Francisco, CA"
    }

    # Simulate potential failure
    if not lead.get_field('company'):
        logger.warning(f"Cannot enrich lead {lead.id} - missing company name")
        raise MissingDataException(
            "Cannot enrich without company name",
            inputs={"lead_id": lead.id},
            repair_hint="Company name is required for enrichment"
        )

    return enrichment_data


# ============================================================================
# Example 4: Validation with specific error types
# ============================================================================

class LeadValidator:
    """Lead validation with specific error handling."""

    @staticmethod
    @with_retry_logic(max_attempts=2, operation_name="validate_email")
    def validate_email(email: str) -> str:
        """Validate and normalize email address.

        Args:
            email: Email to validate

        Returns:
            Normalized email

        Raises:
            ValidationException: If email is invalid
        """
        if not email:
            raise ValidationException(
                "Email is empty",
                inputs={"email": email},
                repair_hint="Provide a non-empty email address"
            )

        email = email.strip().lower()

        if '@' not in email:
            raise ValidationException(
                "Email missing @ symbol",
                inputs={"email": email},
                repair_hint="Email must contain @ symbol (format: user@domain.com)"
            )

        if '.' not in email.split('@')[-1]:
            raise ValidationException(
                "Email domain missing extension",
                inputs={"email": email},
                repair_hint="Email domain must have extension (e.g., .com, .org)"
            )

        return email

    @staticmethod
    @with_retry_logic(max_attempts=2, operation_name="validate_phone")
    def validate_phone(phone: str) -> str:
        """Validate and normalize phone number.

        Args:
            phone: Phone number to validate

        Returns:
            Normalized phone number

        Raises:
            ValidationException: If phone is invalid
        """
        if not phone:
            raise ValidationException(
                "Phone is empty",
                inputs={"phone": phone},
                repair_hint="Provide a non-empty phone number"
            )

        # Remove non-digit characters except +
        clean_phone = ''.join(c for c in phone if c.isdigit() or c == '+')

        # Check length
        if len(clean_phone) < 10:
            raise ValidationException(
                f"Phone number too short: {clean_phone}",
                inputs={"phone": phone},
                repair_hint="Phone must have at least 10 digits"
            )

        return clean_phone


# ============================================================================
# Example 5: Integration with InboundAgent
# ============================================================================

def integrate_error_handling_into_inbound_agent():
    """
    Example showing how to integrate error handling into InboundAgent.

    To integrate into the actual InboundAgent class:

    1. Import error handling modules:
       ```python
       from core.exceptions import (
           RepairableException,
           ValidationException,
           HandledException,
           MissingDataException
       )
       from core.decorators import with_retry_logic
       ```

    2. Add validation method to InboundAgent:
       ```python
       @with_retry_logic(max_attempts=3, operation_name="validate_lead")
       def _validate_lead(self, lead: Lead) -> Dict[str, Any]:
           # Validation logic here
           if not lead.get_field('email'):
               raise MissingDataException(
                   "Lead missing email",
                   inputs={"lead_id": lead.id},
                   repair_hint="Email is required"
               )
           return validated_data
       ```

    3. Wrap qualification logic:
       ```python
       def forward(self, lead: Lead) -> QualificationResult:
           try:
               # Validate first
               validated_data = self._validate_lead(lead)

               # Run qualification
               # ... existing qualification logic ...

               return result

           except HandledException as e:
               # Critical error - return error result
               logger.error(f"Qualification failed: {e.message}")
               return self._create_error_result(lead, e)
       ```

    4. Add error result method:
       ```python
       def _create_error_result(self, lead: Lead, error: HandledException) -> QualificationResult:
           return QualificationResult(
               is_qualified=False,
               score=0,
               tier=LeadTier.UNQUALIFIED,
               reasoning=f"Qualification failed: {error.message}",
               key_factors=[],
               concerns=["Processing error occurred"],
               error_context=error.error_context
           )
       ```
    """
    pass


# ============================================================================
# Example 6: Error handling in async operations
# ============================================================================

@with_retry_logic(max_attempts=3, operation_name="async_enrichment")
async def enrich_lead_async(lead_id: str) -> Dict[str, Any]:
    """Async lead enrichment with error recovery.

    The @with_retry_logic decorator works with both sync and async functions.

    Args:
        lead_id: ID of lead to enrich

    Returns:
        Enrichment data

    Raises:
        RepairableException: If enrichment fails temporarily
        HandledException: If enrichment fails permanently
    """
    import asyncio

    # Simulate async API call
    await asyncio.sleep(0.1)

    # Simulate potential failure
    if not lead_id:
        raise ValidationException(
            "Lead ID is required",
            inputs={"lead_id": lead_id},
            repair_hint="Provide valid lead ID"
        )

    return {
        "enriched": True,
        "data": {"company": "Example Corp"}
    }


# ============================================================================
# Example 7: Manual error handling without decorator
# ============================================================================

def manual_error_handling_example(lead: Lead) -> QualificationResult:
    """Example of manual error handling without decorator.

    Sometimes you need more control over error handling.
    This shows how to use the exception classes directly.

    Args:
        lead: Lead to process

    Returns:
        QualificationResult
    """
    max_attempts = 3
    attempt = 0

    while attempt < max_attempts:
        attempt += 1

        try:
            # Validate email
            email = lead.get_field('email')
            if not email or '@' not in email:
                raise ValidationException(
                    f"Invalid email: {email}",
                    inputs={"email": email},
                    repair_hint="Email must contain @ symbol"
                )

            # Process lead
            # ... qualification logic ...

            # Success!
            return QualificationResult(
                is_qualified=True,
                score=85,
                tier=LeadTier.HOT,
                reasoning="Valid lead",
                key_factors=["Good email"],
                concerns=[]
            )

        except ValidationException as e:
            logger.warning(f"Attempt {attempt}/{max_attempts} failed: {e.message}")

            if attempt >= max_attempts:
                # Max attempts exceeded
                raise HandledException(
                    f"Validation failed after {max_attempts} attempts",
                    original_exception=e
                )

            # Wait before retry
            import time
            time.sleep(1)
            continue

    # Should never reach here
    raise HandledException("Unexpected exit from retry loop")


# ============================================================================
# Usage Example
# ============================================================================

if __name__ == "__main__":
    # This shows how the error handling system works in practice

    # Example 1: Validate lead data
    from models import Lead

    lead = Lead(
        id="test_123",
        email="john@example.com",
        phone="+1234567890",
        typeform_response={
            "business_size": "Large",
            "patient_volume": "100+"
        }
    )

    try:
        validated = validate_lead_data(lead)
        print(f"✓ Validation successful: {validated}")
    except HandledException as e:
        print(f"✗ Validation failed: {e.message}")

    # Example 2: Graceful degradation
    enrichment = enrich_lead_data(lead)
    if enrichment:
        print(f"✓ Enrichment successful: {enrichment}")
    else:
        print("⚠ Enrichment failed, continuing with basic data")

    # Example 3: Validator usage
    try:
        email = LeadValidator.validate_email("john@example.com")
        print(f"✓ Email valid: {email}")
    except ValidationException as e:
        print(f"✗ Email invalid: {e.message}")
