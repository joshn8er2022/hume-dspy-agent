"""Webhook security utilities for signature verification."""
import hmac
import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def verify_typeform_signature(
    payload: bytes,
    signature: str,
    secret: str
) -> bool:
    """Verify Typeform webhook signature.

    Typeform signs webhooks with HMAC-SHA256 using your webhook secret.
    The signature is sent in the X-Typeform-Signature header.

    Args:
        payload: Raw request body as bytes
        signature: Signature from X-Typeform-Signature header
        secret: Your Typeform webhook secret

    Returns:
        True if signature is valid, False otherwise

    Example:
        ```python
        @app.post("/webhooks/typeform")
        async def typeform_webhook(request: Request):
            body = await request.body()
            signature = request.headers.get("X-Typeform-Signature", "")

            if not verify_typeform_signature(body, signature, TYPEFORM_SECRET):
                raise HTTPException(status_code=401, detail="Invalid signature")

            # Process webhook...
        ```
    """
    if not secret:
        logger.warning("No Typeform secret configured - skipping signature verification")
        return True  # Allow if no secret configured (dev mode)

    try:
        # Typeform uses HMAC-SHA256
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()

        # Typeform sends signature as "sha256=<hash>"
        if signature.startswith("sha256="):
            signature = signature[7:]  # Remove "sha256=" prefix

        # Constant-time comparison to prevent timing attacks
        is_valid = hmac.compare_digest(expected_signature, signature)

        if not is_valid:
            logger.warning(f"Invalid Typeform signature. Expected: {expected_signature[:10]}...")

        return is_valid

    except Exception as e:
        logger.error(f"Error verifying Typeform signature: {e}")
        return False


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str,
    algorithm: str = "sha256"
) -> bool:
    """Generic webhook signature verification.

    Works with any HMAC-based webhook signature.

    Args:
        payload: Raw request body as bytes
        signature: Signature from header
        secret: Webhook secret
        algorithm: Hash algorithm (sha256, sha1, etc.)

    Returns:
        True if signature is valid, False otherwise
    """
    if not secret:
        logger.warning(f"No secret configured - skipping signature verification")
        return True

    try:
        # Get hash function
        hash_func = getattr(hashlib, algorithm)

        # Calculate expected signature
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hash_func
        ).hexdigest()

        # Remove algorithm prefix if present (e.g., "sha256=")
        if "=" in signature:
            signature = signature.split("=", 1)[1]

        # Constant-time comparison
        return hmac.compare_digest(expected_signature, signature)

    except Exception as e:
        logger.error(f"Error verifying webhook signature: {e}")
        return False
