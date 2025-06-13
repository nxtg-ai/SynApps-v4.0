"""
Retry utilities for handling transient failures in external API calls.

This module provides decorators and utilities for implementing retry mechanisms
with exponential backoff and circuit breaking capabilities.
"""
import asyncio
import functools
import logging
import random
import time
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union, cast

# Configure logging
logger = logging.getLogger("retry-utils")

# Type variable for the decorated function
F = TypeVar('F', bound=Callable[..., Any])

class RetryExhausted(Exception):
    """Exception raised when all retry attempts have been exhausted."""
    pass

def async_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retry_exceptions: List[Type[Exception]] = None,
    retry_on_status_codes: List[int] = None,
    circuit_breaker_threshold: Optional[int] = None,
    circuit_breaker_timeout: float = 60.0,
):
    """
    Decorator for async functions to implement retry logic with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Multiplier for the delay after each retry
        jitter: Whether to add random jitter to the delay
        retry_exceptions: List of exception types that should trigger a retry
        retry_on_status_codes: List of HTTP status codes that should trigger a retry
        circuit_breaker_threshold: Number of consecutive failures before opening the circuit
        circuit_breaker_timeout: Time in seconds before the circuit breaker resets
    
    Returns:
        Decorated function with retry logic
    """
    # Default retry exceptions
    if retry_exceptions is None:
        retry_exceptions = [
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
        ]
    
    # Default retry status codes (common transient failures)
    if retry_on_status_codes is None:
        retry_on_status_codes = [408, 429, 500, 502, 503, 504]
    
    # Circuit breaker state
    circuit_state = {
        "failures": 0,
        "open_until": 0,
    }

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Check if circuit breaker is open
            if circuit_breaker_threshold and circuit_state["failures"] >= circuit_breaker_threshold:
                if time.time() < circuit_state["open_until"]:
                    logger.warning(f"Circuit breaker open for {func.__name__}, request rejected")
                    raise RetryExhausted(f"Circuit breaker open for {func.__name__}")
                else:
                    # Reset circuit breaker for a test request
                    circuit_state["failures"] = circuit_breaker_threshold - 1
            
            # Retry loop
            retries = 0
            last_exception = None
            
            while retries <= max_retries:
                try:
                    # Attempt the function call
                    result = await func(*args, **kwargs)
                    
                    # Check if result has a status_code attribute (like httpx.Response)
                    status_code = getattr(result, "status_code", None)
                    if status_code is not None and status_code in retry_on_status_codes:
                        raise Exception(f"Received status code {status_code}")
                    
                    # Success - reset circuit breaker failures
                    if circuit_breaker_threshold:
                        circuit_state["failures"] = 0
                    
                    return result
                
                except Exception as e:
                    last_exception = e
                    
                    # Check if this exception should trigger a retry
                    should_retry = False
                    
                    # Check if it's a known retry exception
                    for exc_type in retry_exceptions:
                        if isinstance(e, exc_type):
                            should_retry = True
                            break
                    
                    # Check for HTTP status code in the exception message
                    if not should_retry and retry_on_status_codes:
                        for code in retry_on_status_codes:
                            if str(code) in str(e):
                                should_retry = True
                                break
                    
                    # If we shouldn't retry or we're out of retries
                    if not should_retry or retries >= max_retries:
                        # Update circuit breaker
                        if circuit_breaker_threshold:
                            circuit_state["failures"] += 1
                            if circuit_state["failures"] >= circuit_breaker_threshold:
                                circuit_state["open_until"] = time.time() + circuit_breaker_timeout
                                logger.warning(f"Circuit breaker opened for {func.__name__}")
                        
                        # Re-raise the last exception
                        raise last_exception
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (backoff_factor ** retries), max_delay)
                    
                    # Add jitter if enabled
                    if jitter:
                        delay = delay * (0.5 + random.random())
                    
                    # Log the retry attempt
                    logger.warning(
                        f"Retry {retries + 1}/{max_retries} for {func.__name__} "
                        f"after {delay:.2f}s due to {e.__class__.__name__}: {str(e)}"
                    )
                    
                    # Wait before retrying
                    await asyncio.sleep(delay)
                    retries += 1
            
            # This should not be reached, but just in case
            raise RetryExhausted(f"All {max_retries} retries exhausted for {func.__name__}")
        
        return cast(F, wrapper)
    
    return decorator
