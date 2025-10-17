"""Retry utilities for resilient external API calls."""
import asyncio
import logging
from functools import wraps
from typing import Callable, Type, Tuple
from config.settings import settings

logger = logging.getLogger(__name__)


def async_retry(
    max_attempts: int = None,
    min_wait: float = None,
    max_wait: float = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """Decorator for async functions with exponential backoff retry logic.
    
    Args:
        max_attempts: Maximum number of retry attempts (default: settings.MAX_RETRIES)
        min_wait: Minimum wait time in seconds (default: settings.RETRY_MIN_WAIT_SECONDS)
        max_wait: Maximum wait time in seconds (default: settings.RETRY_MAX_WAIT_SECONDS)
        exceptions: Tuple of exception types to catch and retry
    
    Example:
        @async_retry(max_attempts=3)
        async def send_email(to: str):
            # ... email sending logic
    """
    if max_attempts is None:
        max_attempts = settings.MAX_RETRIES
    if min_wait is None:
        min_wait = settings.RETRY_MIN_WAIT_SECONDS
    if max_wait is None:
        max_wait = settings.RETRY_MAX_WAIT_SECONDS
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"❌ {func.__name__} failed after {max_attempts} attempts: {str(e)}"
                        )
                        raise
                    
                    # Calculate exponential backoff
                    wait_time = min(min_wait * (2 ** (attempt - 1)), max_wait)
                    
                    logger.warning(
                        f"⚠️ {func.__name__} failed (attempt {attempt}/{max_attempts}). "
                        f"Retrying in {wait_time:.1f}s... Error: {str(e)}"
                    )
                    
                    await asyncio.sleep(wait_time)
            
            # Should never reach here, but just in case
            raise last_exception
        
        return wrapper
    return decorator


def sync_retry(
    max_attempts: int = None,
    min_wait: float = None,
    max_wait: float = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """Decorator for synchronous functions with exponential backoff retry logic.
    
    Similar to async_retry but for sync functions.
    """
    if max_attempts is None:
        max_attempts = settings.MAX_RETRIES
    if min_wait is None:
        min_wait = settings.RETRY_MIN_WAIT_SECONDS
    if max_wait is None:
        max_wait = settings.RETRY_MAX_WAIT_SECONDS
    
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"❌ {func.__name__} failed after {max_attempts} attempts: {str(e)}"
                        )
                        raise
                    
                    wait_time = min(min_wait * (2 ** (attempt - 1)), max_wait)
                    
                    logger.warning(
                        f"⚠️ {func.__name__} failed (attempt {attempt}/{max_attempts}). "
                        f"Retrying in {wait_time:.1f}s... Error: {str(e)}"
                    )
                    
                    time.sleep(wait_time)
            
            raise last_exception
        
        return wrapper
    return decorator
